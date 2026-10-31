# Changelog

## 0.5.0 — 2026-10-31

- Try any Linux touchpad: no brand, name, vendor, product or bus allowlist.
- Discover udev-classified touchpads and skip candidates that cannot supply
  the necessary contact coordinates; do not inspect keyboard event streams.
- Use normalized coordinates when physical axis resolution is unavailable.
- Allow an optional event-device override in settings for multiple touchpads.
- Document the single tested reference device and welcome hardware-report PRs.
- Keep read-only access, supervised shutdown, disabled first-install defaults
  and package rollback. Touchscreens and devices without five tracked positions
  cannot provide this five-finger gesture.

## 0.4.0 — 2026-10-30

- Initial public release.
- Five-finger pinch recognition with separate inward and outward actions.
- Separate app-grid open/close and overview open/close actions.
- English settings and a Debian package with a user-session setup launcher.
- Experimental support for Apple SPI Touchpad product IDs, gated by SPI bus,
  indirect-pointer properties, five or more coordinate slots, tracking IDs and
  physical axis resolution.
- Session-aware supervised reader with heartbeat expiry and no input grabbing.

Validated on one 2017 MacBook Pro; additional SPI models need hardware tests.
