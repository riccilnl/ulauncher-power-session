# GNOME Power & Session — Ulauncher 5

GNOME Wayland power and session extension for **Ulauncher 5.15.15 / Extension API 2.0.0**.

## Install or update in Ulauncher

Install using **Preferences → Extensions → Add Extension** and the GitHub URL:

https://github.com/riccilnl/ulauncher-power-session

This extension is **not** installed using an `install.sh` script. If you previously installed a manually copied version, remove that version to avoid confusion.

**Keywords:**
- `power ` (with a trailing space) — full menu, with **Awake as the first entry**.
- `awake ` (with a trailing space) — show **only Awake ON/OFF**.

Existing GitHub installations should use the extension **Update** operation to receive newer commits; if no update control is available, remove the extension and add the same GitHub URL again. Ulauncher 5 does not automatically pick up updated GitHub code as soon as it is pushed.

## Commands

| Menu command | Actual behavior |
| --- | --- |
| Awake OFF → ON | Disables **idle-triggered** auto-suspend for both battery and AC power; screen is still allowed to blank |
| Awake ON → OFF | Restores both original idle-suspend settings |
| Sleep Display (experimental) | Enables Awake, locks the session, requests GNOME ScreenSaver activation |
| Lock | Locks current session, without forcing system suspend |
| Suspend | Suspends the entire computer (disconnects SSH/Cora), confirmation required |
| Log out | Logs out of GNOME, confirmation required |
| Restart | Reboots the computer, confirmation required |
| Shut down | Powers off the computer, confirmation required |

**Wake Display has been removed.** Waking a properly implemented screen-off state should happen from keyboard/mouse activity, not by activating Ulauncher while the screen is off.

**Awake ON is not a system-wide "never sleep" inhibitor.** It changes GNOME's two idle-suspend policies. Closing the laptop lid still follows the system's lid policy. Explicit user suspension, shutdown, battery exhaustion, thermal protection or other independent sleep policies are not overridden.

### Safe state management

- Saves both original GSettings values before writing either.
- Reads both real GSettings values to report ON/OFF/INCONSISTENT, rather than trusting the mere existence of a backup.
- Does not overwrite unexpected manual changes, and rolls back both settings after a partial failure.
- Serializes changes across plugin processes using a per-user state lock.
- Tries to stop the historical `awake-inhibit.service` that prevented idle screen blanking.
- Preserves older backup files `ulauncher-awake-battery` and `ulauncher-awake-ac` without deleting them.
- State file: `~/.local/state/ulauncher-power-session/ulauncher-power-session.json`.

## Critical: Sleep Display is NOT yet equivalent to macOS

GNOME Wayland's `org.gnome.ScreenSaver.SetActive(true)` can activate lock/blank behavior. **It does not guarantee immediate physical LCD backlight-off**, unlike macOS `pmset displaysleepnow`. Do not claim it has passed hardware tests.

The extension intentionally does not write Mutter `PowerSaveMode=3`, previously associated with an inability to wake the Dell screen. Sleep Display currently **requires a second confirmation**; do not use it unattended until the following acceptance checks pass.

1. Screen actually turns off (not only lock UI).
2. Keyboard and touchpad wake the screen.
3. SSH and Cora remain online at least 15 minutes, tested separately on AC and battery.
4. Lid-close sleep still works; resume succeeds.

## Troubleshooting

If Awake is missing, verify you have updated/reinstalled the GitHub extension. Typing `awake ` should return just the toggle; `power ` should put it first.

If the display appears off but SSH or Cora disconnects, inspect system suspend logs. The screen and system suspend mechanisms are distinct.

To view state from **within your own graphical GNOME session**:

```sh
python3 powerctl.py status
python3 powerctl.py awake-on
python3 powerctl.py awake-off
```

## Developer verification

```sh
python3 -m py_compile main.py powerctl.py tests/*.py
python3 -m unittest discover -s tests -v
```

Unit tests use simulated GSettings, screen and power command execution. On Dell Fedora, Ulauncher 5.15.15's actual import/API was used to validate menu generation. These tests do **not** perform a live suspend/shutdown/display-off.

See [DESIGN.md](DESIGN.md) for the architecture and field acceptance contract.
