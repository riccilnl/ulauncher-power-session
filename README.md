# GNOME Power & Session — Ulauncher 5

Seven direct Ulauncher commands using the community-tested **app-like keyword pattern** from [friday/ulauncher-gnome-settings](https://github.com/friday/ulauncher-gnome-settings). No `power` parent menu and **no GNOME application icons**.

## Install and update

Ulauncher → Preferences → Extensions → Add/Update:

https://github.com/riccilnl/ulauncher-power-session

The existing GitHub-installed extension is the only component to update. Upon startup, the new version **removes only its own seven legacy `.desktop` application entries**. It does not create any new ones. These entries may disappear from Ulauncher's old search index after its desktop-file watcher refreshes.

## How the one-Enter UI works

For example: type `sleep`, find **Sleep Display** (⚡), press **Enter once**. Ulauncher briefly inserts the query `sleep `, which fires the extension's `KeywordQueryEvent`. The extension launches the action directly and closes Ulauncher. There is no second Ulauncher result screen.

**Important:** The same action also fires if you explicitly type a matching keyword followed by a space; this is a documented limitation of the app-like keyword workaround. Do not use these words to type unrelated searches with a trailing space. Extra nonempty arguments are ignored.

| Search keyword | Action after one Enter | Confirmation |
| --- | --- | --- |
| `awake` | Toggle GNOME idle-suspend prevention, AC and battery | None; state notification |
| `sleep` | Request display blanking while preserving host networking | None |
| `lock` | Lock GNOME desktop | None |
| `suspend` | Suspend the computer, disconnecting Cora/SSH | One GNOME Zenity confirmation |
| `logout` | Log out of GNOME | One Zenity confirmation |
| `restart` | Reboot | One Zenity confirmation |
| `shutdown` | Shut down | One Zenity confirmation |

All seven entries use the same centered yellow ⚡. Keywords may be customized in Ulauncher's extension preferences. Once selected, the direct action runs in a detached process; duplicate query notifications are suppressed briefly to avoid twice toggling Awake.

## Power and display contract

`Awake ON` sets both GNOME `sleep-inactive-ac-type` and `sleep-inactive-battery-type` to `nothing`, retaining their originals for restoration when toggled OFF. **Awake does not keep the screen lit.** Lid closing remains governed by GNOME/system policy.

`Sleep Display` invokes the existing conservative method: enable Awake, lock the screen, request `org.gnome.ScreenSaver.SetActive(true)`. This **may lock/blank without truly powering down the physical LCD**. Do not claim macOS `pmset displaysleepnow` equivalence until confirmed on Dell Fedora.

Dangerous session actions only run after explicit confirmation. A missing Zenity dialog fails closed.

## Legacy cleanup and rollback

There are no `.desktop` launchers in the current architecture. Prior versions generated `~/.local/share/applications/riccilnl-ulauncher-power-*.desktop`. The updated extension removes only these namespaced files **when they have the extension ownership marker**. It skips symlinks and unrelated entries. No GNOME power settings are modified by migration.

You can check legacy entries with:

```sh
python3 ~/.local/share/ulauncher/extensions/com.github.riccilnl.ulauncher-power-session/desktop_shortcuts.py list
```

The standalone `desktop_shortcuts.py remove` command also cleans old entries but **can no longer create them**.

## Tests and outstanding real-machine checks

```sh
python3 -m py_compile main.py desktop_action.py desktop_shortcuts.py powerctl.py tests/*.py
python3 -m unittest discover -s tests -v
```

Tests mock all sleep, shutdown, reboot, logout and GNOME setting operations. Outstanding: user-visible confirmation that the seven commands appear **only** in Ulauncher, one Enter for Sleep Display, and continued SSH/Cora reachability with keyboard/touchpad wake after actual display-off.
