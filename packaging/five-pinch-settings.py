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


def check_environment():
    if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
        raise RuntimeError('Use a GNOME Wayland session')
    version = subprocess.check_output(['gnome-shell', '--version'], text=True, timeout=5)
    if version.strip().split()[-1].split('.')[0] != '50':
        raise RuntimeError('GNOME 50 required')
    info = subprocess.run(['gnome-extensions', 'info', UUID], capture_output=True,
                          text=True, timeout=5, env={**os.environ, 'LC_ALL': 'C'})
    if info.returncode:
        raise RuntimeError('Sign out, then sign back in')
    return 'State: ACTIVE' in info.stdout


def open_preferences():
    subprocess.Popen(['gnome-extensions', 'prefs', UUID])


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
            local = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'gnome-shell/extensions' / UUID
            backup_root = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'five-pinch/backups'
            error = None
            if SYSTEM.is_dir() and not (local.exists() or local.is_symlink()):
                try:
                    if check_environment():
                        open_preferences()
                        return
                except Exception as exc:
                    error = str(exc)

            window = Adw.ApplicationWindow(application=self, title='Five Pinch',
                                          default_width=480, default_height=360)
            view = Adw.ToolbarView()
            view.add_top_bar(Adw.HeaderBar())
            status = Adw.StatusPage(icon_name='io.github.Nymeriq.FivePinch', title='Five Pinch')
            action = Gtk.Button(label='Enable', css_classes=['suggested-action', 'pill'],
                                halign=Gtk.Align.CENTER)
            status.set_child(action)
            view.set_content(status)
            window.set_content(view)

            def show_error(message):
                status.set_title(message)
                action.set_visible(False)

            if not SYSTEM.is_dir():
                show_error('Install Five Pinch first')
            elif local.exists() or local.is_symlink():
                status.set_title('Manual installation')
                action.set_label('Use packaged version')

                def migrate(_button):
                    try:
                        def disable():
                            subprocess.run(['gnome-extensions', 'disable', UUID],
                                           check=True, capture_output=True, text=True, timeout=8)
                        backup = migrate_local(local, backup_root, disable)
                        status.set_tooltip_text(f'Backup: {backup}')
                        show_error('Sign out, then sign back in')
                    except Exception as exc:
                        show_error(str(exc))
                action.connect('clicked', migrate)
            elif error:
                show_error(error)
            else:
                def enable(_button):
                    try:
                        check_environment()
                        subprocess.run(['gnome-extensions', 'enable', UUID], check=True,
                                       capture_output=True, timeout=5)
                        open_preferences()
                        window.close()
                    except Exception as exc:
                        show_error(str(exc))
                action.connect('clicked', enable)
            window.present()

    if os.geteuid() == 0:
        raise SystemExit('Run Five Pinch Settings as your desktop user, without sudo.')
    return Setup().run(sys.argv)


if __name__ == '__main__':
    raise SystemExit(main())
