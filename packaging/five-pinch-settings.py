#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""User-session setup for the Debian package. Never run from maintainer scripts."""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

UUID = 'five-pinch@local.codex'
SYSTEM = Path('/usr/share/gnome-shell/extensions') / UUID


def migrate_local(local, backup_root, disable):
    """Back up only our own, non-symlink user installation; preserve settings."""
    if local.is_symlink() or not local.is_dir() or local.stat().st_uid != os.getuid():
        raise RuntimeError('Refusing to move an unexpected user installation.')
    metadata = json.loads((local / 'metadata.json').read_text())
    if metadata.get('uuid') != UUID:
        raise RuntimeError('The user installation has an unexpected UUID.')
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = backup_root / ('manual-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    disable()
    shutil.move(str(local), str(backup))
    return backup


def main():
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Adw, Gtk

    Gtk.Window.set_default_icon_name('io.github.Nymeriq.FivePinch')

    class Setup(Adw.Application):
        def __init__(self):
            super().__init__(application_id='io.github.fivepinch.Settings')

        def do_activate(self):
            if self.get_active_window():
                self.get_active_window().present()
                return
            window = Adw.ApplicationWindow(application=self, title='Five Pinch Settings',
                                          default_width=560, default_height=380)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                          margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
            box.append(Gtk.Label(label='Five Pinch', css_classes=['title-1']))
            message = Gtk.Label(wrap=True, xalign=0)
            box.append(message)
            action = Gtk.Button(css_classes=['suggested-action'])
            box.append(action)
            box.append(Gtk.Label(wrap=True, xalign=0,
                label='Experimental: GNOME 50 / Wayland. Try any touchpad with five tracked contacts. '
                      'Tested on MacBook Pro 2017 only. Community tests and pull requests are welcome.'))
            window.set_content(box)
            local = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'gnome-shell/extensions' / UUID
            backup_root = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'five-pinch/backups'
            if not SYSTEM.is_dir():
                message.set_label('The Debian package is not installed. Install the .deb package first.')
                action.set_visible(False)
            elif local.exists() or local.is_symlink():
                message.set_label('A manual user installation overrides the Debian package. '
                    'Use the packaged version to back up that installation and preserve your gesture settings. '
                    'You will then need to log out and back in.')
                action.set_label('Use packaged version')

                def migrate(_button):
                    try:
                        def disable():
                            subprocess.run(['gnome-extensions', 'disable', UUID],
                                           check=True, capture_output=True, text=True, timeout=8)
                        backup = migrate_local(local, backup_root, disable)
                        message.set_label(f'Previous installation saved to:\n{backup}\n\n'
                            'Save your work, then log out and back in. Open Five Pinch Settings again afterwards.')
                        action.set_sensitive(False)
                    except Exception as exc:
                        message.set_label(f'Could not switch installations: {exc}')
                action.connect('clicked', migrate)
            else:
                message.set_label('Enable the extension and open its settings. On first installation, '
                    'log out and back in if GNOME has not discovered it yet. '
                    'Start with Detect only before selecting gesture actions.')
                action.set_label('Enable and open settings')

                def open_settings(_button):
                    try:
                        if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
                            raise RuntimeError('Please use a GNOME Wayland session.')
                        version = subprocess.check_output(['gnome-shell', '--version'], text=True, timeout=5)
                        if version.strip().split()[-1].split('.')[0] != '50':
                            raise RuntimeError('This release requires GNOME Shell 50.')
                        info = subprocess.run(['gnome-extensions', 'info', UUID], capture_output=True, timeout=5)
                        if info.returncode:
                            raise RuntimeError('Log out and back in so GNOME can discover Five Pinch, then try again.')
                        subprocess.run(['gnome-extensions', 'enable', UUID], check=True,
                                       capture_output=True, timeout=5)
                        subprocess.Popen(['gnome-extensions', 'prefs', UUID])
                        window.close()
                    except Exception as exc:
                        message.set_label(str(exc))
                action.connect('clicked', open_settings)
            window.present()

    if os.geteuid() == 0:
        raise SystemExit('Run Five Pinch Settings as your desktop user, without sudo.')
    return Setup().run(sys.argv)


if __name__ == '__main__':
    raise SystemExit(main())
