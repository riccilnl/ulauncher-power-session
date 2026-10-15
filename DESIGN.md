# Decision: single-Enter native Ulauncher actions

## Why previous approach failed

Ulauncher 5 `ExtensionKeywordResultItem.on_enter` returns `SetUserQueryAction(keyword + ' ')`; it doesn't execute the operation. Then `KeywordQueryEvent` returned an operation, then custom double confirmation: the user saw **three Enters** for Sleep Display.

## Frozen solution

Use Ulauncher 5 native app search instead of extension keyword search:
`AppResultItem.on_enter` → `LaunchAppAction` → `desktop_action.py` → existing `powerctl.py`.

The GitHub Ulauncher extension remains the installation and update entry; `main.py` auto-registers seven managed `.desktop` entries on startup. There are no keyword preferences and no second Ulauncher command menu.

`desktop_shortcuts.py`:
- Only touches namespaced `riccilnl-ulauncher-power-*.desktop` files.
- Uses ownership marker, refuses foreign files/symlinks, atomic replacement, idempotence.
- User can remove entries using `python3 desktop_shortcuts.py remove`.
- Does not mutate existing user shortcuts/other files, requires no root.

`desktop_action.py`:
- `sleep` first Enter launches the existing GNOME display blanking asynchronously (no confirmation).
- `awake` and `lock` first Enter run directly.
- `suspend`, `logout`, `restart`, `shutdown` require native `zenity` dialog before any dangerous command.
- A missing or dismissed confirmation fails closed.

Keep `powerctl.py` unchanged, preserving AC+battery backup, rollback, lid-close policy, and avoiding raw Mutter PowerSaveMode writes.

## Validation

- [x] Ulauncher 5 source confirms native desktop app search first Enter is `LaunchAppAction`.
- [x] Ulauncher 5 source confirms app directory inotify watcher.
- [ ] Source file syntax, desktop parsing, simulated dispatch tests in the installed Fedora environment.
- [ ] After actual GitHub update: shortcut names and icon in Ulauncher, first Enter sleep.
- [ ] Physical LCD off, reliable wake, Cora/SSH continuity on both AC and battery.
- [ ] GNOME confirmation behavior and safe uninstall cleanup.

No claim of macOS physical display-off equivalence before Dell acceptance.
