"""Isolated unit tests: neither the real system nor its power settings are changed."""
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
        self.fail_value = None
        self.fail_screen = False

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        code, out, err = 0, "", ""
        if argv[:2] == ["gsettings", "get"]:
            out = self.values[argv[-1]] + "\n"
        elif argv[:2] == ["gsettings", "set"]:
            key, value = argv[-2:]
            if key == self.fail_key and (self.fail_value is None or self.fail_value == value):
                code, err = 1, "injected"
            else:
                self.values[key] = value
        elif "SetActive" in " ".join(argv):
            code = 1 if self.fail_screen else 0
            err = "unknown method" if self.fail_screen else ""
        return subprocess.CompletedProcess(argv, code, out, err)


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
        self.assertEqual(self.ctl.status()["state"], "ON")
        self.assertTrue(self.ctl.state_file.is_file())
        self.assertIn("OFF", self.ctl.awake_toggle())
        self.assertEqual(self.fake.values, {k: "'suspend'" for k in KEYS})
        self.assertEqual(self.ctl.status()["state"], "OFF")

    def test_on_failure_restores_both_and_clears_new_backup(self):
        self.fake.fail_key = KEYS[1]
        with self.assertRaisesRegex(PowerError, "rolled back"):
            self.ctl.awake_on()
        self.assertFalse(self.ctl.state_file.exists())
        self.assertEqual(self.fake.values, {k: "'suspend'" for k in KEYS})

    def test_off_failure_restores_on_and_preserves_backup(self):
        self.ctl.awake_on()
        self.fake.fail_key, self.fake.fail_value = KEYS[1], "'suspend'"
        with self.assertRaisesRegex(PowerError, "rolled back"):
            self.ctl.awake_off()
        self.assertEqual(self.fake.values, {k: "'nothing'" for k in KEYS})
        self.assertTrue(self.ctl.state_file.exists())

    def test_legacy_shortcut_backup(self):
        (self.base / "ulauncher-awake-battery").write_text("'hibernate'\n")
        (self.base / "ulauncher-awake-ac").write_text("'logout'\n")
        self.ctl.awake_on()
        self.ctl.awake_off()
        self.assertEqual(self.fake.values[KEYS[0]], "'hibernate'")
        self.assertEqual(self.fake.values[KEYS[1]], "'logout'")

    def test_manual_change_guard_for_off(self):
        self.ctl.awake_on()
        self.fake.values[KEYS[0]] = "'hibernate'"
        self.assertEqual(self.ctl.status()["state"], "INCONSISTENT")
        with self.assertRaises(PowerError):
            self.ctl.awake_off()
        self.assertTrue(self.ctl.state_file.is_file())
        self.assertEqual(self.fake.values[KEYS[0]], "'hibernate'")
        self.assertEqual(self.fake.values[KEYS[1]], "'nothing'")

    def test_manual_change_guard_for_repeated_on(self):
        self.ctl.awake_on()
        self.fake.values[KEYS[1]] = "'hibernate'"
        with self.assertRaisesRegex(PowerError, "External change"):
            self.ctl.awake_on()
        self.assertEqual(self.fake.values[KEYS[1]], "'hibernate'")

    def test_invalid_backup_fails_closed(self):
        self.ctl.state_dir.mkdir()
        self.ctl.state_file.write_text("{not json")
        with self.assertRaises(PowerError):
            self.ctl.awake_on()

    def test_display_does_not_override_mutter_or_suspend(self):
        self.ctl.display_sleep()
        commands = " ".join(" ".join(x) for x in self.fake.calls)
        self.assertNotIn("PowerSaveMode", commands)
        self.assertNotIn("systemctl suspend", commands)
        self.assertIn("org.gnome.ScreenSaver.SetActive true", commands)
        self.assertIn("lock-session", commands)
        self.assertEqual(self.ctl.status()["state"], "ON")

    def test_screensaver_failure_is_reported(self):
        self.fake.fail_screen = True
        with self.assertRaisesRegex(PowerError, "ScreenSaver"):
            self.ctl.display_sleep()

    def test_no_display_wake_action(self):
        with self.assertRaisesRegex(PowerError, "Unknown operation"):
            self.ctl.action("display-wake")

    def test_destructive_actions_are_fixed_argv(self):
        for name in ("suspend", "logout", "reboot", "shutdown"):
            self.ctl.action(name)
        self.assertEqual([x[0] for x in self.fake.calls[-4:]],
                         ["systemctl", "gnome-session-quit", "systemctl", "systemctl"])

    def test_awake_off_without_backup_is_safe(self):
        self.ctl.awake_off()
        self.assertEqual(self.fake.values[KEYS[0]], "'suspend'")

    def test_lock_serialization_file_is_private(self):
        with self.ctl.state_lock():
            self.assertTrue((self.ctl.state_dir / ".lock").exists())


if __name__ == "__main__":
    unittest.main()
