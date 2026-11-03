# Changelog

## 0.7.1 — local UI review build

- Main preferences contain only Enable gestures, Pinch in, Pinch out and Sensitivity.
- Put device selection and compatibility switches under Advanced; status under Diagnostics.
- Remove taglines, explanatory rows, duplicated labels and unnecessary search.
- Open preferences directly for active installations. Require explicit Enable for
  inactive extensions and preserve safe manual-install backup migration.
- Keep all stored setting keys/values, gesture engines, profiles, safeguards and
  uninstall behavior unchanged. No new UI framework or dependency.

## 0.7.0 — 2026-11-03

- Publish rinertia virtual-scroll protection, confirmed working by the reference user.
- Detect the actual running virtual device automatically; no rinertia dependency,
  service stop, restart, configuration edit or global scroll setting change.
- Keep normal behavior without rinertia, with an option to disable the integration.
- Keep Original, Balanced and Relaxed recognition profiles.
- Add a dedicated scalable Five Pinch application icon and preference-page icon.
- Align the launcher desktop filename with its existing application ID for icon matching.
- Retain uninstall/reset cleanup, prior packages and opt-in diagnostics.

## 0.6.6 — local test build

- Add optional, enabled-by-default rinertia scrolling protection. Detect the
  actual `rinertia Virtual Device` event source; no service control is used.
- Block that virtual device's scrolls during a five-contact cycle and its
  momentum tail. A new physical contact cycle immediately clears the old guard.
- End the tail after a 120 ms scroll-free gap, at most two seconds after hand lift;
  an unreleased cycle expires after three seconds.
- Other pointer devices, standalone <=4-contact cycles, and the three recognition
  profiles remain unchanged. Scheduler races and other virtual device names still
  require live testing; this is not a universal conflict guarantee.
- Keep a settings toggle, prior packages and diagnostic recordings for rollback.

## 0.6.5 — diagnostic test build

- Still no recognition/filter changes.
- Trace workspace activation stacks, overview transitions and action boundaries.
- Observe scroll/button events and overview-group delivery as well as stage swipes.
- Refresh read-only tracker observers when tracing starts and report which exist.
- Capture 02 confirmed a workspace change without any observed native stage swipe;
  a swipe cause remains unproven. Detailed findings saved alongside the private log.

## 0.6.4 — diagnostic test build

- No recognition or swipe-filter behavior changes.
- Opt-in journal trace records each captured swipe phase and its filter decision,
  reader lifecycle messages, native tracker signals and workspace changes.
- Tracker hooks observe only; no tracker state is changed. Logging is off by default.
- Extend the session recorder with opt-in Shell tracing and restore the previous
  logging setting when recording ends. Existing source capture remains available.

## 0.6.3 — local test build

- Arm pinch-tail protection at five simultaneous contacts, before the pinch
  action threshold. This covers early thumb/index lift even if no action fired.
- Keep protection through that contact cycle's full hand lift, with the existing
  three-second watchdog. Independent <=4-contact cycles never arm it.
- Show the latest native swipe filter decision in settings for diagnosis.
- Do not cancel native swipes already underway before the contact message arrives.
- Live testing is pending; 0.6.2 did not resolve the reference user's symptom.

## 0.6.2 — local test build

- Add optional Protect pinch ending, scoped to the same physical touchpad and
  a confirmed five-finger pinch with an assigned action.
- Suppress complete new native 3/4-finger swipe sequences begun in that pinch's
  tail. Leave independent gestures started with four or fewer fingers alone.
- Report the full hand lift from the reader, so a new physical gesture is allowed
  immediately. Use event timestamps to distinguish delayed old events.
- Do not interrupt native swipes that began before pinch recognition.
- No global swipe sensitivity changes or changes to GNOME tracker settings.
- Keep a switch and the 0.6.1 package as fallbacks; live testing is pending.

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
