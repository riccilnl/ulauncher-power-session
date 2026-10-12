"""GNOME power control without raw Mutter PowerSaveMode writes or forced lid inhibition."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

POWER_SCHEMA = "org.gnome.settings-daemon.plugins.power"
KEYS = ("sleep-inactive-battery-type", "sleep-inactive-ac-type")
STATE_NAME = "ulauncher-power-session.json"
SCREENSAVER = ("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver",
               "org.gnome.ScreenSaver.SetActive")


class PowerError(RuntimeError):
    pass


class Controller:
    def __init__(self, state_dir=None, runner=None):
        state_base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
        self.state_dir = Path(state_dir) if state_dir else state_base / "ulauncher-power-session"
        self.state_file = self.state_dir / STATE_NAME
        self.legacy_dir = state_base
        self.runner = runner or subprocess.run

    def run(self, argv, *, timeout=8, check=True):
        try:
            result = self.runner(argv, text=True, capture_output=True, timeout=timeout,
                                 check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PowerError(f"{argv[0]} could not run: {exc}") from exc
        if check and result.returncode != 0:
            details = (result.stderr or result.stdout or "").strip()[:300]
            raise PowerError(f"{argv[0]} failed: {details or result.returncode}")
        return (result.stdout or "").strip()

    def get(self, key):
        value = self.run(["gsettings", "get", POWER_SCHEMA, key])
        if not value:
            raise PowerError(f"Empty GSettings value: {key}")
        return value

    def set(self, key, value):
        self.run(["gsettings", "set", POWER_SCHEMA, key, value])
        if self.get(key) != value:
            raise PowerError(f"GSettings value not applied: {key}")

    def stop_legacy(self):
        # A previous shortcut used to inhibit *idle*, preventing normal display blanking.
        self.run(["systemctl", "--user", "stop", "awake-inhibit.service"], check=False)

    @contextmanager
    def state_lock(self):
        """Serialize Awake transitions from launcher and CLI processes."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        lockpath = self.state_dir / ".lock"
        with lockpath.open("a+") as fd:
            os.chmod(lockpath, 0o600)
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)

    def saved(self):
        if not self.state_file.exists():
            return None
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PowerError(f"Awake state cannot be read: {exc}") from exc
        if not isinstance(data, dict) or data.get("version") != 1 or not all(
                isinstance(data.get(key), str) for key in KEYS):
            raise PowerError("Unsupported Awake state format; preserving existing settings")
        return {key: data[key] for key in KEYS}

    def snapshot(self):
        existing = self.saved()
        if existing is not None:
            return existing
        values = {key: self.get(key) for key in KEYS}
        for key, filename in ((KEYS[0], "ulauncher-awake-battery"),
                              (KEYS[1], "ulauncher-awake-ac")):
            legacy = self.legacy_dir / filename
            if legacy.is_file():
                saved_value = legacy.read_text(encoding="utf-8").strip()
                if saved_value:
                    values[key] = saved_value
        self.state_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": 1, **values}, indent=2) + "\n",
                       encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.state_file)
        return values

    def awake_on(self):
        self.stop_legacy()
        existing = self.saved()
        before = {key: self.get(key) for key in KEYS}
        if existing is not None:
            for key in KEYS:
                if before[key] not in ("'nothing'", existing[key]):
                    raise PowerError(f"External change detected for {key}; not overwriting")
        self.snapshot()  # Original state is durable before either GSettings change.
        changed = []
        try:
            for key in KEYS:
                if before[key] != "'nothing'":
                    changed.append(key)  # Include failed key: set might partially succeed.
                    self.set(key, "'nothing'")
        except PowerError as exc:
            restore_errors = []
            for key in reversed(changed):
                try:
                    if self.get(key) != before[key]:
                        self.set(key, before[key])
                except PowerError as restore_exc:
                    restore_errors.append(str(restore_exc))
            if not restore_errors and existing is None:
                self.state_file.unlink()
            detail = "; rollback failed: " + "; ".join(restore_errors) if restore_errors else "; rolled back"
            raise PowerError(f"Awake ON failed: {exc}{detail}") from exc
        return "Awake ON: AC and battery idle suspend disabled (lid policy unchanged)"

    def awake_off(self):
        self.stop_legacy()
        originals = self.saved()
        if originals is None:
            return "No Awake backup exists; current settings left unchanged"
        before = {key: self.get(key) for key in KEYS}
        for key, original in originals.items():
            if before[key] not in ("'nothing'", original):
                raise PowerError(f"External change detected for {key}; backup retained")
        changed = []
        try:
            for key, original in originals.items():
                if before[key] != original:
                    changed.append(key)
                    self.set(key, original)
        except PowerError as exc:
            restore_errors = []
            for key in reversed(changed):
                try:
                    if self.get(key) != before[key]:
                        self.set(key, before[key])
                except PowerError as restore_exc:
                    restore_errors.append(str(restore_exc))
            detail = "; rollback failed: " + "; ".join(restore_errors) if restore_errors else "; rolled back"
            raise PowerError(f"Awake OFF failed: {exc}{detail}") from exc
        self.state_file.unlink()
        return "Awake OFF: previous AC and battery policies restored"

    def awake_toggle(self):
        return self.awake_off() if self.saved() else self.awake_on()

    def status(self):
        snapshot = self.saved()
        current = {key: self.get(key) for key in KEYS}
        if snapshot is None:
            state = "OFF"
        elif all(current[key] == "'nothing'" for key in KEYS):
            state = "ON"
        else:
            state = "INCONSISTENT"
        return {"state": state, "awake": state == "ON",
                "battery": current[KEYS[0]], "ac": current[KEYS[1]]}

    def lock(self):
        self.run(["loginctl", "lock-session"])
        return "Lock requested"

    def screen_set_active(self, active):
        return self.run(["gdbus", "call", "--session",
                         "--dest", SCREENSAVER[0], "--object-path", SCREENSAVER[1],
                         "--method", SCREENSAVER[2], "true" if active else "false"], timeout=6)

    def display_sleep(self, delay=0):
        # Do not use raw Mutter power commands; screen wake previously failed.
        self.awake_on()
        self.lock()
        if delay:
            time.sleep(delay)
        try:
            self.screen_set_active(True)
        except PowerError as exc:
            raise PowerError(f"Lock succeeded; ScreenSaver activation failed: {exc}") from exc
        return ("GNOME ScreenSaver activated; physical LCD blanking, input wake and "
                "SSH/Cora availability remain unverified")

    def action(self, name):
        if name == "awake-on":
            return self.awake_on()
        if name == "awake-off":
            return self.awake_off()
        if name == "awake-toggle":
            return self.awake_toggle()
        if name == "lock":
            return self.lock()
        if name == "suspend":
            self.run(["systemctl", "suspend"])
            return "System suspend requested"
        if name == "logout":
            self.run(["gnome-session-quit", "--logout", "--no-prompt"])
            return "GNOME logout requested"
        if name == "reboot":
            self.run(["systemctl", "reboot"])
            return "System reboot requested"
        if name == "shutdown":
            self.run(["systemctl", "poweroff"])
            return "System shutdown requested"
        raise PowerError(f"Unknown operation: {name}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="GNOME power and session controller")
    parser.add_argument("action", choices=("status", "awake-on", "awake-off", "awake-toggle",
                        "lock", "display-sleep", "suspend", "logout",
                        "reboot", "shutdown"))
    parser.add_argument("--delay", type=float, default=0.0)
    args = parser.parse_args(argv)
    ctl = Controller()
    try:
        if args.action == "status":
            print(json.dumps(ctl.status(), ensure_ascii=False))
        else:
            with ctl.state_lock():
                if args.action == "display-sleep":
                    print(ctl.display_sleep(delay=max(0.0, min(args.delay, 5.0))))
                else:
                    print(ctl.action(args.action))
    except PowerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.action == "display-sleep":
            try:
                subprocess.run(["notify-send", "Sleep Display failed", str(exc)],
                               capture_output=True, check=False, timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
