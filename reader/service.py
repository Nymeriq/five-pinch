#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only Apple SPI recognizer, private stdin/stdout protocol with Shell.

No root, grab, uinput, network, D-Bus endpoint or raw event logging.
Without an ongoing parent lease it exits and closes the input device.
"""
import array
import fcntl
import glob
import json
import os
from pathlib import Path
import select
import struct
import sys
import time

# Python -I excludes CWD and PYTHONPATH. Only this installed, trusted directory
# is added after standard-library imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from detector import Detector, Slots

EVENT = struct.Struct('@llHHi')
BUS_SPI = 0x001c


def validate_device(name, identity, properties, slot, x, y, tracking):
    """Experimental family support, gated by actual multitouch capabilities."""
    if name != 'Apple SPI Touchpad' or identity[0] != BUS_SPI:
        raise RuntimeError('This release requires an Apple SPI Touchpad on the SPI bus.')
    # INPUT_PROP_POINTER is required; INPUT_PROP_DIRECT identifies a touchscreen.
    if not properties & 1 or properties & 2:
        raise RuntimeError('The device must be an indirect pointer touchpad.')
    if slot[1] != 0 or not 5 <= slot[2] + 1 <= 64:
        raise RuntimeError('At least five Protocol B slots are required.')
    if x[1] >= x[2] or y[1] >= y[2] or x[5] <= 0 or y[5] <= 0:
        raise RuntimeError('Valid X/Y coordinate ranges and axis resolutions are required.')
    if tracking[1] < 0 or tracking[2] <= tracking[1]:
        raise RuntimeError('Per-contact tracking IDs are required.')


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
    paths = []
    for name in glob.glob('/sys/class/input/event*/device/name'):
        try:
            if Path(name).read_text().strip() == 'Apple SPI Touchpad':
                paths.append('/dev/input/' + Path(name).parents[1].name)
        except OSError:
            continue
    if len(paths) != 1:
        raise RuntimeError('Exactly one Apple SPI Touchpad is required.')
    return paths[0]


class Touchpad:
    def __init__(self, path):
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
            validate_device(self.name, self.identity, self.properties,
                            self.slot, self.x, self.y, self.axis(57))
            # Match kernel event timestamps to monotonic time; never execute backlog.
            fcntl.ioctl(self.fd, 0x400445a0, struct.pack('i', time.CLOCK_MONOTONIC))
            self.state = Slots(self.slot[1], self.slot[2], self.x[5], self.y[5])
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
                if not self.ready:
                    self.ready = not points and not self.buttons
                    continue
                candidate = self.detector.frame(now, points, bool(self.buttons))
                if candidate:
                    results.append(candidate)
        return results


def run():
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
                    touchpad = Touchpad(find_device())
                    status('Recognition active (experimental Apple SPI support). Lift all fingers before starting.')
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
                        emit({'type': 'pinch', 'direction': candidate['direction'],
                              'sequence': sequence,
                              'monotonic_us': int(time.monotonic() * 1000000)})
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
    if sys.argv[1:] == ['--probe']:
        pad = Touchpad(find_device())
        try:
            print(json.dumps({'name': pad.name,
                              'identity': ':'.join(f'{v:04x}' for v in pad.identity[:3]),
                              'compatibility': 'experimental; hardware testing required',
                              'slots': pad.slot[2] + 1,
                              'resolution': [pad.x[5], pad.y[5]], 'readable': True}))
        finally:
            pad.close()
    elif sys.argv[1:]:
        raise SystemExit('No standalone options. Run from the extension.')
    else:
        raise SystemExit(run())
