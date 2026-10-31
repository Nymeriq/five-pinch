# SPDX-License-Identifier: MIT
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reader'))
from service import validate_device, coordinate_scale, find_device
from unittest.mock import patch, MagicMock


class CompatibilityTests(unittest.TestCase):
    def validate(self, **changes):
        args = dict(name='Apple SPI Touchpad', identity=(0x1c, 0x06cb, 0x0557, 0),
                    properties=5, slot=(0, 0, 10, 0, 0, 0),
                    x=(0, -6243, 6749, 0, 0, 96), y=(0, -170, 7685, 0, 0, 94),
                    tracking=(0, 0, 65535, 0, 0, 0))
        args.update(changes)
        return validate_device(**args)

    def test_original_device(self):
        self.validate()

    def test_other_spi_product_and_vendor_ids(self):
        for vendor, product in [(0x06cb, 0x1234), (0x05ac, 0x5678), (0, 0)]:
            with self.subTest(vendor=vendor, product=product):
                self.validate(identity=(0x1c, vendor, product, 1))

    def test_five_slots_suffice(self):
        self.validate(slot=(0, 0, 4, 0, 0, 0))

    def test_other_buses_and_device_names_are_allowed(self):
        for bus, name in ((3, 'USB Trackpad'), (5, 'Magic Trackpad'), (0x18, 'ELAN Touchpad'), (0x11, 'Synaptics')):
            self.validate(name=name, identity=(bus, 0x1234, 0x5678, 0))

    def test_non_touchpad_classification_rejected(self):
        with self.assertRaises(RuntimeError):
            self.validate(name='Keyboard', is_touchpad=False)

    def test_direct_touchscreen_rejected(self):
        for props in (2, 3):
            with self.assertRaises(RuntimeError):
                self.validate(properties=props)

    def test_insufficient_or_invalid_slots(self):
        for axis in ((0, 0, 3, 0, 0, 0), (1, 1, 10, 0, 0, 0), (0, 0, 64, 0, 0, 0)):
            with self.assertRaises(RuntimeError):
                self.validate(slot=axis)

    def test_invalid_ranges_rejected(self):
        for axis in ((0, 100, 100, 0, 0, 10), (0, 100, 0, 0, 0, 10)):
            with self.assertRaises(RuntimeError):
                self.validate(x=axis)

    def test_invalid_tracking_ids(self):
        with self.assertRaises(RuntimeError):
            self.validate(tracking=(0, 0, 0, 0, 0, 0))

    def test_missing_resolution_uses_normalized_fallback(self):
        x, y = (0, 0, 2000, 0, 0, 0), (0, 0, 1000, 0, 0, 0)
        self.validate(x=x, y=y, properties=0)
        self.assertEqual(coordinate_scale(x, y), (20, 10, 'normalized (100 x 100)'))

    def test_physical_resolution_preserved(self):
        self.assertEqual(coordinate_scale((0, 0, 2000, 0, 0, 96), (0, 0, 1000, 0, 0, 94)),
                         (96, 94, 'millimetres'))

    def test_discovery_skips_keyboards_and_tries_other_touchpads(self):
        with patch('service.glob.glob', return_value=['/sys/class/input/event3', '/sys/class/input/event1', '/sys/class/input/event2']), \
             patch('service.udev_properties', side_effect=lambda p: {'ID_INPUT_TOUCHPAD': '1'} if str(p).endswith(('2', '3')) else {'ID_INPUT_KEYBOARD': '1'}), \
             patch('service.Touchpad') as cls:
            pad = MagicMock()
            cls.side_effect = [RuntimeError('Only two slots'), pad]
            self.assertEqual(find_device(), '/dev/input/event3')
            self.assertEqual([c.args[0] for c in cls.call_args_list], ['/dev/input/event2', '/dev/input/event3'])
            pad.close.assert_called_once()

    def test_no_touchpad_does_not_open_keyboard(self):
        with patch('service.glob.glob', return_value=['/sys/class/input/event1']), \
             patch('service.udev_properties', return_value={'ID_INPUT_KEYBOARD': '1'}), \
             patch('service.Touchpad') as cls:
            with self.assertRaisesRegex(RuntimeError, 'No usable touchpad'):
                find_device()
            cls.assert_not_called()


if __name__ == '__main__':
    unittest.main()
