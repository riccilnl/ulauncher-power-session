"""Add 7 single-Enter launchers to GNOME/Ulauncher app search."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
import tempfile

BASE = Path(__file__).resolve().parent
PREFIX = "riccilnl-ulauncher-power"
MARKER = "X-Riccilnl-PowerSession=true"
ICON = BASE / "images/bolt-v2.svg"
ACTIONS = (
    ("awake", "Awake", "Toggle idle suspend prevention on AC and battery"),
    ("sleep", "Sleep Display", "Blank the screen without suspending the computer"),
    ("lock", "Lock", "Lock GNOME desktop session"),
    ("suspend", "Suspend", "Suspend the computer"),
    ("logout", "Log Out", "Log out of GNOME"),
    ("restart", "Restart", "Reboot the computer"),
    ("shutdown", "Shut Down", "Power off the computer"),
)

def desktop_directory():
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share")) / "applications"

def quote_exec(path):
    path = str(path)
    if any(ch in path for ch in ("\n", "\r", "\0", "%")):
        raise ValueError("Invalid executable path for Desktop Entry")
    return '"' + path.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`") + '"'

def entry_text(slug, name, description):
    script = BASE / "desktop_action.py"
    if not script.is_file() or not ICON.is_file():
        raise FileNotFoundError("Missing desktop_action.py or bolt icon")
    return "\n".join([
        "[Desktop Entry]", "Version=1.0", "Type=Application",
        f"Name={name}", f"Comment={description}",
        f"Exec={quote_exec(Path(sys.executable))} {quote_exec(script)} {slug}",
        f"Icon={ICON}", "Terminal=false", "StartupNotify=false",
        "Categories=Utility;", MARKER, "",
    ])

def ensure_launchers(destination=None):
    target = Path(destination) if destination is not None else desktop_directory()
    target.mkdir(parents=True, exist_ok=True)
    changed = []
    for slug, name, description in ACTIONS:
        path = target / f"{PREFIX}-{slug}.desktop"
        desired = entry_text(slug, name, description)
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlink: {path}")
        if path.exists():
            old = path.read_text(encoding="utf-8")
            if MARKER not in old.splitlines():
                raise RuntimeError(f"Refusing unmanaged desktop entry: {path}")
            if old == desired:
                continue
        fd, tmp = tempfile.mkstemp(prefix=".power-session-", suffix=".tmp", dir=target)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(desired)
            os.chmod(tmp, 0o644)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        changed.append(path)
    return changed

def remove_launchers(destination=None):
    target = Path(destination) if destination is not None else desktop_directory()
    removed = []
    for slug, *_ in ACTIONS:
        path = target / f"{PREFIX}-{slug}.desktop"
        if path.is_file() and not path.is_symlink():
            if MARKER in path.read_text(encoding="utf-8").splitlines():
                path.unlink()
                removed.append(path)
    return removed

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "remove", "list"))
    mode = parser.parse_args(argv).action
    paths = (ensure_launchers() if mode == "install" else
             remove_launchers() if mode == "remove" else
             [desktop_directory() / f"{PREFIX}-{slug}.desktop" for slug, *_ in ACTIONS])
    for path in paths:
        print(path)
    return 0

if __name__ == "__main__":
    sys.exit(main())
