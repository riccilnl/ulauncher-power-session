# GNOME Power & Session — architecture and acceptance

**Source of truth:** `riccilnl/ulauncher-power-session` `main`; Fedora 44 / GNOME Wayland / Ulauncher 5.15.15, API v2.

## UI decision: no parent command

Ulauncher 5's `ExtensionSearchMode` returns each `keyword` preference as a standalone, globally searchable result, and `ExtensionKeywordResultItem.on_enter` sets the user query to `<keyword> `. Only **then** is `KeywordQueryEvent` fired. A normal API v2 extension cannot directly inject its own executable result items into the initial blank launcher result list. We therefore provide **seven keyword preferences**, one for each requested command, rather than `power <subcommand>`.

| Preference | Keyword | Controller action |
| --- | --- | --- |
| `awake_keyword` | awake | awake-toggle |
| `sleep_keyword` | sleep | display-sleep |
| `lock_keyword` | lock | lock |
| `suspend_keyword` | suspend | suspend |
| `logout_keyword` | logout | logout |
| `restart_keyword` | restart | reboot |
| `shutdown_keyword` | shutdown | shutdown |

All menu keyword icons are the same `images/bolt-v2.svg`: a centered, solid yellow bolt on a square navy background, with no incomplete/crooked circular power-glyph arcs. No Wake Display or parent `power` command.

## Module contracts

- `manifest.json`: v2 protocol, 7 user-modifiable keyword preferences; icon same for all.
- `main.py`: route `get_keyword()` by preferences to exactly 1 action; Awake state from controller, not marker file; destructive actions confirmed; do not silently report success.
- `powerctl.py`: GNOME GSettings state and original snapshot, AC/battery rollback, flock to serialize, existing lid policy untouched.
- `tests/`: verify all seven keywords and actual Ulauncher v5 `Query` parsing; simulated control only.

## Known limitations & acceptance

- [x] Independent global keyword search results instead of `power` subcommands.
- [x] All 7 names specified, one icon used throughout.
- [x] Sleep Display and destructive actions require confirmation.
- [ ] User graphical-session running status / actual search interaction (launcher profile cannot be read via isolated NodeDeck execution).
- [ ] Sleep Display **physical LCD off** immediately.
- [ ] Display wakes reliably; no black frozen display.
- [ ] SSH/Cora online throughout on battery and AC.
- [ ] Lid close still suspends, lid open resumes.
- [ ] User confirms the new ⚡ icon appears upright/centered in Ulauncher 5.

**Never claim macOS-equivalent display-off until the hardware acceptance items pass.**
