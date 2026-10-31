#!/usr/bin/env python3
"""Linux diagnostic reader using only the Python standard library. No actions."""
import array
import fcntl
import json
import os
from pathlib import Path
import select
import struct
import time
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'reader'))
from detector import Detector, Slots


def capture(path, destination, seconds=45):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        name = bytearray(256)
        fcntl.ioctl(fd, 0x81004506, name, True)
        name = name.split(b'\0')[0].decode()
        if name != 'Apple SPI Touchpad':
            raise RuntimeError('Unexpected device')
        def axis(code):
            buf = bytearray(24)
            fcntl.ioctl(fd, 0x80184540 + code, buf, True)
            return struct.unpack('6i', buf)
        slot, x, y = axis(47), axis(53), axis(54)
        if slot[2] - slot[1] + 1 < 5 or min(x[5], y[5]) <= 0:
            raise RuntimeError('Insufficient slots or resolution')
        state = Slots(slot[1], slot[2], x[5], y[5])
        state.slot = slot[0]
        # Read current per-slot state so startup with fingers down is safe.
        for code in (57, 53, 54):
            values = array.array('i', [code] + [0] * (slot[2] + 1))
            request = 0x8000450a | (len(values) * values.itemsize << 16)
            fcntl.ioctl(fd, request, values, True)
            for index in range(slot[1], slot[2] + 1):
                state.abs(47, index)
                state.abs(code, values[index + 1])
        state.slot = slot[0]
        detector = Detector()
        ready = False
        buttons = set()
        keys = bytearray(96)
        fcntl.ioctl(fd, 0x80604518, keys, True)
        for key in (272, 273, 274):
            if keys[key // 8] & (1 << (key % 8)):
                buttons.add(key)
        event_struct = struct.Struct('@llHHi')
        pending = b''
        maximum = 0
        candidates = []
        frames = 0
        started = time.monotonic()
        output = Path(destination)
        with output.open('w') as log:
            log.write(json.dumps({'device': name, 'slot_axis': slot,
                                  'x_axis': x, 'y_axis': y}) + '\n')
            print(f'MÉRÉS ELINDULT: {seconds:g} másodperc, csak megfigyelés.', flush=True)
            while time.monotonic() - started < seconds:
                if not select.select([fd], [], [], .25)[0]:
                    continue
                data = os.read(fd, event_struct.size * 256)
                if not data:
                    raise RuntimeError('Device disconnected')
                pending += data
                while len(pending) >= event_struct.size:
                    sec, usec, kind, code, value = event_struct.unpack_from(pending)
                    pending = pending[event_struct.size:]
                    if kind == 0 and code == 3:
                        raise RuntimeError('SYN_DROPPED; recording aborted')
                    if kind == 3:
                        state.abs(code, value)
                    elif kind == 1 and code in (272, 273, 274):
                        if value:
                            buttons.add(code)
                        else:
                            buttons.discard(code)
                    elif kind == 0 and code == 0:
                        points = state.points()
                        if points is None:
                            continue
                        now = sec + usec / 1e6
                        maximum = max(maximum, len(points))
                        frames += 1
                        log.write(json.dumps({'time': now, 'points_mm': points,
                                              'clicked': bool(buttons)}) + '\n')
                        if not ready:
                            ready = not points
                            continue
                        result = detector.frame(now, points, bool(buttons))
                        if result:
                            candidates.append(result)
                            print(json.dumps(result), flush=True)
            summary = {'frames': frames, 'max_contacts': maximum,
                       'candidates': candidates, 'recording': str(output)}
            print(json.dumps(summary), flush=True)
    finally:
        os.close(fd)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--seconds', type=float, default=45)
    args = p.parse_args()
    capture(args.device, args.output, args.seconds)
