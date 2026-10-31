# Five Pinch

Experimental five-finger pinch gestures for Apple SPI touchpads on GNOME 50 / Wayland.

[Download the Debian package](https://github.com/Nymeriq/five-pinch/releases/latest) · [MIT license](LICENSE)

The settings UI, action names, status messages and setup application are in English.

The repository also includes the [development history and diagnostic tools](docs/DEVELOPMENT.md),
the complete recognizer and extension source, Debian packaging and automated tests.

## Install the Debian package

From the folder containing the downloaded package:

```bash
sudo apt install ./five-pinch_0.4.0_all.deb
```

Open **Five Pinch Settings** from your applications. On a new installation,
log out and back in if GNOME has not discovered the extension yet. Then select
**Enable and open settings**. Start with **Detect only (no action)** for both
directions and turn on **Enable recognition**. Lift all fingers between gestures.

Suggested actions once detection works:

- **Pinch in → Open app grid**
- **Pinch out → Close app grid**

**Close app grid** returns to the desktop only when the app grid is selected.
**Close overview** is a separate action and also closes the window overview.
Both options remain independently selectable.

### Upgrading the previous manual installation

A user installation in `~/.local/share/gnome-shell/extensions/five-pinch@local.codex`
overrides the system version installed by the package. The setup application
detects this and offers **Use packaged version**. This disables the old extension,
backs up its files to `~/.local/state/five-pinch/backups/`, and preserves all
gesture settings. XDG data/state locations are respected when set.

After switching, save your work and log out and back in. Open Five Pinch Settings
again and enable the packaged extension. Do not restore the old user folder over
the packaged version unless you deliberately want to revert to the manual copy.

The package's root installation scripts never edit user home directories,
change user gesture preferences, or enable extensions for users.

### Removal

Disable Five Pinch in the Extensions app first, then:

```bash
sudo apt remove five-pinch
```

Log out and back in to unload any already-loaded Shell code. Personal gesture
settings and backups are retained, including on purge. No input group membership
or root background service is created.

## Compatibility: not every MacBook

The only hardware currently tested end to end is a **2017 MacBook Pro
with Apple SPI Touchpad**, identity `001c:06cb:0557`. Version 0.4.0 removes
that vendor/product allowlist experimentally. It accepts other devices only if:

- The exact kernel name is `Apple SPI Touchpad` and the input bus is SPI (`001c`).
- It is an indirect pointer, not a direct touchscreen.
- It exposes Linux Protocol B with at least five coordinate slots (up to 64).
- Both X/Y coordinate ranges are valid and have nonzero physical resolution.
- Per-contact tracking IDs are available.
- GNOME Shell 50 is running on Wayland in an active local session.

Vendor/product IDs are retained in `--probe` output to identify test machines.
No device is declared hardware-validated merely because these checks pass.
Sensitivity thresholds are unchanged and measured in millimetres, but geometry,
thumb/palm behaviour, firmware and Linux driver differences still require tests.
Only one matching touchpad may be present; ambiguous discovery is rejected.

This is **experimental compatibility**, not a claim that every SPI MacBook works.
Older USB/BCM5974 devices, external Magic Trackpads and non-SPI Apple Silicon/T2
input paths are not included simply because they are Apple hardware. X11 and
macOS are not supported.

Different MacBook generations use different input paths; see the kernel
[Apple SPI driver](https://github.com/torvalds/linux/blob/master/drivers/input/keyboard/applespi.c),
[BCM5974 documentation](https://www.kernel.org/doc/html/v4.18/input/devices/bcm5974.html),
and [Asahi support overview](https://asahilinux.org/docs/platform/feature-support/overview/).

For each newly accepted model: record the `--probe` identity and model name;
perform 20 inward and 20 outward gestures with all fingers lifted between cycles;
then test ordinary pointing, scrolling, three/four/five-finger swipes, clicks and
palm contact without pinching. Also test lock/unlock and suspend/resume. Verify
no unintended desktop actions. Start with **Detect only** and keep a rollback
package available. These tests have not yet been performed on additional models.

## Device access and lifecycle

The package installs one udev rule in `/usr/lib/udev/rules.d/70-five-pinch.rules`.
It adds the standard `uaccess` tag only to devices with the exact
`Apple SPI Touchpad` name, SPI bus, and udev touchpad classification.
Version 0.4.0 deliberately removes vendor/product filters in both the reader
and the permission rule; unrelated keyboards, USB and Bluetooth nodes do not match. It does not grant keyboard access, modify groups,
or make device nodes world-readable. Standard session ACLs can include write
permission; the recognizer itself opens the input device read-only.
Rules are reloaded on install/remove. If access is not immediately refreshed,
log out and back in. Test access on each target system before release.

The GNOME extension supervises a Python child through private stdin/stdout pipes.
The child does not expose a D-Bus gesture endpoint, create virtual input devices,
grab the touchpad, log raw coordinates, or run as root. Parent closure, extension
disablement, or missing heartbeats stops it. Session lock, inactive session,
sleep and long Shell stalls stop recognition; lift all fingers after resuming.

Typing suppression observes key events delivered to the Shell and has not been
validated in every application. The recognizer does not reproduce libinput's
complete palm/thumb/typing filters. Existing three/four-finger gesture handlers
continue to run and may conflict with contact transitions.

Detection requires five stable tracking IDs, at least 80 ms, 18% median pairwise
scale change and 3 mm median pairwise distance change; at least 7 of 10 pairs
must move consistently. It produces at most one event per full hand-contact cycle.
Click, contact loss/replacement, stale events and dropped input cancel the cycle.

## Build and checks

Build the package without installing it, from the source folder:

```bash
python3 packaging/build_deb.py --output ../five-pinch_0.4.0_all.deb --staging-parent ../../work/deb-build
```

Build tools: Python 3, `dpkg-deb`, and `glib-compile-schemas`.
The package is architecture `all` because its files are Python, GJS and data;
that label does not imply every CPU platform or MacBook is hardware-supported.

Checks:

```bash
PYTHONPATH=reader python3 -m unittest discover -s tests -v
gjs -m tests/protocol_test.js
python3 tests/check_shell_logic.py
glib-compile-schemas --strict schemas
desktop-file-validate packaging/five-pinch-settings.desktop
udevadm verify packaging/70-five-pinch.rules
```

The automated suite contains 37 Python tests, 8 protocol checks and 13 Shell
logic checks with mocked UI/session objects. Package migration tests verify
backups, wrong UUID rejection, symlink rejection and disable-failure handling.
Package archive inspection/extraction is separate from a real apt installation.
The 0.3.0 Debian installation and live app-grid actions were confirmed on the
reference MacBook. The 0.4.0 family expansion still needs real tests on other models.

The original detector was exercised on the real touchpad: 18 inward and 17
outward candidates; a separate short negative run had no candidates despite
12 five-contact cycles. Live app-grid open/close actions were also confirmed on the reference machine. These are initial results, not a universal reliability guarantee.

The source archive also contains the older manual `install.sh` / `uninstall.sh`.
Use the .deb for a new installation; do not install a second manual copy on top
of the package. Manual files and Debian-managed files have separate ownership.

MIT license, see LICENSE. Independently written; no Custom Touchpad Gestures
source code is included.

## Roll back this experiment

Keep the previous `five-pinch_0.3.0_all.deb`. To revert a packaged installation:

```bash
sudo apt install --allow-downgrades ./five-pinch_0.3.0_all.deb
```

Log out and back in after either upgrade or downgrade so GNOME loads the
corresponding code. Your existing gesture action settings are preserved.
The packaged 0.4.0 reader has passed its probe/lifecycle smoke test on the
original MacBook; other SPI identities are covered by synthetic capability
tests only, pending real testers.
