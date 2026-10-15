# GNOME Power & Session · Single Enter (Ulauncher 5)

The GitHub extension provides seven native desktop search results. **Type `sleep`, press Enter once, done.** No keyword expansion, no second Ulauncher menu, no Sleep Display confirmation.

## Install / update

Install or update the public Ulauncher extension:

https://github.com/riccilnl/ulauncher-power-session

On startup, the extension automatically writes seven identifiable `.desktop` launchers to `~/.local/share/applications` using your XDG data directory. Ulauncher 5 watches this directory and indexes them as **native apps**, so the first Enter executes the selected app. After an update, allow a few seconds for its app watcher to refresh. These entries also appear in GNOME's application search.

The Ulauncher Extension API v2 cannot trigger a direct command from the first Enter of a keyword item. This release **removes all extension keywords**, using native `LaunchAppAction` instead. Do not keep adding the old `power` keyword.

| Search term | First Enter | Extra confirmation |
| --- | --- | --- |
| `sleep` (Sleep Display) | Request blank display, keep host running | None |
| `awake` | Toggle GNOME idle-suspend prevention | None |
| `lock` | Lock GNOME session | None |
| `suspend` | Suspend whole computer | GNOME/Zenity confirmation |
| `logout` | End GNOME login session | GNOME/Zenity confirmation |
| `restart` | Reboot | GNOME/Zenity confirmation |
| `shutdown` | Power off | GNOME/Zenity confirmation |

The one-Enter direct commands use the same ⚡ icon. Shutdown/restart/suspend/logout retain **one native confirmation dialog** outside Ulauncher to prevent accidental session loss. If Zenity is unavailable, these commands fail closed, without performing the action.

### Awake versus Sleep Display

`awake` disables **automatic idle suspend** for both AC and battery. The screen may still blank/dim; the system and Cora remain running. Closing the lid follows your existing policy.

`sleep` invokes the existing controller: Awake ON, lock GNOME, then ScreenSaver activation after a 0.8-second delay to let Ulauncher close. It has not passed the complete **physical LCD off and keyboard/mouse wake** acceptance gate. Do not use unattended until that test passes.

### Troubleshooting / uninstall

The extension should be Running in Preferences → Extensions. If native results do not appear after an update, Ulauncher may not yet have indexed the newly created files. Inspect `~/.local/share/applications/riccilnl-ulauncher-power-*.desktop`. No system privileges are required.

Before removing this extension, clean up the desktop entries from the installed extension directory:

```sh
python3 ~/.local/share/ulauncher/extensions/com.github.riccilnl.ulauncher-power-session/desktop_shortcuts.py remove
```

Only files carrying this extension's ownership marker are removed. The original GNOME power settings and Awake state are never deleted by shortcut cleanup.

### Tests

```sh
python3 -m py_compile main.py desktop_shortcuts.py desktop_action.py powerctl.py
python3 -m unittest discover -s tests -v
```

Unit tests simulate execution and **never suspend, log out, reboot, shut down or blank the real display**. Actual UI and physical monitor behavior must be accepted on your Dell Fedora laptop.
