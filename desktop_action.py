"""Execute a native Ulauncher app-search result on the first Enter."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
CTL = BASE / "powerctl.py"
DIRECT = {
    "awake": "awake-toggle", "sleep": "display-sleep", "lock": "lock",
    "suspend": "suspend", "logout": "logout", "restart": "reboot",
    "shutdown": "shutdown",
}
DANGEROUS = {"suspend", "logout", "restart", "shutdown"}
LABELS = {"suspend": "挂起电脑", "logout": "注销会话",
          "restart": "重启电脑", "shutdown": "关闭电脑"}

def notify(title, body, *, runner=subprocess.run):
    try:
        runner(["notify-send", title, body], check=False, timeout=4,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        pass

def dispatch(name, *, runner=subprocess.run, spawner=subprocess.Popen, notifier=notify):
    if name not in DIRECT:
        raise ValueError("Unknown operation")
    if name in DANGEROUS:
        try:
            response = runner([
                "zenity", "--question", "--title", "确认操作",
                "--text", f"确定要{LABELS[name]}吗？",
                "--ok-label", "确认", "--cancel-label", "取消",
            ], check=False, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            notifier("操作已取消", f"系统确认对话框不可用：{exc}")
            return 1
        if response.returncode != 0:
            return 0
    if name == "sleep":
        # Native Ulauncher app result closes immediately after the first Enter.
        # Defer the GNOME lock and screensaver call until its window has closed.
        try:
            spawner([sys.executable, str(CTL), DIRECT[name], "--delay", "0.8"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True, cwd=str(BASE))
        except OSError as exc:
            notifier("Sleep Display 执行失败", str(exc))
            return 1
        return 0
    try:
        result = runner([sys.executable, str(CTL), DIRECT[name]],
                        capture_output=True, text=True, check=False, timeout=17)
    except (OSError, subprocess.TimeoutExpired) as exc:
        notifier("执行失败", str(exc))
        return 1
    message = ((result.stdout if result.returncode == 0 else result.stderr) or "").strip()
    if result.returncode:
        notifier("执行失败", message or str(result.returncode))
        return result.returncode
    if name == "awake":
        notifier("Awake", message or "设置已切换")
    return 0

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=tuple(DIRECT))
    args = parser.parse_args(argv)
    return dispatch(args.action)

if __name__ == "__main__":
    sys.exit(main())
