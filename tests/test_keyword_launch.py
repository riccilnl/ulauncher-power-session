"""One Enter from a searchable Ulauncher v5 keyword executes immediately.

All power operations are mocked. No real GNOME power actions or user files.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Ubuntu GitHub CI doesn't ship Ulauncher. Stub only its Extension API, while
# using the *real* implementation on Fedora for platform integration testing.
try:
    import ulauncher.api.client.Extension  # noqa: F401
except ImportError:
    def stub(name, **values):
        module = types.ModuleType(name)
        module.__dict__.update(values)
        sys.modules[name] = module
    for name in ("ulauncher", "ulauncher.api", "ulauncher.api.client",
                 "ulauncher.api.shared", "ulauncher.api.shared.event",
                 "ulauncher.api.shared.action"):
        stub(name)
    class StubExtension:
        def __init__(self):
            self.preferences = {}
            self.logger = Mock()
        def subscribe(self, *args):
            pass
    class StubListener:
        pass
    class StubHideWindowAction:
        pass
    stub("ulauncher.api.client.Extension", Extension=StubExtension)
    stub("ulauncher.api.client.EventListener", EventListener=StubListener)
    sys.modules["ulauncher.api.shared.event"].KeywordQueryEvent = object
    stub("ulauncher.api.shared.action.HideWindowAction",
         HideWindowAction=StubHideWindowAction)

import main
from action import DIRECT, DANGEROUS, dispatch

class FakeEvent:
    def __init__(self, keyword, argument=None):
        self.keyword, self.argument = keyword, argument
    def get_keyword(self):
        return self.keyword
    def get_argument(self):
        return self.argument

class KeywordTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "manifest.json").read_text())
        self.preferences = {
            item["id"]: item["default_value"]
            for item in self.manifest["preferences"]
        }
        self.extension = types.SimpleNamespace(preferences=self.preferences)

    def test_seven_searchable_plugin_keywords_no_power_prefix(self):
        self.assertEqual(len(self.preferences), 7)
        self.assertNotIn("power", self.preferences.values())
        self.assertEqual({val[1] for val in main.COMMANDS.values()}, set(DIRECT))
        for pref_id, (default, slug) in main.COMMANDS.items():
            self.assertEqual(self.preferences[pref_id], default)
            self.assertEqual(main.action_for_keyword(default, self.preferences), slug)

    def test_first_enter_dispatches_sleep_and_hides_without_second_result(self):
        spawn = Mock()
        listener = main.ImmediateKeywords(spawner=spawn, clock=lambda: 42)
        reply = listener.on_event(FakeEvent("sleep"), self.extension)
        self.assertIsInstance(reply, main.HideWindowAction)
        self.assertEqual(spawn.call_count, 1)
        self.assertEqual(spawn.call_args.args[0][-1], "sleep")
        self.assertEqual(spawn.call_args.args[0][-2], str(ROOT / "action.py"))

    def test_double_event_does_not_toggle_awake_twice(self):
        now = [10.0]
        spawn = Mock()
        listener = main.ImmediateKeywords(spawner=spawn, clock=lambda: now[0])
        listener.on_event(FakeEvent("awake"), self.extension)
        listener.on_event(FakeEvent("awake"), self.extension)
        self.assertEqual(spawn.call_count, 1)
        now[0] += main.RETRIGGER_SECONDS + 0.01
        listener.on_event(FakeEvent("awake"), self.extension)
        self.assertEqual(spawn.call_count, 2)

    def test_arguments_unknown_keywords_and_custom_names(self):
        spawn = Mock()
        listener = main.ImmediateKeywords(spawner=spawn, clock=lambda: 1)
        self.assertIsNone(listener.on_event(FakeEvent("sleep", "display"), self.extension))
        self.assertIsNone(listener.on_event(FakeEvent("power"), self.extension))
        self.assertEqual(spawn.call_count, 0)
        changed = {**self.preferences, "awake_keyword": "keep"}
        self.assertIsNone(main.action_for_keyword("awake", changed))
        self.assertEqual(main.action_for_keyword("keep", changed), "awake")

    def test_clean_plugin_does_not_manage_application_entries(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("desktop_shortcuts", source)
        self.assertNotIn("remove_launchers", source)
        self.assertNotIn("ensure_launchers", source)
        self.assertNotIn("~/.local/share/applications", source)
        self.assertEqual(len(self.manifest["preferences"]), 7)
        self.assertFalse((ROOT / "desktop_shortcuts.py").exists())
        self.assertFalse((ROOT / "desktop_action.py").exists())

    def test_missing_gui_confirm_fails_closed(self):
        run = Mock(side_effect=OSError("no Zenity"))
        notice = Mock()
        self.assertEqual(dispatch("shutdown", runner=run, notifier=notice), 1)
        self.assertEqual(run.call_count, 1)
        notice.assert_called_once()

    def test_sleep_action_does_not_show_confirmation(self):
        runner = Mock(side_effect=AssertionError("sleep must not prompt"))
        spawned = Mock()
        self.assertEqual(dispatch("sleep", runner=runner, spawner=spawned, notifier=Mock()), 0)
        self.assertEqual(spawned.call_count, 1)
        self.assertIn("display-sleep", spawned.call_args.args[0])

    def test_dangerous_action_cancel_prevents_execution(self):
        for cmd in DANGEROUS:
            runner = Mock(return_value=subprocess.CompletedProcess([], 1))
            self.assertEqual(dispatch(cmd, runner=runner, notifier=Mock()), 0)
            self.assertEqual(runner.call_count, 1)
            self.assertEqual(runner.call_args.args[0][0], "zenity")


if __name__ == "__main__":
    unittest.main()
