# SPDX-License-Identifier: MIT
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

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


if __name__ == '__main__':
    unittest.main()
