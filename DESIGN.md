# Architecture / decision — Ulauncher-native app-like keywords

## Fixed user requirements

1. Search `sleep` / `awake` / `lock` / `suspend` / `logout` / `restart` / `shutdown` directly, no `power` prefix.
2. First Enter executes without nested Ulauncher menus, especially `sleep`.
3. No generated GNOME application icons; all command icons are the same ⚡.
4. Awake toggles idle auto-suspend on **AC + battery**, preserves lid-close behavior and prior settings; screen may still blank.
5. The display-off technique must not force full system suspend or make SSH/Cora unreachable.
6. Dangerous commands require **only one external OS confirmation**, never another Ulauncher menu.

## Chosen community design

See [friday/ulauncher-gnome-settings](https://github.com/friday/ulauncher-gnome-settings). Ulauncher v5 extension keywords are globally searchable, but Ulauncher's default `ExtensionKeywordResultItem.on_enter()` inserts `keyword + ' '` instead of directly executing. Its `KeywordQueryEvent` fires on that input change. The plugin now **executes at that event and immediately returns `HideWindowAction`**, instead of rendering a second result.

| Module | Contract |
| --- | --- |
| `manifest.json` | Seven Ulauncher v2 keyword preferences with display names and ⚡ icon |
| `main.py` | One event → detached `action.py` → `HideWindowAction` (no submenu) |
| `action.py` | Awake/Lock/Sleep direct, disruptive commands via one Zenity confirmation |
| `powerctl.py` | Existing AC+battery GSettings snapshot/restore with flock and rollback |
| `tests/` | First-Enter dispatch, duplicate-event debounce, argument guards, absence of app-entry mutation, power tests |

## Explicit trade-offs

- The keyword pattern is a **community workaround**, not an official first-Enter execution hook. The query may briefly display `sleep ` before it closes. Typing that exact keyword with a space (even without Enter) will also invoke it. Avoid nonempty argument execution; disruptive operations show Zenity confirmation.
- Keyword display text does not dynamically show Awake ON/OFF, but the operation posts a notification.
- Suppress repeated identical action events within 1.5 seconds to prevent double toggle.
- No mutation of Ulauncher's `shortcuts.json`, any GNOME `.desktop` files or any application-menu entries. Previous cleanup and migration code has been removed.

## Acceptance

- [x] Upstream Ulauncher v5 code supports the SetUserQueryAction → KeywordQueryEvent → HideWindowAction sequence.
- [x] GitHub repository source uses seven keyword preferences, no app-generating startup.
- [ ] CI mocked tests pass and Fedora Ulauncher 5 API integration tested.
- [x] No application-menu cleanup or mutation code in the plugin. Existing user cleanup remains untouched.
- [ ] Actual Ulauncher command first Enter on Dell Fedora (Sleep Display and Awake).
- [ ] Display-off, wake, SSH/Cora and lid-close behaviors verified in both AC/battery conditions.

Do not claim field acceptance from mocked tests.
