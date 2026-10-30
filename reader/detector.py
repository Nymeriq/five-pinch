#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Five-contact geometry detector and Protocol B slot accumulator."""
import itertools
import math
import statistics


class Detector:
    def __init__(self):
        self.clear()

    def clear(self):
        self.ids = None
        self.base = None
        self.started = None
        self.blocked = False

    def frame(self, now, points, clicked=False):
        """points: {tracking_id: (x_mm, y_mm)} from a complete SYN_REPORT."""
        if not points:
            self.clear()
            return None
        if clicked:
            self.blocked = True
        if self.blocked:
            return None
        if len(points) != 5:
            if self.ids is not None:
                self.blocked = True
            return None
        ids = tuple(sorted(points))
        if self.ids is None:
            self.ids, self.started = ids, now
            self.base = dict(points)
            return None
        if ids != self.ids or now < self.started or now - self.started > 2.0:
            self.blocked = True
            return None
        if now - self.started < 0.080:
            return None
        ratios, changes = [], []
        for a, b in itertools.combinations(ids, 2):
            before = math.dist(self.base[a], self.base[b])
            after = math.dist(points[a], points[b])
            if before < 5.0:  # Degenerate initial hand geometry: do not guess.
                self.blocked = True
                return None
            ratios.append(after / before)
            changes.append(after - before)
        scale = statistics.median(ratios)
        delta = statistics.median(changes)
        inward = scale <= 0.82 and delta <= -3.0
        outward = scale >= 1.18 and delta >= 3.0
        if not (inward or outward):
            return None
        # At least 7 of 10 finger pairs must change in the same direction.
        coherent = sum(r < 0.94 if inward else r > 1.06 for r in ratios)
        if coherent < 7:
            return None
        self.blocked = True  # One candidate per complete hand contact cycle.
        return {'event': 'five-pinch-candidate',
                'direction': 'in' if inward else 'out',
                'scale': round(scale, 4), 'time': now,
                'diagnostic_only': True}


class Slots:
    """Protocol B accumulator; never reuse coordinates across tracking IDs."""
    def __init__(self, minimum, maximum, rx, ry):
        self.minimum, self.maximum = minimum, maximum
        self.rx, self.ry = rx, ry
        self.slot = minimum
        self.slots = {}

    def abs(self, code, value):
        if code == 47:  # ABS_MT_SLOT
            if not self.minimum <= value <= self.maximum:
                raise ValueError('Invalid MT slot')
            self.slot = value
        elif code == 57:  # ABS_MT_TRACKING_ID
            self.slots[self.slot] = {'id': value}
        elif code in (53, 54):
            self.slots.setdefault(self.slot, {})['x' if code == 53 else 'y'] = value

    def points(self):
        active = [s for s in self.slots.values() if s.get('id', -1) >= 0]
        if any('x' not in s or 'y' not in s for s in active):
            return None
        result = {s['id']: (s['x'] / self.rx, s['y'] / self.ry) for s in active}
        if len(result) != len(active):
            raise ValueError('Duplicate tracking ID')
        return result


