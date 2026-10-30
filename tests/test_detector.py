# SPDX-License-Identifier: MIT
import math
import unittest
from detector import Detector, Slots


def hand(scale=1, dx=0, angle=0, count=5):
    return {i: (dx + scale * (x * math.cos(angle) - y * math.sin(angle)),
                scale * (x * math.sin(angle) + y * math.cos(angle)))
            for i, (x, y) in enumerate([(0, 0), (15, 30), (30, 40), (45, 30), (60, 0)][:count])}


class RecognitionTests(unittest.TestCase):
    def setUp(self):
        self.d = Detector()
        self.d.frame(0, hand())

    def test_in(self):
        self.assertEqual(self.d.frame(.1, hand(.75))['direction'], 'in')

    def test_out(self):
        self.assertEqual(self.d.frame(.1, hand(1.25))['direction'], 'out')

    def test_swipe(self):
        self.assertIsNone(self.d.frame(.1, hand(dx=30)))

    def test_rotate(self):
        self.assertIsNone(self.d.frame(.1, hand(angle=.8)))

    def test_jitter(self):
        self.assertIsNone(self.d.frame(.1, hand(1.03)))

    def test_settle(self):
        self.assertIsNone(self.d.frame(.03, hand(.75)))

    def test_one_candidate(self):
        self.d.frame(.1, hand(.75))
        self.assertIsNone(self.d.frame(.2, hand(1.3)))
        self.d.frame(.3, {})
        self.d.frame(.4, hand())
        self.assertIsNotNone(self.d.frame(.5, hand(1.3)))

    def test_contact_loss_latches(self):
        self.d.frame(.1, hand(count=4))
        self.assertIsNone(self.d.frame(.2, hand(.75)))

    def test_id_replacement(self):
        p = hand(.75)
        p[9] = p.pop(0)
        self.assertIsNone(self.d.frame(.1, p))

    def test_click(self):
        self.assertIsNone(self.d.frame(.1, hand(.75), clicked=True))
        self.assertIsNone(self.d.frame(.2, hand(.7)))

    def test_timeout(self):
        self.assertIsNone(self.d.frame(3, hand(.75)))

    def test_six_contacts(self):
        p = hand(.75)
        p[5] = (80, 80)
        self.d.frame(.1, p)
        self.assertIsNone(self.d.frame(.2, hand(.75)))

    def test_single_moving_finger(self):
        p = hand()
        p[0] = (30, 20)
        self.assertIsNone(self.d.frame(.1, p))

    def test_three_or_four_never_trigger(self):
        for n in (3, 4):
            d = Detector()
            d.frame(0, hand(count=n))
            self.assertIsNone(d.frame(.1, hand(.7, count=n)))


class ProtocolTests(unittest.TestCase):
    def test_tracking_replacement_clears_coordinates(self):
        s = Slots(0, 10, 10, 20)
        s.abs(57, 1)
        s.abs(53, 100)
        s.abs(54, 200)
        self.assertEqual(s.points(), {1: (10, 10)})
        s.abs(57, 2)
        self.assertIsNone(s.points())
        s.abs(57, -1)
        self.assertEqual(s.points(), {})

    def test_bad_slot(self):
        with self.assertRaises(ValueError):
            Slots(0, 10, 1, 1).abs(47, 11)


if __name__ == '__main__':
    unittest.main()
