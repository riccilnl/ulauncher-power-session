"""Remove only legacy .desktop launchers created by older extension releases.

The current release is keyword-only. It never creates desktop app entries.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PREFIX = "riccilnl-ulauncher-power"
MARKER = "X-Riccilnl-PowerSession=true"
LEGACY_ACTIONS = ("awake", "sleep", "lock", "suspend", "logout", "restart", "shutdown")


def desktop_directory():
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share")) / "applications"


def remove_launchers(destination=None):
    target = Path(destination) if destination is not None else desktop_directory()
    removed = []
    for slug in LEGACY_ACTIONS:
        path = target / f"{PREFIX}-{slug}.desktop"
        # Do not touch user files, unowned entries, or symlinks.
        if path.is_file() and not path.is_symlink():
            if MARKER in path.read_text(encoding="utf-8").splitlines():
                path.unlink()
                removed.append(path)
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clean obsolete app launchers")
    parser.add_argument("command", choices=["remove", "list"])
    mode = parser.parse_args(argv).command
    paths = (remove_launchers() if mode == "remove" else
             [desktop_directory() / f"{PREFIX}-{slug}.desktop"
              for slug in LEGACY_ACTIONS])
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
