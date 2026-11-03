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
        self.assertIsNone(self.d.frame(4, hand(.75)))

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


class SensitivityTests(unittest.TestCase):
    def test_small_pinches_need_less_movement(self):
        for profile, scale, expected in [
                ('original', .86, False), ('balanced', .86, True),
                ('original', 1.14, False), ('balanced', 1.14, True),
                ('balanced', .90, False), ('relaxed', .90, True),
                ('balanced', 1.10, False), ('relaxed', 1.10, True)]:
            with self.subTest(profile=profile, scale=scale):
                d = Detector(profile)
                d.frame(0, hand())
                self.assertEqual(d.frame(.1, hand(scale)) is not None, expected)

    def test_slow_pinch_has_more_time(self):
        for profile in ('balanced', 'relaxed'):
            d = Detector(profile)
            d.frame(0, hand())
            self.assertIsNone(d.frame(1.5, hand(.96)))
            self.assertEqual(d.frame(2.5, hand(.85))['direction'], 'in')
        d = Detector('original')
        d.frame(0, hand())
        self.assertIsNone(d.frame(2.5, hand(.75)))

    def test_every_profile_rejects_non_pinch_motion(self):
        for profile in ('original', 'balanced', 'relaxed'):
            motions = [hand(dx=30), hand(angle=.8), hand(1.03)]
            one_finger = hand()
            one_finger[0] = (30, 20)
            motions.append(one_finger)
            for points in motions:
                with self.subTest(profile=profile, points=points):
                    d = Detector(profile)
                    d.frame(0, hand())
                    self.assertIsNone(d.frame(.1, points))

    def test_relaxed_still_requires_absolute_movement(self):
        tiny = {i: (x * .3, y * .3) for i, (x, y) in hand().items()}
        d = Detector('relaxed')
        d.frame(0, tiny)
        self.assertIsNone(d.frame(.1, {i: (x * .91, y * .91) for i, (x, y) in tiny.items()}))

    def test_every_profile_keeps_contact_and_click_guards(self):
        for profile in ('original', 'balanced', 'relaxed'):
            for points, clicked in [(hand(count=4), False), (hand(), True)]:
                d = Detector(profile)
                d.frame(0, hand())
                self.assertIsNone(d.frame(.1, points, clicked))
                self.assertIsNone(d.frame(.2, hand(.7)))
                d.frame(.3, {})
                d.frame(.4, hand())
                self.assertIsNotNone(d.frame(.5, hand(.7)))


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
