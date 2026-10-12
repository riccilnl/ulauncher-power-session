"""Ulauncher v5 standalone global search keyword contract."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ulauncher.search.Query import Query
import main

EXPECTED = {
    "awake": "awake-toggle",
    "sleep": "display-sleep",
    "lock": "lock",
    "suspend": "suspend",
    "logout": "logout",
    "restart": "reboot",
    "shutdown": "shutdown",
}


class DirectCommandsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "manifest.json").read_text())
        cls.preferences = {
            pref["id"]: pref["default_value"]
            for pref in cls.manifest["preferences"]
            if pref["type"] == "keyword"
        }

    def test_all_seven_are_globally_searchable(self):
        self.assertEqual(len(self.preferences), 7)
        actual = {}
        for keyword in EXPECTED:
            found = main.command_for_keyword(keyword, self.preferences)
            self.assertIsNotNone(found, keyword)
            actual[keyword] = found[0]
        self.assertEqual(actual, EXPECTED)

    def test_no_power_prefix(self):
        self.assertNotIn("power", self.preferences.values())
        self.assertIsNone(main.command_for_keyword("power", self.preferences))

    def test_all_entries_listed_in_manifest(self):
        manifest_names = [pref["name"] for pref in self.manifest["preferences"]]
        self.assertEqual(manifest_names, [
            "Awake", "Sleep Display", "Lock", "Suspend",
            "Log Out", "Restart", "Shut Down",
        ])

    def test_ulauncher_v5_keywords_parse_directly(self):
        for word in EXPECTED:
            query = Query(word + " ")
            self.assertTrue(query.is_mode_active(), word)
            self.assertEqual(query.get_keyword(), word)
        self.assertEqual(Query("sleep display").get_keyword(), "sleep")
        self.assertTrue(Query("sleep display").is_mode_active())

    def test_default_keyword_has_one_matching_result(self):
        for keyword, action in EXPECTED.items():
            found = main.command_for_keyword(keyword, self.preferences)
            one = main.result_for_action(*found, state="OFF")
            self.assertIsNotNone(one)
            self.assertTrue(one.get_name())

    def test_user_custom_keywords_still_work(self):
        changed = {**self.preferences, "awake_keyword": "keep"}
        self.assertEqual(main.command_for_keyword("keep", changed)[0],
                         "awake-toggle")
        self.assertIsNone(main.command_for_keyword("awake", changed))

    def test_awake_on_off_are_clear(self):
        awake = main.command_for_keyword("awake", self.preferences)
        self.assertIn("Awake ON", main.result_for_action(*awake, state="ON").get_name())
        self.assertIn("Awake OFF", main.result_for_action(*awake, state="OFF").get_name())

    def test_legacy_wake_display_removed(self):
        self.assertNotIn("display-wake", main.VALID)

    def test_destructive_and_experimental_require_confirmation(self):
        self.assertEqual(main.CONFIRM, {
            "display-sleep", "suspend", "logout", "reboot", "shutdown",
        })

    def test_same_bolt_icon_all_commands(self):
        self.assertEqual(main.ICON, self.manifest["icon"])
        self.assertEqual(main.ICON, "images/icon.svg")
        svg = (ROOT / main.ICON).read_text()
        self.assertIn('viewBox="0 0 64 64"', svg)
        self.assertIn('fill="#FFD43B"', svg)
        self.assertNotIn("circle", svg)


if __name__ == "__main__":
    unittest.main()
