# GNOME Power & Session — design and acceptance contract

## Fixed baseline
- Target: Fedora 44, GNOME Wayland, Ulauncher 5.15.15, Extension API 2.0.0.
- GitHub URL installation is the default delivery method; no manual installer.
- No raw Mutter DisplayConfig PowerSaveMode writes, no generic sleep inhibitor that suppresses lid close.
- No automated destructive power actions in tests; shutdown, reboot, logout, and suspend require explicit UI confirmation.
- Mac-like Sleep Display is a hardware **acceptance criterion**, not an assumed capability.

## Modules
| Component | Interface | Contract |
| --- | --- | --- |
| UI | `main.PowerExtension` | V2 keyword query, result actions, confirmation |
| Controller | `powerctl.Controller` | Fixed subprocess argv, timeout and error reporting |
| Awake backup | `saved/snapshot/awake_on/awake_off` | Save AC and battery originals before setting 'nothing'; restore guarded by comparison |
| Display | `display_sleep/display_wake` | GNOME ScreenSaver activation only; don't promise physical display off |
| Power | `action` | lock, suspend, logout, reboot, shutdown |
| Compatibility | `manifest.json`, `versions.json` | Ulauncher 5 v2 API; GitHub extension downloader |

## Tests / outstanding
- [x] Static API check against upstream Ulauncher 5.15.15 source.
- [x] Unit tests with mocked commands for persistence, migration, safe display call and destructive command mapping.
- [ ] GitHub extension installation on actual Dell; verify status is Running, keyword works.
- [ ] Confirm ScreenSaver API actually works in the active GNOME session.
- [ ] Confirm immediate LCD physical off, wake by keyboard/mouse.
- [ ] Confirm Cora/SSH persistence on AC and battery.
- [ ] Confirm lid-close sleep and subsequent resume.

**Do not mark Sleep Display production-ready until all field acceptance items pass.**
