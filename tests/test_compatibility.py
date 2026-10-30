# SPDX-License-Identifier: MIT
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reader'))
from service import validate_device


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

    def test_usb_and_bluetooth_rejected(self):
        for bus in (3, 5):
            with self.assertRaises(RuntimeError):
                self.validate(identity=(bus, 0x05ac, 0x0557, 0))

    def test_keyboard_and_other_names_rejected(self):
        for name in ('Apple SPI Keyboard', 'Apple Touchpad', 'Magic Trackpad'):
            with self.assertRaises(RuntimeError):
                self.validate(name=name)

    def test_direct_or_nonpointer_rejected(self):
        for props in (0, 2, 3):
            with self.assertRaises(RuntimeError):
                self.validate(properties=props)

    def test_insufficient_or_invalid_slots(self):
        for axis in ((0, 0, 3, 0, 0, 0), (1, 1, 10, 0, 0, 0), (0, 0, 64, 0, 0, 0)):
            with self.assertRaises(RuntimeError):
                self.validate(slot=axis)

    def test_missing_resolution_or_invalid_ranges(self):
        for axis in ((0, 0, 100, 0, 0, 0), (0, 100, 100, 0, 0, 10), (0, 100, 0, 0, 0, 10)):
            with self.assertRaises(RuntimeError):
                self.validate(x=axis)

    def test_invalid_tracking_ids(self):
        with self.assertRaises(RuntimeError):
            self.validate(tracking=(0, 0, 0, 0, 0, 0))


if __name__ == '__main__':
    unittest.main()
