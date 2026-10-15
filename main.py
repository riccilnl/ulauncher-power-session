"""Ulauncher 5 power extension: one-Enter commands, no desktop app entries.

Matches the community pattern in friday/ulauncher-gnome-settings:
select a searchable keyword once -> Ulauncher inserts "keyword " ->
KeywordQueryEvent directly launches the operation and hides Ulauncher.
"""
from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import sys
import time

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

BASE = Path(__file__).resolve().parent
RUNNER = BASE / "action.py"
# Keep in sync with manifest.json. IDs are stable when users customize keywords.
COMMANDS = {
    "awake_keyword": ("awake", "awake"),
    "sleep_keyword": ("sleep", "sleep"),
    "lock_keyword": ("lock", "lock"),
    "suspend_keyword": ("suspend", "suspend"),
    "logout_keyword": ("logout", "logout"),
    "restart_keyword": ("restart", "restart"),
    "shutdown_keyword": ("shutdown", "shutdown"),
}
# Duplicate event delivery must not toggle Awake twice or re-trigger shutdown.
RETRIGGER_SECONDS = 1.5


def action_for_keyword(keyword, preferences):
    for pref_id, (default, action) in COMMANDS.items():
        if keyword == preferences.get(pref_id, default):
            return action
    return None


def launch_action(action, spawner=subprocess.Popen):
    """Detached command execution; action.py handles user-visible errors."""
    return spawner(
        [sys.executable, str(RUNNER), action],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(BASE),
        start_new_session=True,
    )


class ImmediateKeywords(EventListener):
    def __init__(self, *, spawner=subprocess.Popen, clock=time.monotonic):
        self.spawner = spawner
        self.clock = clock
        self._last_action = None
        self._last_at = float("-inf")

    def on_event(self, event, extension):
        # Non-empty arguments never run: selecting the keyword inserts just a
        # trailing space; typing "sleep something" is not an execute command.
        if event.get_argument():
            return None
        action = action_for_keyword(event.get_keyword(), extension.preferences)
        if action is None:
            return None
        now = self.clock()
        if action == self._last_action and now - self._last_at < RETRIGGER_SECONDS:
            return HideWindowAction()
        self._last_action, self._last_at = action, now
        try:
            launch_action(action, self.spawner)
        except OSError:
            logging.getLogger(__name__).exception("Cannot start %s", action)
            # Keep plugin alive; the launcher should still be dismissed.
        return HideWindowAction()


class PowerExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, ImmediateKeywords())



if __name__ == "__main__":
    PowerExtension().run()
