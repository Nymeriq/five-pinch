# Contributing

Five Pinch currently targets GNOME 50 on Wayland and Linux Apple SPI touchpads.
Support for additional SPI product IDs is experimental.

Before submitting a change, run the tests and package checks documented in README.md.
Do not remove device capability checks to make an unsupported device appear supported.

## Report a hardware test

Open an issue with your MacBook model, Linux distribution, kernel version,
GNOME version, input identity and the output of:

```bash
python3 -I reader/service.py --probe
```

Use Detect only first. Report the number of inward/outward attempts and detections,
negative-test results for normal pointing/scrolling/swiping, and lock/suspend results.
Keep experimental acceptance distinct from hardware-validated compatibility.

## Build a Debian package

```bash
python3 packaging/build_deb.py --output ../five-pinch_0.4.0_all.deb --staging-parent ../work/deb-build
```

The package builder does not install the result or run maintainer scripts.
