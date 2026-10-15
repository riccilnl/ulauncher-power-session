"""One-Enter behavior tests: simulate shell and desktop APIs without power changes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop_shortcuts import ACTIONS, MARKER, PREFIX, ensure_launchers, remove_launchers
from desktop_action import DIRECT, DANGEROUS, dispatch

class NativeLaunchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_no_keyword_layer(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(manifest["preferences"], [])
        self.assertEqual(len(ACTIONS), 7)
        self.assertEqual(set(DIRECT), {a[0] for a in ACTIONS})

    def test_registration_is_idempotent(self):
        files = ensure_launchers(self.dir)
        self.assertEqual(len(files), 7)
        self.assertEqual(ensure_launchers(self.dir), [])
        for path in files:
            content = path.read_text()
            self.assertIn("Type=Application", content)
            self.assertIn("Terminal=false", content)
            self.assertIn("desktop_action.py", content)
            self.assertIn(MARKER, content)

    def test_foreign_file_not_overwritten(self):
        existing = self.dir / f"{PREFIX}-sleep.desktop"
        existing.write_text("[Desktop Entry]\nName=Foreign\n")
        with self.assertRaisesRegex(RuntimeError, "unmanaged"):
            ensure_launchers(self.dir)
        self.assertIn("Foreign", existing.read_text())

    def test_remove_only_own_files(self):
        ensure_launchers(self.dir)
        other = self.dir / "unrelated.desktop"
        other.write_text("keep")
        self.assertEqual(len(remove_launchers(self.dir)), 7)
        self.assertEqual(other.read_text(), "keep")
        self.assertEqual(remove_launchers(self.dir), [])

    def test_GNOME_desktop_files_and_native_search(self):
        try:
            import gi
        except ImportError:
            self.skipTest("PyGObject unavailable; GNOME integration needs Fedora")
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio
        from ulauncher.utils.fuzzy_search import get_score
        for file in ensure_launchers(self.dir):
            app = Gio.DesktopAppInfo.new_from_filename(str(file))
            self.assertIsNotNone(app, str(file))
            self.assertEqual(app.get_string("Type"), "Application")
            self.assertIn("desktop_action.py", app.get_string("Exec"))
            self.assertIsNotNone(app.get_icon())
        self.assertGreaterEqual(get_score("sleep", "Sleep Display"), 75)

    def test_sleep_first_enter_never_confirms(self):
        run = Mock(side_effect=AssertionError("must not call zenity"))
        spawn = Mock()
        self.assertEqual(dispatch("sleep", runner=run, spawner=spawn, notifier=Mock()), 0)
        self.assertEqual(spawn.call_count, 1)
        self.assertIn("display-sleep", spawn.call_args.args[0])

    def test_awake_one_process(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, "Awake ON", ""))
        self.assertEqual(dispatch("awake", runner=run, notifier=Mock()), 0)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-1], "awake-toggle")

    def test_dangerous_operations_cancel_without_execution(self):
        for name in DANGEROUS:
            run = Mock(return_value=subprocess.CompletedProcess([], 1, "", ""))
            self.assertEqual(dispatch(name, runner=run, notifier=Mock()), 0)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][0], "zenity")

    def test_missing_confirmation_dialog_fails_closed(self):
        run = Mock(side_effect=OSError("zenity not installed"))
        notice = Mock()
        self.assertEqual(dispatch("shutdown", runner=run, notifier=notice), 1)
        self.assertEqual(run.call_count, 1)
        notice.assert_called_once()

    def test_dangerous_confirm_then_execute(self):
        run = Mock(side_effect=[subprocess.CompletedProcess([], 0, "", ""),
                                subprocess.CompletedProcess([], 0, "", "")])
        self.assertEqual(dispatch("restart", runner=run, notifier=Mock()), 0)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[-1].args[0][-1], "reboot")

if __name__ == "__main__":
    unittest.main()
