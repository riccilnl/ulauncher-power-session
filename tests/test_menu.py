"""Verify the real Ulauncher v2 menu API and user-visible Awake placement."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import main


class MenuTests(unittest.TestCase):
    def test_awake_is_first_under_power(self):
        results = main.entries_for_query("", state="OFF")
        self.assertGreaterEqual(len(results), 7)
        self.assertEqual(results[0].get_name(), "Awake OFF · 点击开启")

    def test_awake_on_is_visible(self):
        results = main.entries_for_query("", state="ON")
        self.assertTrue(results[0].get_name().startswith("Awake ON"))

    def test_explicit_keyword_shows_only_awake(self):
        results = main.entries_for_query("", direct_awake=True, state="OFF")
        self.assertEqual(len(results), 1)
        self.assertIn("Awake", results[0].get_name())

    def test_search_awake(self):
        results = main.entries_for_query("awake", state="ON")
        self.assertEqual(len(results), 1)
        self.assertIn("Awake ON", results[0].get_name())

    def test_wake_display_removed(self):
        self.assertFalse(any(key == "display-wake" for key, *_ in main.ENTRIES))
        results = main.entries_for_query("wake display", state="ON")
        self.assertEqual(results, [])

    def test_sleep_display_requires_confirmation(self):
        self.assertIn("display-sleep", main.CONFIRM)

    def test_keywords_present_in_manifest(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        keywords = {pref["default_value"] for pref in manifest["preferences"]
                    if pref.get("type") == "keyword"}
        self.assertTrue({"power", "awake"} <= keywords)


if __name__ == "__main__":
    unittest.main()
