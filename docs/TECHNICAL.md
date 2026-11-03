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
Root package scripts never enable extensions or edit user settings databases directly.
Removal delegates Five Pinch cleanup to reachable sessions as the owning user.

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
five-pinch-reset
sudo apt purge five-pinch
```

Log out and back in to unload any already-loaded Shell code. Five Pinch settings are reset for the current user;
intentional manual-install backups remain. See [full removal](APT.md#revert-or-remove)
for shared machines and repository cleanup. To go back to the previous package, download
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
python3 packaging/build_deb.py --output ../five-pinch_0.6.6_all.deb --staging-parent ../work/deb-build
```

Python 3, `dpkg-deb`, and `glib-compile-schemas` are needed to build. Debian
architecture `all` means interpreted code/data, not universal hardware support.
The builder never installs the package or runs maintainer scripts.

55 Python tests cover geometry, native frames, compatibility/discovery,
normalized fallback, control leases and setup migration. Protocol and pinch-tail checks
and mocked Shell checks cover action dispatch and lifecycle guards. None
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

## Sensitivity profiles

| Profile | Median scale change | Median pair distance | Earliest recognition | Timeout | Pair direction margin |
| --- | --- | --- | --- | --- | --- |
| Original | 18% | 3.0 | 80 ms | 2 s | 6% |
| Balanced (default) | 12% | 1.8 | 60 ms | 3 s | 4% |
| Relaxed | 8% | 1.2 | 60 ms | 3 s | 2.5% |

Distances are millimetres on devices with physical resolution, otherwise the
normalized coordinate units described above. At least seven of ten finger pairs
must still move coherently. Five stable contact identities and lifting all
fingers between attempts are still required. Original keeps the old algorithm's
thresholds, including its timeout. The more sensitive modes are tuning starting
points, not validated claims about detection accuracy on every touchpad.

Select Original in settings to restore the earlier recognition feel immediately.
For a full package rollback, disable the extension and install the previous
`.deb` with `sudo apt install --allow-downgrades ./five-pinch_0.5.1_all.deb`, then
log out and back in. A newer sensitivity setting may remain stored but is ignored
by 0.5.1. Your action choices are preserved.

## Pinch-tail protection (experimental)

The stage capture handler filters complete swipe sequences only when their BEGIN
falls after the reader observes five simultaneous contacts and no later than its full
hand lift, on the same `/dev/input/eventN` source. A `pinch-end` message carries
the lift timestamp. Queued old native events can still be filtered, while a new
hand cycle after that timestamp is passed through. Two-finger scrolls are never
claimed; standalone one/two/three/four-finger gestures do not arm the guard.

No private Shell tracker fields or global input settings are changed. Swipes
already underway when the contact notification arrives are left alone to avoid orphaning a Shell
animation. IPC scheduling races can therefore still allow a competing native
swipe. A missing release expires after three seconds; disable, lock/session
pause or reader restart clears the guard. If both actions are diagnostic/disabled, contact events do not
arm it. At least one configured desktop action is required. `Protect pinch ending` restores prior behavior when switched off.

Run `gjs -m tests/pinch_tail_test.js` for state and timestamp checks. These do
not prove ordering against a live compositor; hardware/user feedback is needed.

## rinertia integration (experimental)

The reference-device diagnostic capture confirmed a scroll-driven workspace
change, via `overview._onScrollEvent` → `workspacesView._onScrollEvent` →
`windowManager.handleWorkspaceScroll`. The source was the virtual mouse named
`rinertia Virtual Device`, distinct from the physical touchpad. A native swipe
filter alone cannot intercept that scroll path.

The separate `protect-rinertia` switch filters only SCROLL events with this
runtime source name, after five physical contacts on the supervised touchpad.
No service discovery, root access, process suspension, external-device input
reader or rinertia configuration modification is required. An installed but
inactive rinertia has no effect. A renamed virtual device is not matched.

The physical reader reports contact-cycle start, five contacts and full hand
lift with monotonic timestamps. New contact-cycle start clears prior momentum
protection, including for one/two/three/four-contact gestures. At hand lift, a
bounded momentum phase begins: a 120 ms gap ends it, with a hard maximum of two
seconds. The active contact phase has a three-second watchdog. Lock, disable,
reader restart, typing pause or uninstall clears the guard. Another physical
mouse is never filtered. Multiple physical touchpads feeding the same virtual
rinertia pointer cannot be perfectly attributed; IPC timing can also affect
edge cases. Live hardware testing remains necessary.

Run `gjs -m tests/rinertia_guard_test.js` for scope, expiry, new-cycle and recorded
failure-timing regression checks. Diagnostic traces are opt-in and turned off by
default. The session recorder restores its previous logging setting when stopped
normally; no raw logs are published with the source.
