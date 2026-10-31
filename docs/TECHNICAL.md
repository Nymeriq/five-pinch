# Five Pinch: technical guide

[← Back to the quick start](../README.md)

## Choosing a touchpad manually

With multiple touchpads, automatic mode picks the first usable event device.
Leave **Touchpad device path** blank to keep this automatic selection.
To select a particular touchpad, enter its **full Linux input device path**,
for example `/dev/input/event7`. The placeholder is an example only.
A device name, a USB/vendor/product ID, or just `event7` is not accepted.

To find the path, run:

```bash
sudo libinput list-devices
```

If the command is missing, install Ubuntu's `libinput-tools` package.
Find your touchpad's **Device** section and copy the path from **Kernel**
(shown as **Device node** by some tools), for example `/dev/input/event7`.
Do not copy a keyboard or mouse entry. The **Recognizer** status in Five Pinch
Settings reports whether the selected touchpad can be opened and used.

The override takes effect while recognition is enabled. Event numbers can change
on reconnect/reboot; if recognition stops working, clear the field to return to
automatic selection or find and enter the new path.

## Previous manual installations

A manual user copy overrides the Debian package. **Use packaged version** in
the setup application disables that copy and backs it up under
`~/.local/state/five-pinch/backups/`, preserving gesture settings. Log out and
back in, then open Five Pinch Settings again. XDG locations are respected.
Root package scripts never modify user home directories or enable extensions.

## What hardware can try it?

Any input device classified by Linux udev as a **touchpad**, regardless of its
manufacturer, model name, USB/Bluetooth/I2C/SPI/PS2 bus, or product ID. The package
can be installed without detecting a particular laptop; missing hardware is
reported in the settings instead of blocking package installation.

There are still basic data requirements, not a hardware whitelist:

- Linux Protocol B multitouch with five independently positioned contacts.
- Valid X/Y coordinate ranges and per-contact tracking IDs.
- Read access to the selected touchpad in the active local session.
- GNOME Shell 50 on Wayland (not macOS or X11).

A device that counts five fingers but only reports two positions cannot supply
an actual five-finger pinch. The recognizer reports this and tries another
candidate instead of treating partial data as five tracked fingers.

Physical axis resolution is optional. When reported, coordinates use millimetres.
Otherwise both axes use an explicitly labelled virtual **100 × 100** coordinate
space; the same three-unit distance threshold is then relative to that space,
not three physical millimetres. This fallback is approximate and may need tuning.
The status/probe output shows which coordinate mode is in use.

No additional device has been tested just because its name passes discovery.
USB, Bluetooth and non-Apple support are open experiments, not verified claims.
See [CONTRIBUTING](../CONTRIBUTING.md) to report results or submit improvements.

## Stop, uninstall or roll back

Turn off **Enable recognition**, or disable Five Pinch in the Extensions app.
The child reader stops; there is no standalone root daemon or autostart service.

To remove the package:

```bash
gnome-extensions disable five-pinch@local.codex
sudo apt remove five-pinch
```

Log out and back in to unload any already-loaded Shell code. Personal settings
and manual-install backups remain. To go back to the previous package, download
0.4.0 from Releases:

```bash
sudo apt install --allow-downgrades ./five-pinch_0.4.0_all.deb
```

Log out and back in after an upgrade or downgrade. If gestures are interfering,
disable recognition/the extension first; your ordinary pointing remains handled
by the system's existing driver.

## Practical failure modes and limits

On untested hardware it may miss gestures, recognize unwanted ones, or interact
badly with another gesture extension. Since extension code runs inside GNOME
Shell, bugs can also disrupt the desktop session; there is no zero-risk promise.

Five Pinch does not replace drivers, change firmware, patch libinput, grab the
touchpad or create virtual input devices. The recognizer opens its device
read-only and refuses to run as root. A parent pipe and one-second heartbeat
lease stop it if its supervising extension disappears. Locked/inactive sessions,
sleep and long Shell stalls suspend recognition. Lift all fingers after resuming.
Typing suppression is not validated in every application; full libinput-style
palm/thumb filtering is not implemented. Other three/four-finger handlers remain
active and can conflict with contact transitions.

The package adds the standard session `uaccess` tag only to udev-classified
touchpads (`ID_INPUT_TOUCHPAD=1`). This deliberately covers all touchpad brands,
not keyboards, arbitrary input devices or touchscreens. It does not modify input
groups or make event nodes world-readable. Standard session ACLs may include write
access; Five Pinch itself only opens the device read-only. Logout/login refreshes
access and unloads code after removal.

The reader stores no raw contact history during ordinary use. Only status and
the latest gesture appear in settings. Diagnostic captures are optional and
separate; see [development notes](DEVELOPMENT.md).

## Build and test

The source includes the recognizer, extension, diagnostics, Debian packaging,
setup/migration launcher and tests. The setup and status messages are in English.

```bash
PYTHONPATH=reader python3 -m unittest discover -s tests -v
gjs -m tests/protocol_test.js
python3 tests/check_shell_logic.py
glib-compile-schemas --strict schemas
desktop-file-validate packaging/five-pinch-settings.desktop
udevadm verify packaging/70-five-pinch.rules
python3 packaging/build_deb.py --output ../five-pinch_0.5.1_all.deb --staging-parent ../work/deb-build
```

Python 3, `dpkg-deb`, and `glib-compile-schemas` are needed to build. Debian
architecture `all` means interpreted code/data, not universal hardware support.
The builder never installs the package or runs maintainer scripts.

42 Python tests cover geometry, native frames, compatibility/discovery,
normalized fallback, control leases and setup migration. Eight protocol checks
and 13 mocked Shell checks cover action dispatch and lifecycle guards. None
substitutes for community hardware tests.

Optional checks with your current user's device access, without sudo:

```bash
python3 -I reader/service.py --probe
python3 -I reader/service.py --probe --device /dev/input/eventN
python3 tests/check_native_lifecycle.py
```

The original reference-device trial generated 18 inward and 17 outward candidates;
a separate short negative sample generated none despite 12 five-contact cycles.
The user confirmed working Debian installation and app-grid open/close actions.
The 0.5.0 discovery and reader lifecycle were checked again on that device.
Other hardware needs testers, not our permission to try it.

The older manual `install.sh` and `uninstall.sh` remain for source installations.
Do not put a manual copy on top of a packaged installation unless you deliberately
want to override it.
