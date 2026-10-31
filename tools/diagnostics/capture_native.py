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
from detector import Detector
from service import Touchpad


def capture(path, destination, seconds=45):
    pad = Touchpad(path)
    fd = pad.fd
    try:
        name, slot, x, y = pad.name, pad.slot, pad.x, pad.y
        state = pad.state
        detector = Detector()
        ready = False
        clicked = bool(pad.buttons)
        event_struct = struct.Struct('@llHHi')
        pending = b''
        maximum = 0
        candidates = []
        frames = 0
        started = time.monotonic()
        output = Path(destination)
        with output.open('w') as log:
            log.write(json.dumps({'device': name, 'slot_axis': slot,
                                  'x_axis': x, 'y_axis': y, 'coordinate_mode': pad.coordinate_mode}) + '\n')
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
                        log.write(json.dumps({'time': now, 'points': points,
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
        pad.close()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--seconds', type=float, default=45)
    args = p.parse_args()
    capture(args.device, args.output, args.seconds)
