"""Unit tests use a fake subprocess runner: no GNOME session or real power changes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from powerctl import Controller, PowerError, KEYS


class Fake:
    def __init__(self):
        self.values = {k: "'suspend'" for k in KEYS}
        self.calls = []
        self.fail_key = None
        self.fail_screen = False

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        status, out, err = 0, "", ""
        if argv[:2] == ["gsettings", "get"]:
            out = self.values[argv[-1]] + "\n"
        elif argv[:2] == ["gsettings", "set"]:
            if argv[-2] == self.fail_key:
                status, err = 1, "injected"
            else:
                self.values[argv[-2]] = argv[-1]
        elif "SetActive" in " ".join(argv):
            status = 1 if self.fail_screen else 0
            err = "unknown method" if self.fail_screen else ""
        return subprocess.CompletedProcess(argv, status, out, err)


class PowerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.fake = Fake()
        self.ctl = Controller(state_dir=self.base / "state", runner=self.fake)
        self.ctl.legacy_dir = self.base

    def test_awake_both_modes_and_restore(self):
        self.assertIn("ON", self.ctl.awake_toggle())
        self.assertEqual(self.fake.values, {k: "'nothing'" for k in KEYS})
        self.assertTrue(self.ctl.state_file.is_file())
        self.assertIn("OFF", self.ctl.awake_toggle())
        self.assertEqual(self.fake.values, {k: "'suspend'" for k in KEYS})

    def test_save_before_change(self):
        self.fake.fail_key = KEYS[1]
        with self.assertRaises(PowerError):
            self.ctl.awake_on()
        self.assertTrue(self.ctl.state_file.is_file())
        self.fake.fail_key = None
        self.ctl.awake_off()
        self.assertEqual(self.fake.values[KEYS[0]], "'suspend'")

    def test_legacy_shortcut_backup(self):
        (self.base / "ulauncher-awake-battery").write_text("'hibernate'\n")
        (self.base / "ulauncher-awake-ac").write_text("'logout'\n")
        self.ctl.awake_on()
        self.ctl.awake_off()
        self.assertEqual(self.fake.values[KEYS[0]], "'hibernate'")
        self.assertEqual(self.fake.values[KEYS[1]], "'logout'")

    def test_manual_change_guard(self):
        self.ctl.awake_on()
        self.fake.values[KEYS[0]] = "'hibernate'"
        with self.assertRaises(PowerError):
            self.ctl.awake_off()
        self.assertTrue(self.ctl.state_file.is_file())
        self.assertEqual(self.fake.values[KEYS[0]], "'hibernate'")
        self.assertEqual(self.fake.values[KEYS[1]], "'nothing'")

    def test_invalid_backup_fails_closed(self):
        self.ctl.state_dir.mkdir()
        self.ctl.state_file.write_text("{not json")
        with self.assertRaises(PowerError):
            self.ctl.awake_on()

    def test_display_does_not_override_mutter(self):
        self.ctl.display_sleep()
        commands = " ".join(" ".join(x) for x in self.fake.calls)
        self.assertNotIn("PowerSaveMode", commands)
        self.assertIn("org.gnome.ScreenSaver.SetActive true", commands)
        self.assertIn("lock-session", commands)

    def test_wake(self):
        self.ctl.display_wake()
        self.assertEqual(self.fake.calls[-1][-1], "false")

    def test_screensaver_failure_is_reported(self):
        self.fake.fail_screen = True
        with self.assertRaisesRegex(PowerError, "ScreenSaver"):
            self.ctl.display_sleep()

    def test_destructive_actions_are_fixed_argv(self):
        for name in ("suspend", "logout", "reboot", "shutdown"):
            self.ctl.action(name)
        self.assertEqual([x[0] for x in self.fake.calls[-4:]],
                         ["systemctl", "gnome-session-quit", "systemctl", "systemctl"])

    def test_awake_off_without_backup_is_safe(self):
        self.ctl.awake_off()
        self.assertEqual(self.fake.values[KEYS[0]], "'suspend'")


if __name__ == "__main__":
    unittest.main()
