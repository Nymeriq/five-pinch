# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).resolve().parents[1] / 'packaging/five-pinch-reset.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class Settings:
    def __init__(self):
        self.data = {'enabled-extensions': ['before', cleanup.UUID, 'after'],
                     'disabled-extensions': ['other', cleanup.UUID]}
    def get_strv(self, key):
        return self.data[key]
    def set_strv(self, key, value):
        self.data[key] = value


class RemovalTests(unittest.TestCase):
    def test_disable_then_reset_only_our_data(self):
        settings = Settings()
        commands = []
        def run(command, **kwargs):
            commands.append(command)
            if len(commands) == 1:
                self.assertIn(cleanup.UUID, settings.data['enabled-extensions'])
            return subprocess.CompletedProcess(command, 0)
        cleanup.reset_session(settings, run)
        self.assertEqual(settings.data, {'enabled-extensions': ['before', 'after'],
                                         'disabled-extensions': ['other']})
        self.assertEqual(commands, [['/usr/bin/gnome-extensions', 'disable', cleanup.UUID],
                                   ['/usr/bin/dconf', 'reset', '-f', cleanup.SETTINGS_PATH]])

    def test_settings_reset_errors_are_reported(self):
        def run(command, **kwargs):
            if 'dconf' in command[0]:
                raise subprocess.CalledProcessError(1, command)
            return subprocess.CompletedProcess(command, 0)
        with self.assertRaises(subprocess.CalledProcessError):
            cleanup.reset_session(Settings(), run)

    def test_upgrade_never_runs_session_cleanup(self):
        script = (Path(__file__).resolve().parents[1] / 'packaging/prerm').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'called'
            # Use a harmless marker in place of the real reset command.
            script = script.replace('/usr/bin/python3 -I /usr/bin/five-pinch-reset --active-sessions',
                                    f'touch {marker}')
            hook = Path(tmp) / 'prerm'
            hook.write_text(script)
            for action in ('upgrade', 'deconfigure', 'failed-upgrade'):
                subprocess.run(['sh', str(hook), action], check=True)
                self.assertFalse(marker.exists())
            subprocess.run(['sh', str(hook), 'remove'], check=True)
            self.assertTrue(marker.exists())

    def test_only_purge_removes_our_repository_files(self):
        script = (Path(__file__).resolve().parents[1] / 'packaging/postrm').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            # Never run the real system udev or delete real /etc files in tests.
            script = script.replace('if command -v udevadm >/dev/null 2>&1; then', 'if false; then')
            script = script.replace('/etc/apt/', tmp + '/')
            ours = [Path(tmp) / p for p in ('sources.list.d/five-pinch.sources',
                                          'preferences.d/five-pinch', 'keyrings/five-pinch.gpg')]
            other = Path(tmp) / 'sources.list.d/another.sources'
            for p in ours + [other]:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('keep')
            hook = Path(tmp) / 'postrm'
            hook.write_text(script)
            for action in ('upgrade', 'remove'):
                subprocess.run(['sh', str(hook), action], check=True, capture_output=True)
                self.assertTrue(all(p.exists() for p in ours))
            subprocess.run(['sh', str(hook), 'purge'], check=True, capture_output=True)
            self.assertTrue(all(not p.exists() for p in ours))
            self.assertTrue(other.exists())

    def test_session_delegation_uses_fixed_code_and_clean_user_environment(self):
        from types import SimpleNamespace
        account = SimpleNamespace(pw_name='tester', pw_uid=1000, pw_dir='/home/tester')
        with patch.object(cleanup.os, 'geteuid', return_value=0), \
             patch.object(cleanup, 'active_users', return_value=[(account, Path('/run/user/1000'))]), \
             patch.object(cleanup.subprocess, 'run') as run:
            cleanup.reset_active_sessions()
        command = run.call_args.args[0]
        self.assertEqual(command[:6], ['/usr/sbin/runuser', '-u', 'tester', '--', '/usr/bin/env', '-i'])
        self.assertIn('DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus', command)
        self.assertEqual(command[-3:-1], ['/usr/bin/python3', '-I'])
        self.assertNotIn('--active-sessions', command)


if __name__ == '__main__':
    unittest.main()
