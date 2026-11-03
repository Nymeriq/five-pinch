#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only touchpad recognizer, private stdin/stdout protocol with Shell.

No root, grab, uinput, network, D-Bus endpoint or raw event logging.
Without an ongoing parent lease it exits and closes the input device.
"""
import argparse
import array
import fcntl
import glob
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import time

# Python -I excludes CWD and PYTHONPATH. Only this installed, trusted directory
# is added after standard-library imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from detector import Detector, Slots, PROFILES

EVENT = struct.Struct('@llHHi')


def validate_device(name, identity, properties, slot, x, y, tracking, is_touchpad=True):
    """Require usable data, never a brand, model, vendor ID or input bus."""
    if not is_touchpad:
        raise RuntimeError('The input device is not classified as a touchpad by udev.')
    if properties & 2:  # INPUT_PROP_DIRECT: a touchscreen, not a touchpad.
        raise RuntimeError('Direct touchscreens are not touchpads.')
    if slot[1] != 0 or not 5 <= slot[2] + 1 <= 64:
        raise RuntimeError('Five independently tracked Protocol B contacts are required for five-finger pinch.')
    if x[1] >= x[2] or y[1] >= y[2]:
        raise RuntimeError('Valid X/Y coordinate ranges are required.')
    if tracking[1] < 0 or tracking[2] <= tracking[1]:
        raise RuntimeError('Per-contact tracking IDs are required.')


def coordinate_scale(x, y):
    if x[5] > 0 and y[5] > 0:
        return x[5], y[5], 'millimetres'
    # No invented physical dimensions: use an explicitly labelled virtual
    # 100 x 100 coordinate space when hardware does not report resolution.
    return (x[2] - x[1]) / 100, (y[2] - y[1]) / 100, 'normalized (100 x 100)'


def udev_properties(sysfs_path):
    try:
        result = subprocess.run(['udevadm', 'info', '--query=property', '--path=' + str(sysfs_path)],
                                capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode:
        return {}
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def boot_time():
    return time.clock_gettime(time.CLOCK_BOOTTIME)


class Lease:
    def __init__(self, now):
        self.deadline = now + 1.0
        self.started = False
        self.buffer = b''

    def receive(self, data, now):
        if not data:
            raise EOFError('Parent closed the control pipe')
        self.buffer += data
        if len(self.buffer) > 1024:
            raise ValueError('Oversized control message')
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            if line != b'run':
                raise ValueError('Unknown control message')
            self.started = True
            self.deadline = now + 1.0

    def valid(self, now):
        return now < self.deadline


def emit(message):
    print(json.dumps(message, ensure_ascii=False), flush=True)


def status(message):
    emit({'type': 'status', 'message': message})


def find_device():
    errors = []
    nodes = sorted(glob.glob('/sys/class/input/event*'),
                   key=lambda p: int(Path(p).name.removeprefix('event')))
    for node in nodes:
        if udev_properties(node).get('ID_INPUT_TOUCHPAD') != '1':
            continue
        path = '/dev/input/' + Path(node).name
        try:
            pad = Touchpad(path)
            pad.close()
            return path
        except (OSError, RuntimeError) as exc:
            errors.append(f'{Path(node).name}: {exc}')
    detail = '; '.join(errors) if errors else 'No udev-classified touchpad was found.'
    raise RuntimeError('No usable touchpad. ' + detail)


class Touchpad:
    def __init__(self, path):
        self.path = os.path.realpath(path)
        self.tail_pending = False
        self.cycle_active = False
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            name = bytearray(256)
            fcntl.ioctl(self.fd, 0x81004506, name, True)
            identity = bytearray(8)
            fcntl.ioctl(self.fd, 0x80084502, identity, True)
            self.name = name.split(b'\0')[0].decode()
            self.identity = struct.unpack('4H', identity)
            props = bytearray(8)
            fcntl.ioctl(self.fd, 0x80084509, props, True)
            self.properties = int.from_bytes(props, sys.byteorder)
            self.slot = self.axis(47)
            self.x, self.y = self.axis(53), self.axis(54)
            device_id = os.fstat(self.fd).st_rdev
            props_path = f'/sys/dev/char/{os.major(device_id)}:{os.minor(device_id)}'
            classified = udev_properties(props_path).get('ID_INPUT_TOUCHPAD') == '1'
            validate_device(self.name, self.identity, self.properties,
                            self.slot, self.x, self.y, self.axis(57), is_touchpad=classified)
            sx, sy, self.coordinate_mode = coordinate_scale(self.x, self.y)
            # Match kernel event timestamps to monotonic time; never execute backlog.
            fcntl.ioctl(self.fd, 0x400445a0, struct.pack('i', time.CLOCK_MONOTONIC))
            self.state = Slots(self.slot[1], self.slot[2], sx, sy)
            for code in (57, 53, 54):
                values = array.array('i', [code] + [0] * (self.slot[2] + 1))
                request = 0x8000450a | (len(values) * values.itemsize << 16)
                fcntl.ioctl(self.fd, request, values, True)
                for index in range(self.slot[2] + 1):
                    self.state.abs(47, index)
                    self.state.abs(code, values[index + 1])
            self.state.slot = self.slot[0]
            self.buttons = set()
            keys = bytearray(96)
            fcntl.ioctl(self.fd, 0x80604518, keys, True)
            for key in (272, 273, 274):
                if keys[key // 8] & (1 << (key % 8)):
                    self.buttons.add(key)
            self.ready = False
            self.detector = Detector()
            self.pending = b''
        except BaseException:
            self.close()
            raise

    def axis(self, code):
        buf = bytearray(24)
        fcntl.ioctl(self.fd, 0x80184540 + code, buf, True)
        return struct.unpack('6i', buf)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def read(self):
        data = os.read(self.fd, EVENT.size * 256)
        if not data:
            raise OSError('Touchpad disconnected.')
        self.pending += data
        results = []
        while len(self.pending) >= EVENT.size:
            sec, usec, kind, code, value = EVENT.unpack_from(self.pending)
            self.pending = self.pending[EVENT.size:]
            if kind == 0 and code == 3:
                raise OSError('SYN_DROPPED: reopening the recognizer.')
            if kind == 3:
                self.state.abs(code, value)
            elif kind == 1 and code in (272, 273, 274):
                if value:
                    self.buttons.add(code)
                else:
                    self.buttons.discard(code)
            elif kind == 0 and code == 0:
                points = self.state.points()
                if points is None:
                    self.ready = False
                    self.detector.clear()
                    continue
                now = sec + usec / 1e6
                if not 0 <= time.monotonic() - now <= .2:
                    self.ready = False
                    self.detector.clear()
                    continue
                if not points and getattr(self, 'tail_pending', False):
                    self.tail_pending = False
                    results.append({'event': 'pinch-released', 'time': now})
                if not points:
                    self.cycle_active = False
                if not self.ready:
                    self.ready = not points and not self.buttons
                    continue
                if points and not getattr(self, 'cycle_active', False):
                    self.cycle_active = True
                    results.append({'event': 'contact-begin', 'time': now})
                elif not points:
                    self.cycle_active = False
                if len(points) == 5 and not getattr(self, 'tail_pending', False):
                    self.tail_pending = True
                    results.append({'event': 'five-contact', 'time': now})
                candidate = self.detector.frame(now, points, bool(self.buttons))
                if candidate:
                    self.tail_pending = True
                    results.append(candidate)
        return results


def run(device_path=None, sensitivity='balanced'):
    if os.geteuid() == 0:
        status('Do not run as root. Let the extension start the recognizer as your own user.')
        return 1
    lease = Lease(boot_time())
    touchpad = None
    retry = 0
    sequence = 0
    try:
        while lease.valid(boot_time()):
            descriptors = [sys.stdin.fileno()]
            if touchpad:
                descriptors.append(touchpad.fd)
            readable, _, _ = select.select(descriptors, [], [], .1)
            if sys.stdin.fileno() in readable:
                lease.receive(os.read(sys.stdin.fileno(), 1024), boot_time())
            if not lease.valid(boot_time()):
                break
            if lease.started and touchpad is None and boot_time() >= retry:
                try:
                    touchpad = Touchpad(device_path or find_device())
                    touchpad.detector = Detector(sensitivity)
                    status(f'Recognition active: {touchpad.name} ({touchpad.coordinate_mode}; {sensitivity}). Lift all fingers before starting.')
                except PermissionError:
                    status('Cannot read the touchpad. See the installation guide.')
                    retry = boot_time() + 5
                except (OSError, RuntimeError) as exc:
                    status(str(exc))
                    retry = boot_time() + 5
            if touchpad and touchpad.fd in readable:
                try:
                    for candidate in touchpad.read():
                        sequence += 1
                        message = {'type': {'pinch-released': 'pinch-end', 'five-contact': 'five-contact', 'contact-begin': 'contact-begin'}.get(candidate['event'], 'pinch'),
                                   'device': touchpad.path, 'sequence': sequence,
                                   'monotonic_us': int(candidate['time'] * 1000000)}
                        if message['type'] == 'pinch':
                            message['direction'] = candidate['direction']
                        emit(message)
                except (OSError, ValueError) as exc:
                    touchpad.close()
                    touchpad = None
                    retry = boot_time() + 2
                    status(str(exc))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        if touchpad:
            touchpad.close()
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Report device capabilities without desktop actions')
    parser.add_argument('--device', help='Optional /dev/input/eventN; otherwise select the first usable touchpad')
    parser.add_argument('--sensitivity', choices=PROFILES, default='balanced',
                        help='Gesture sensitivity; original restores the 0.5.1 recognition thresholds')
    args = parser.parse_args()
    if args.probe:
        pad = Touchpad(args.device or find_device())
        try:
            print(json.dumps({'name': pad.name,
                              'identity': ':'.join(f'{v:04x}' for v in pad.identity[:3]),
                              'compatibility': 'open hardware support; only the documented reference device is tested',
                              'slots': pad.slot[2] + 1, 'coordinate_mode': pad.coordinate_mode,
                              'resolution': [pad.x[5], pad.y[5]], 'readable': True}))
        finally:
            pad.close()
    else:
        raise SystemExit(run(args.device, args.sensitivity))
