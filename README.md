# GNOME Power & Session — Ulauncher 5

A GNOME Wayland power/session extension for **Ulauncher 5.15.x / API 2.0**.

## Install from Ulauncher

Open **Ulauncher Preferences → Extensions → Add Extension**, then enter:

https://github.com/riccilnl/ulauncher-power-session

This is the supported install path. **Do not run an install.sh script or copy files manually.**
Type `power ` (including the space) to display extension actions.

## Actions

| Entry | Meaning |
| --- | --- |
| Sleep Display | Disable idle suspend on AC and battery, lock GNOME, request ScreenSaver activation |
| Wake Display | Ask ScreenSaver to deactivate (does not unlock authentication) |
| Awake | Toggle idle-suspend prevention on AC and battery; retain original values for restoration |
| Lock | Lock the GNOME user session |
| Suspend | Explicitly suspend the machine; ask to confirm first |
| Log out | Log out of the user session; ask to confirm first |
| Restart | Restart computer; ask to confirm first |
| Shut down | Shut down computer; ask to confirm first |

GNOME **lid-close policy is not changed**. No root access is required. All subprocesses use fixed argument arrays (no shell commands).

## Important: Sleep Display is experimental

GNOME Wayland's `org.gnome.ScreenSaver.SetActive(true)` is not a proven counterpart to macOS `pmset displaysleepnow`. The extension **does not** directly set Mutter `PowerSaveMode=3`, which was associated with loss of display wake on the target laptop. The ScreenSaver call may lock/blank the UI without immediately removing physical LCD backlight power.

Before marking macOS-equivalent behavior as accepted, **verify on the actual Fedora laptop**:
1. Physical display turns off immediately.
2. Keyboard or touchpad turns it back on.
3. SSH and Cora remain reachable throughout (on both AC and battery power, for at least 15 minutes).
4. Closing the lid still suspends the laptop and opening it can resume.

Do not leave an untested Sleep Display implementation running unattended overnight.

## Restore / troubleshooting

After a prior **manual installation**, remove only the old manually copied extension directory:
`~/.local/share/ulauncher/extensions/ulauncher-power-session`. This is **not** the GitHub-managed extension, which Ulauncher identifies as `com.github.riccilnl.ulauncher-power-session`.

An Extension showing Stopped may have a startup error; inspect Ulauncher logs and do not assume it just needs a restart.

CLI, when run inside the logged-in GNOME graphical user session:

```sh
python3 powerctl.py status
python3 powerctl.py awake-on
python3 powerctl.py awake-off
python3 powerctl.py display-wake
```

The Awake state backup is `~/.local/state/ulauncher-power-session/ulauncher-power-session.json`. Previous shortcut backup files `ulauncher-awake-battery` and `ulauncher-awake-ac` are recognized but never removed. If an existing setting changed manually, Awake OFF will refuse to overwrite it. Display Sleep calls Awake ON, so use Awake OFF later to restore normal idle suspension.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py powerctl.py
```

The module is built on the **Ulauncher v2** Extension API: `Extension`, `KeywordQueryEvent`, `ItemEnterEvent`, `ExtensionCustomAction`. No extra Python packages are required beyond those installed by Ulauncher.

## Status

Source/tests uploaded for Ulauncher 5.15.15 compatibility. GitHub URL installation, plugin running state, immediate physical panel-off, display wake and overnight Cora/SSH continuity **still need actual host verification**.
