# GNOME Power & Session (Ulauncher 5)

Standalone GNOME Wayland power/session commands. **No `power` prefix**, no installer shell script. Target Fedora 44, Ulauncher 5.15.15, Extension API 2.0.0.

## Install or update

Ulauncher → Preferences → Extensions → Add Extension

https://github.com/riccilnl/ulauncher-power-session

For an existing GitHub installation use **Update** to load a new commit, or remove/re-add the URL if the update option is unavailable.

## Top-level commands

All seven commands appear as independently searchable **Ulauncher keyword items**, with one shared centered yellow ⚡ icon. Type the desired command, select its keyword item, then select the operation. The first selection activates the extension's command result; that is a limitation of the Ulauncher 5 keyword API. No `power` prefix or combined command menu is required.

| Search in the normal Ulauncher search bar | Command | Description |
| --- | --- | --- |
| `awake` | Awake | Toggle AC+battery **idle** auto-suspend; status says ON/OFF |
| `sleep` / `sleep display` | Sleep Display | Experimental: enables Awake, locks GNOME, requests screensaver activation |
| `lock` | Lock | Lock session |
| `suspend` | Suspend | Suspend machine (disconnects SSH/Cora) |
| `logout` | Log Out | Log out of GNOME |
| `restart` | Restart | Restart machine |
| `shutdown` | Shut Down | Shut down machine |

After the selected keyword, Ulauncher 5 requires a space to activate extension results (it inserts the space for you when you select a keyword search result). The last five commands include an extra confirmation for dangerous actions; Sleep Display also requires confirmation while unverified.

If your launcher already has another `sleep`, `lock`, etc. keyword, adjust this extension's keyword under Preferences → Extensions. These are regular user-configurable keywords.

## What Awake actually means

Awake ON disables GNOME **idle-triggered auto-suspend** both on AC and battery. The screen can still dim/blank normally. A normal laptop-lid close still follows its existing policy. It does not prevent deliberate Suspend, shutdown, battery depletion, or other unrelated mechanisms. Awake OFF restores saved AC and battery values with rollback and conflict checks.

## Sleep Display is experimental

GNOME's `org.gnome.ScreenSaver.SetActive(true)` is **not** verified to turn off the physical LCD immediately like macOS `pmset displaysleepnow`. GNOME may merely lock/dim the desktop. Do not leave this function running unattended until real acceptance:
1. Physical LCD goes dark immediately.
2. Keyboard/mouse/touchpad restore display.
3. Cora and SSH stay online with battery and AC for at least 15 minutes.
4. Lid-close still suspends and resumes correctly.

The plugin does not force `Mutter DisplayConfig.PowerSaveMode=3`, because that preceded unresponsive display behavior on the Dell.

## Development verification

```sh
python3 -m py_compile main.py powerctl.py tests/*.py
python3 -m unittest discover -s tests -v
```

Power/suspend/shutdown commands are mocked in unit tests. The manifest and menu are checked with Ulauncher 5's real Python API. Tests **do not** suspend or shut down the device.

For technical limitations, module contracts and acceptance checklist, see [DESIGN.md](DESIGN.md).
