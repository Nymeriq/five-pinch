# SPDX-License-Identifier: MIT
import os
import sys
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reader'))
from service import Lease, Touchpad, EVENT
from detector import Detector, Slots


class LeaseTests(unittest.TestCase):
    def test_expiry(self):
        lease = Lease(0)
        self.assertFalse(lease.started)
        self.assertFalse(lease.valid(1))
        lease.receive(b'run\n', .5)
        self.assertTrue(lease.valid(1.49))
        self.assertFalse(lease.valid(1.5))

    def test_partial(self):
        lease = Lease(0)
        lease.receive(b'ru', .2)
        self.assertFalse(lease.started)
        lease.receive(b'n\n', .3)
        self.assertTrue(lease.started)

    def test_closed_or_invalid_control(self):
        for data, error in [(b'', EOFError), (b'execute\n', ValueError), (b'x' * 1025, ValueError)]:
            with self.assertRaises(error):
                Lease(0).receive(data, .1)


class NativeInputTests(unittest.TestCase):
    def setUp(self):
        self.r, self.w = os.pipe()
        self.pad = Touchpad.__new__(Touchpad)
        self.pad.fd = self.r
        self.pad.state = Slots(0, 10, 10, 10)
        self.pad.buttons = set()
        self.pad.ready = False
        self.pad.detector = Detector()
        self.pad.pending = b''
        self.start = time.monotonic() - .15

    def tearDown(self):
        self.pad.close()
        os.close(self.w)

    def send(self, events, stamp=None):
        t = stamp if stamp is not None else self.start
        sec = int(t)
        usec = int((t - sec) * 1e6)
        os.write(self.w, b''.join(EVENT.pack(sec, usec, *event) for event in events))
        return self.pad.read()

    def hand(self, scale=1, ids=False):
        events = []
        for i, (x, y) in enumerate([(0, 0), (15, 30), (30, 40), (45, 30), (60, 0)]):
            events.append((3, 47, i))
            if ids:
                events.append((3, 57, i + 10))
            events.extend([(3, 53, round(x * scale * 10)), (3, 54, round(y * scale * 10))])
        events.append((0, 0, 0))
        return events

    def test_raw_frames_produce_pinch_once(self):
        self.send([(0, 0, 0)])  # Hands off arms detector.
        self.send(self.hand(ids=True))
        results = self.send(self.hand(.75), self.start + .1)
        self.assertEqual([r['direction'] for r in results], ['in'])
        self.assertEqual(self.send(self.hand(.7), self.start + .11), [])

    def test_release_is_reported_only_after_a_recognized_pinch(self):
        self.send([(0, 0, 0)])
        self.send(self.hand(ids=True))
        self.assertEqual(self.send(self.hand(.75), self.start + .1)[0]['direction'], 'in')
        lift = []
        for i in range(5):
            lift.extend([(3, 47, i), (3, 57, -1)])
        lift.append((0, 0, 0))
        result = self.send(lift, self.start + .11)
        self.assertEqual([r['event'] for r in result], ['pinch-released'])
        self.assertEqual(self.send([(0, 0, 0)], self.start + .12), [])

    def test_ordinary_contact_cycle_sends_no_release(self):
        self.send([(0, 0, 0)])
        self.send(self.hand(ids=True))
        self.send(self.hand(1.03), self.start + .1)
        lift = []
        for i in range(5):
            lift.extend([(3, 47, i), (3, 57, -1)])
        lift.append((0, 0, 0))
        self.assertEqual(self.send(lift, self.start + .11), [])

    def test_normalized_coordinates_can_recognize_pinch(self):
        self.pad.state = Slots(0, 10, 20, 10)
        self.send([(0, 0, 0)])
        self.send(self.hand(ids=True))
        results = self.send(self.hand(.75), self.start + .1)
        self.assertEqual([r['direction'] for r in results], ['in'])

    def test_startup_contacts_not_armed(self):
        self.send(self.hand(ids=True))
        self.assertEqual(self.send(self.hand(.75), self.start + .1), [])

    def test_dropped_events_abort(self):
        with self.assertRaisesRegex(OSError, 'SYN_DROPPED'):
            self.send([(0, 3, 0)])

    def test_stale_input_disarms(self):
        self.send([(0, 0, 0)])
        self.send(self.hand(ids=True), time.monotonic() - 2)
        self.assertFalse(self.pad.ready)

    def test_click_cancels(self):
        self.send([(0, 0, 0)])
        self.send(self.hand(ids=True))
        self.send([(1, 272, 1), (0, 0, 0)])
        self.assertEqual(self.send(self.hand(.75), self.start + .1), [])


if __name__ == '__main__':
    unittest.main()
