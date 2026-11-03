#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build without installing or executing package maintainer scripts."""
import argparse
import gzip
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

VERSION = '0.6.6'
UUID = 'five-pinch@local.codex'
SOURCE = Path(__file__).resolve().parents[1]


def build(output, staging_parent):
    staging_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='five-pinch-deb-', dir=staging_parent) as tmp:
        root = Path(tmp)
        extension = root / 'usr/share/gnome-shell/extensions' / UUID
        extension.mkdir(parents=True)
        for name in ['metadata.json', 'extension.js', 'prefs.js', 'protocol.js', 'pinchTailGuard.js', 'rinertiaGuard.js', 'LICENSE']:
            shutil.copyfile(SOURCE / name, extension / name)
        (extension / 'reader').mkdir()
        for name in ['service.py', 'detector.py']:
            shutil.copyfile(SOURCE / 'reader' / name, extension / 'reader' / name)
        (extension / 'schemas').mkdir()
        for file in (SOURCE / 'schemas').glob('*.xml'):
            shutil.copyfile(file, extension / 'schemas' / file.name)
        subprocess.run(['glib-compile-schemas', '--strict', str(extension / 'schemas')], check=True)
        for src, dest in [
            ('five-pinch-settings.py', 'usr/bin/five-pinch-settings'),
            ('five-pinch-reset.py', 'usr/bin/five-pinch-reset'),
            ('five-pinch-settings.desktop', 'usr/share/applications/five-pinch-settings.desktop'),
            ('70-five-pinch.rules', 'usr/lib/udev/rules.d/70-five-pinch.rules')]:
            path = root / dest
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / 'packaging' / src, path)
        (root / 'usr/bin/five-pinch-settings').chmod(0o755)
        (root / 'usr/bin/five-pinch-reset').chmod(0o755)
        doc = root / 'usr/share/doc/five-pinch'
        doc.mkdir(parents=True)
        shutil.copyfile(SOURCE / 'README.md', doc / 'README.md')
        (doc / 'copyright').write_text('Five Pinch\nCopyright (c) 2026 Five Pinch contributors\n\n' +
                                        (SOURCE / 'LICENSE').read_text())
        with gzip.GzipFile(filename=str(doc / 'changelog.gz'), mode='wb', mtime=0) as file:
            file.write(b'five-pinch (0.6.6) experimental; urgency=low\n\n'
                       b'  * Add scoped rinertia scrolling protection during five-contact interactions.\n\n'
                       b' -- Five Pinch contributors  Tue, 03 Nov 2026 12:00:00 +0100\n')
        control = root / 'DEBIAN'
        control.mkdir()
        size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) // 1024 + 1
        (control / 'control').write_text(f'''Package: five-pinch
Version: {VERSION}
Section: gnome
Priority: optional
Architecture: all
Maintainer: Five Pinch contributors
Installed-Size: {size}
Depends: gnome-shell (>= 50), gnome-shell (<< 51), python3 (>= 3.10), python3-gi, gir1.2-adw-1, libglib2.0-bin, dconf-cli, util-linux, dconf-gsettings-backend | gsettings-backend, udev
Description: Experimental five-finger pinch gestures for GNOME 50
 English settings, app-grid and overview actions, and a supervised read-only
 touchpad recognizer. Any udev-classified touchpad can be tried, regardless of brand or bus.
 Requires GNOME 50 on Wayland and at least five coordinate slots.
''')
        for name in ['prerm', 'postinst', 'postrm']:
            shutil.copyfile(SOURCE / 'packaging' / name, control / name)
            (control / name).chmod(0o755)
        checksums = []
        for path in sorted(root.rglob('*')):
            if path.is_file() and control not in path.parents:
                checksums.append(f'{hashlib.md5(path.read_bytes()).hexdigest()}  {path.relative_to(root)}')
        (control / 'md5sums').write_text('\n'.join(checksums) + '\n')
        # Independent of the builder's umask; do not package a private tempdir
        # as the root directory or group-writable installed source files.
        root.chmod(0o755)
        executables = {root / 'usr/bin/five-pinch-settings',
                       root / 'usr/bin/five-pinch-reset',
                       control / 'prerm', control / 'postinst', control / 'postrm'}
        for path in root.rglob('*'):
            path.chmod(0o755 if path.is_dir() or path in executables else 0o644)
        subprocess.run(['dpkg-deb', '--root-owner-group', '-Zxz', '--build', str(root), str(output.resolve())], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--staging-parent', required=True, type=Path)
    args = parser.parse_args()
    build(args.output, args.staging_parent)
