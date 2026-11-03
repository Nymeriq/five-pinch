# SPDX-License-Identifier: MIT
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

path = Path(__file__).resolve().parents[1] / 'packaging/five-pinch-settings.py'
spec = importlib.util.spec_from_file_location('five_pinch_setup', path)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def test_migration_preserves_files_and_disables_before_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / setup.UUID
            local.mkdir()
            (local / 'metadata.json').write_text(json.dumps({'uuid': setup.UUID}))
            (local / 'prefs.js').write_text('original')
            called = []
            def disable():
                self.assertTrue(local.exists())
                called.append(True)
            backup = setup.migrate_local(local, root / 'backups', disable)
            self.assertEqual(called, [True])
            self.assertFalse(local.exists())
            self.assertEqual((backup / 'prefs.js').read_text(), 'original')

    def test_unexpected_uuid_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / 'extension'
            local.mkdir()
            (local / 'metadata.json').write_text('{"uuid":"other-extension"}')
            with self.assertRaises(RuntimeError):
                setup.migrate_local(local, Path(tmp) / 'backups', lambda: self.fail('must not disable'))
            self.assertTrue(local.exists())

    def test_disable_failure_leaves_installation_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / setup.UUID
            local.mkdir()
            (local / 'metadata.json').write_text(json.dumps({'uuid': setup.UUID}))
            def fail():
                raise RuntimeError('Disable failed')
            with self.assertRaises(RuntimeError):
                setup.migrate_local(local, Path(tmp) / 'backups', fail)
            self.assertTrue(local.exists())

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'target'
            target.mkdir()
            link = root / 'link'
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                setup.migrate_local(link, root / 'backups', lambda: self.fail('must not disable'))
            self.assertTrue(link.is_symlink())


class LauncherTests(unittest.TestCase):
    def test_active_extension_can_open_directly(self):
        with patch.dict(setup.os.environ, {'XDG_SESSION_TYPE': 'wayland'}), \
             patch.object(setup.subprocess, 'check_output', return_value='GNOME Shell 50.1'), \
             patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'State: ACTIVE')):
            self.assertTrue(setup.check_environment())

    def test_inactive_extension_requires_explicit_activation(self):
        with patch.dict(setup.os.environ, {'XDG_SESSION_TYPE': 'wayland'}), \
             patch.object(setup.subprocess, 'check_output', return_value='GNOME Shell 50.1'), \
             patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'State: INITIALIZED')):
            self.assertFalse(setup.check_environment())

    def test_missing_extension_requires_new_session(self):
        with patch.dict(setup.os.environ, {'XDG_SESSION_TYPE': 'wayland'}), \
             patch.object(setup.subprocess, 'check_output', return_value='GNOME Shell 50.1'), \
             patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '')):
            with self.assertRaisesRegex(RuntimeError, 'Sign out'):
                setup.check_environment()

    def test_environment_checks_precede_activation(self):
        with patch.object(setup.subprocess, 'run') as run:
            with patch.dict(setup.os.environ, {'XDG_SESSION_TYPE': 'x11'}):
                with self.assertRaisesRegex(RuntimeError, 'Wayland'):
                    setup.check_environment()
            with patch.dict(setup.os.environ, {'XDG_SESSION_TYPE': 'wayland'}), \
                 patch.object(setup.subprocess, 'check_output', return_value='GNOME Shell 49.0'):
                with self.assertRaisesRegex(RuntimeError, 'GNOME 50'):
                    setup.check_environment()
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
