# Development and validation

## Why there are two components

The original investigation found that five physical contacts appeared in
libinput's internal debug output, but no five-finger pinch event was emitted.
The inspected libinput gesture code processed up to four contacts. Adding a
fifth option to a Shell gesture handler alone would not supply missing events.

Five Pinch therefore combines a read-only Linux input reader with a GNOME 50
extension. The reader works with per-contact coordinates; the extension applies
the chosen Shell action. This avoids replacing the system libinput library.

The project is independently written. It does not include source from Custom
Touchpad Gestures. That project's inspected main branch had unresolved merge
markers and no clear license declaration, so it was not used as the code base.

## Implemented milestones

1. A diagnostic five-contact recognizer and synthetic geometry tests.
2. Native Protocol B input reading without third-party Python packages.
3. Live hardware capture and replay on a 2017 MacBook Pro Apple SPI Touchpad.
4. A supervised reader integrated with a separate GNOME extension.
5. Independent app-grid open/close and overview open/close actions.
6. English settings, Debian packaging, and backup-based manual-install migration.
7. Experimental Apple SPI family acceptance using device capability checks.

The current reference device exposes 11 coordinate slots and X/Y resolutions
of 96/94 units per millimetre. The first positive capture generated 18 inward
and 17 outward candidates. A separate short negative capture generated no
candidates despite 12 cycles reaching five contacts. These samples establish
initial feasibility, not an accuracy guarantee or validation of other models.

The reference user also confirmed that Debian installation and actual app-grid
open/close actions work. Other SPI models still require independent tests.

## Diagnostics

`tools/diagnostics/capture_native.py` reads one explicitly selected Apple SPI
Touchpad for a bounded interval. It prints candidates and writes coordinate
frames for offline analysis. It does not perform desktop actions or install
anything. Unlike the normal reader, it deliberately records raw touch geometry.

Identify the current event node first; event numbers can change after reboot.
With suitable read access, from the repository root:

```bash
python3 tools/diagnostics/capture_native.py \
  --device /dev/input/eventN --output /tmp/five-pinch-test.jsonl --seconds 45
python3 tools/diagnostics/analyze_capture.py /tmp/five-pinch-test.jsonl
```

The diagnostics reuse `reader/detector.py`, so offline replay uses the same
geometry logic as the deployed recognizer. JSONL captures are gitignored;
test summaries, rather than personal raw recordings, belong in hardware reports.
Original local recordings and backups are not part of this public repository.

## Limits still to test

- Additional Apple SPI models, firmware variants and hand geometries.
- Extended ordinary use, palm/thumb contacts and typing in different applications.
- Sleep, session switching, lock/unlock and recovery after input loss.
- Interaction with GNOME's built-in three/four-finger gestures and other extensions.

See [CONTRIBUTING](../CONTRIBUTING.md) for hardware reports and the
[README](../README.md) for package builds, installation and rollback.
