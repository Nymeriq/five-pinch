# Contributing

Try Five Pinch on any touchpad. The only hardware currently tested is a
2017 MacBook Pro with Apple SPI Touchpad. We welcome both successful reports
and fixes for other manufacturers, transports, drivers and coordinate formats.

## Report a test or add your hardware to the docs

Please open a pull request adding a row to [docs/HARDWARE.md](docs/HARDWARE.md).
An issue is fine too if you are not comfortable making a PR. Include:

- Touchpad/laptop model and connection type if known.
- Linux distribution, kernel, GNOME version and Wayland session.
- Output of `python3 -I reader/service.py --probe`.
- Whether pinch in/out work; mention missed or unwanted activations.
- Relevant settings, including a manual device path or normalized-coordinate fallback.

Start with Detect only before binding actions. For a fuller test, try ordinary
pointing, scrolling, three/four/five-finger swipes, click, lock/unlock and suspend.
A simple report is still welcome; do not label unperformed checks as passed.
Raw input recordings are optional and are not required to submit a report.

## Code improvements

Send a PR for detection/discovery improvements or support for another input
format. Keep the reader read-only, supervised and easy to disable. Do not add
vendor whitelists. Checks should reject missing/malformed data, not unknown brands.
If an improvement makes a new device work, update the hardware table in the same PR.
Run the tests/build checks in README.md and state what you actually tested.

## Build

```bash
python3 packaging/build_deb.py --output ../five-pinch_0.5.0_all.deb --staging-parent ../work/deb-build
```
