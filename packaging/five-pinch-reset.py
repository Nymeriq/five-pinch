#!/usr/bin/python3 -I
# SPDX-License-Identifier: MIT
"""Reset only Five Pinch. Root mode delegates to users with live session buses."""
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys

UUID = 'five-pinch@local.codex'
SETTINGS_PATH = '/org/gnome/shell/extensions/five-pinch/'


def reset_session(shell_settings, run=subprocess.run):
    # Disable through Shell first so its existing disable() stops the reader.
    result = run(['/usr/bin/gnome-extensions', 'disable', UUID],
                 capture_output=True, timeout=8)
    if result.returncode:
        print('Five Pinch: could not confirm live Shell disable; log out after removal.', file=sys.stderr)
    # Remove only our UUID, preserving other extension membership and ordering.
    for key in ('enabled-extensions', 'disabled-extensions'):
        values = shell_settings.get_strv(key)
        if UUID in values:
            shell_settings.set_strv(key, [value for value in values if value != UUID])
    run(['/usr/bin/dconf', 'reset', '-f', SETTINGS_PATH],
        capture_output=True, check=True, timeout=8)


def active_users(runtime=Path('/run/user'), lookup=pwd.getpwuid):
    if not runtime.exists():
        return
    for directory in sorted(runtime.iterdir()):
        if not directory.name.isdecimal() or directory.is_symlink():
            continue
        uid = int(directory.name)
        if uid == 0:
            continue
        try:
            account = lookup(uid)
            if directory.stat().st_uid != uid or not stat.S_ISSOCK((directory / 'bus').stat().st_mode):
                continue
        except (KeyError, FileNotFoundError, PermissionError):
            continue
        yield account, directory


def reset_active_sessions():
    if os.geteuid() != 0:
        raise RuntimeError('Active-session cleanup must be invoked by package removal.')
    script = str(Path(__file__).resolve())
    for account, runtime in active_users():
        # Do not read or edit user files as root. Fixed code runs as that user,
        # with a clean environment and Python isolated mode.
        command = ['/usr/sbin/runuser', '-u', account.pw_name, '--',
                   '/usr/bin/env', '-i', 'PATH=/usr/bin:/bin',
                   f'HOME={account.pw_dir}', f'USER={account.pw_name}',
                   f'LOGNAME={account.pw_name}', f'XDG_RUNTIME_DIR={runtime}',
                   f'DBUS_SESSION_BUS_ADDRESS=unix:path={runtime}/bus',
                   '/usr/bin/python3', '-I', script]
        try:
            subprocess.run(command, check=True, timeout=25)
        except (OSError, subprocess.SubprocessError):
            print(f'Five Pinch: session cleanup incomplete for UID {account.pw_uid}; '
                  'run five-pinch-reset before removal, or log out afterwards.', file=sys.stderr)


def main():
    if sys.argv[1:] == ['--active-sessions']:
        reset_active_sessions()
        return
    if sys.argv[1:]:
        raise RuntimeError('Usage: five-pinch-reset (as your own desktop user)')
    if os.geteuid() == 0:
        raise RuntimeError('Run five-pinch-reset as your own desktop user, without sudo.')
    from gi.repository import Gio
    reset_session(Gio.Settings.new('org.gnome.shell'))
    Gio.Settings.sync()
    print('Five Pinch disabled and its settings reset. Other extensions were not changed.')


if __name__ == '__main__':
    main()
