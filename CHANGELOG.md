# Changelog

## 0.6.1 — 2026-11-03

- First public release of the three sensitivity modes tested in the local 0.6.0 build.
- Balanced confirmed comfortable by the reference MacBook Pro user; keep all three options.
- On package removal, disable/reset Five Pinch in reachable user sessions.
- Add `five-pinch-reset` for explicit per-user cleanup; never reset on upgrade.
- On purge, also remove the three files created by the optional APT setup.
- Document logout, multi-user cleanup, retained backups and full removal.

## 0.6.0 — 2026-11-03 (local test build)

- Add Balanced and Relaxed sensitivity profiles for smaller, slower pinches.
- Keep Original with the exact 0.5.1 thresholds as an immediate fallback.
- Apply sensitivity changes without logging out once this version is loaded.
- Preserve five-contact identity, coherent-motion, click and lifecycle guards.
- Sensitivity thresholds are experimental; reference-device feedback confirmed Balanced; other hardware still needs testing.

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
