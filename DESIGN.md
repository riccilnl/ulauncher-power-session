# GNOME Power & Session — architecture, decisions and audit

## Baseline (2026-10-12)

Target: Dell Fedora 44, GNOME Wayland, Ulauncher 5.15.15, Extension API 2.0.0. Source of truth: `riccilnl/ulauncher-power-session` on GitHub `main`.

Ulauncher 5 GitHub installer requires `versions.json`, `manifest.json`, and `main.py`. The keyword handler is `KeywordQueryEvent`, and actions return `ExtensionCustomAction` from the v2 API.

## Modules and contracts

| Component | Public contract |
| --- | --- |
| `manifest.json` | Two independent keywords, `power` (all) and `awake` (only Awake) |
| `main.py` | Awake first in power menu; state visible as ON, OFF, INCONSISTENT or UNKNOWN; no Wake Display |
| `powerctl.py:Controller` | Fixed subprocess argv, explicit errors, immutable original settings backup |
| Awake transitions | AC + battery type set to `nothing`, with comparison guards, exclusive state lock, and rollback |
| Screen action | Lock, request ScreenSaver SetActive; **not** a proven physical backlight-off control |
| Power actions | Suspend, logout, reboot and poweroff require a second UI confirmation |
| `tests/` | Mocked power-setting transitions and actual Ulauncher 5 menu rendering API import |

## Audit: fixes

1. **Awake undiscoverable:** An Awake row was present in source but the only launcher keyword was `power`. Installed UI state could not be read directly across the node's authorization boundary. Fixed by putting Awake first and offering a dedicated `awake` keyword; covered by 7 UI tests.
2. **Misleading Wake Display:** Removed. Recovery should occur from mouse/keyboard, and the feature was not practical while display was dark.
3. **Fake ON indicator:** Menu previously displayed ON solely when a backup file existed. Corrected by reading both GSettings values and comparing against the saved state.
4. **Partial changes:** Awake writes are now rolled back if one of the AC/battery settings fails. Backup remains if rollback itself fails.
5. **Potential double-click races:** File lock added for CLI transitions.
6. **Unsafe acceptance claim:** Screen display command remains experimental, with explicit confirmation and outstanding field tests. No code claim that ScreenSaver necessarily turns the physical panel off.
7. **Legacy transient inhibitor:** Best-effort stop of historical `awake-inhibit.service`; does not create a new sleep inhibitor that would suppress lid-close sleep.
8. **Delivery:** GitHub URL only, not manual install scripts; tests executed on Dell with Ulauncher 5.15.15 APIs.

## Quality gate

- [x] Real Ulauncher 5.15.15 v2 extension API read and import verified.
- [x] `versions.json` and `manifest.json` supported by Ulauncher 5 downloader.
- [x] 20 tests pass in the Dell test sandbox; tests never call real suspend/reboot/shutdown.
- [ ] Actual GitHub-installed extension status read from user's graphical session.
- [ ] `power`/ `awake` keyword interaction accepted by the user.
- [ ] Immediate physical panel-off on Dell.
- [ ] Keyboard/touchpad wake; no unresponsive black display.
- [ ] SSH and Cora continuous connectivity on AC and battery.
- [ ] Lid-close suspend / lid-open resume.

Do **not** declare Mac-equivalent Sleep Display complete until the outstanding tests pass.

## Future verification constraints

Avoid `org.gnome.Mutter.DisplayConfig PowerSaveMode=3` as a shortcut: it previously coincided with an unresponsive display. Do not substitute an `idle` inhibitor that prevents normal screen blanking, or a `sleep` inhibitor that overrides the user's lid-close behavior.
