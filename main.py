"""GNOME Power & Session for Ulauncher 5 (Extension API v2).

Each operation has its own globally searchable keyword. No 'power' prefix.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

BASE = Path(__file__).resolve().parent
CTL = BASE / "powerctl.py"
ICON = "images/bolt-v2.svg"

# Each manifest keyword gets one separately searchable top-level Ulauncher item.
# id: (default keyword, controller action, display name, description)
COMMANDS = {
    "awake_keyword": ("awake", "awake-toggle", "Awake", "防止电池和插电时空闲自动挂起，可切换恢复"),
    "sleep_keyword": ("sleep", "display-sleep", "Sleep Display", "实验：锁屏并请求 GNOME 熄屏，后台保持运行"),
    "lock_keyword": ("lock", "lock", "Lock", "锁定当前 GNOME 会话"),
    "suspend_keyword": ("suspend", "suspend", "Suspend", "挂起电脑，SSH/Cora 将断开"),
    "logout_keyword": ("logout", "logout", "Log Out", "注销当前 GNOME 会话"),
    "restart_keyword": ("restart", "reboot", "Restart", "重新启动电脑"),
    "shutdown_keyword": ("shutdown", "shutdown", "Shut Down", "关闭电脑"),
}
VALID = {spec[1] for spec in COMMANDS.values()}
CONFIRM = {"display-sleep", "suspend", "logout", "reboot", "shutdown"}


def item(name, description, data):
    return ExtensionResultItem(name=name, description=description, icon=ICON,
                               on_enter=ExtensionCustomAction(data, keep_app_open=True))


def call(action):
    try:
        proc = subprocess.run([sys.executable, str(CTL), action],
                              capture_output=True, text=True, timeout=14, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (proc.stdout if proc.returncode == 0 else proc.stderr).strip()
    return proc.returncode == 0, output or f"Exit code {proc.returncode}"


def awake_state():
    """Read the actual GNOME settings via controller; do not trust only a marker file."""
    try:
        proc = subprocess.run([sys.executable, str(CTL), "status"], capture_output=True,
                              text=True, timeout=3, check=False)
        if proc.returncode != 0:
            return "UNKNOWN"
        data = json.loads(proc.stdout)
        return data["state"] if data.get("state") in ("ON", "OFF", "INCONSISTENT") else "UNKNOWN"
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return "UNKNOWN"


def command_for_keyword(keyword, preferences):
    """Honor user-customized keyword preferences, with manifest defaults as fallback."""
    for pref_id, (default, action, title, description) in COMMANDS.items():
        if keyword == preferences.get(pref_id, default):
            return action, title, description
    return None


def result_for_action(action, title, description, state="UNKNOWN"):
    if action == "awake-toggle":
        display = {
            "ON": ("Awake ON · 点击关闭", "已禁止电池/插电空闲挂起；点击恢复"),
            "OFF": ("Awake OFF · 点击开启", "点击后禁止电池/插电空闲挂起，屏幕仍可熄灭"),
            "INCONSISTENT": ("Awake 状态异常", "原设置和当前状态不一致，请检查"),
            "UNKNOWN": ("Awake · 无法确认状态", "当前无法读取系统电源设置"),
        }
        title, description = display.get(state, display["UNKNOWN"])
    return item(title, description, {"cmd": "execute", "action": action})


class PowerExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, Queries())
        self.subscribe(ItemEnterEvent, Commands())


class Queries(EventListener):
    def on_event(self, event, extension):
        found = command_for_keyword(event.get_keyword(), extension.preferences)
        if not found:
            return RenderResultListAction([item("无法识别的命令", "请检查插件关键词配置",
                                                {"cmd": "cancel"})])
        action, title, description = found
        state = awake_state() if action == "awake-toggle" else "UNKNOWN"
        return RenderResultListAction([result_for_action(action, title, description, state)])


class Commands(EventListener):
    def on_event(self, event, extension):
        data = event.get_data() or {}
        mode, action = data.get("cmd"), data.get("action")
        if mode == "cancel":
            return HideWindowAction()
        if mode not in {"execute", "confirmed"} or action not in VALID:
            return RenderResultListAction([item("无效操作", "未执行", {"cmd": "cancel"})])
        if mode == "execute" and action in CONFIRM:
            name = next(title for _default, cmd, title, _desc in COMMANDS.values()
                        if cmd == action)
            note = ("实验功能：物理熄屏尚未验收，勿无人值守运行"
                    if action == "display-sleep" else
                    "再次回车才执行，此操作可能断开当前会话或网络")
            return RenderResultListAction([
                item("确认：" + name, note, {"cmd": "confirmed", "action": action}),
                item("取消", "不执行", {"cmd": "cancel"}),
            ])
        if action == "display-sleep":
            try:
                subprocess.Popen(
                    [sys.executable, str(CTL), action, "--delay", "1.0"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True, cwd=str(BASE),
                )
            except OSError as exc:
                return RenderResultListAction([item("执行失败", str(exc), {"cmd": "cancel"})])
            return HideWindowAction()
        success, message = call(action)
        if not success:
            return RenderResultListAction([item("执行失败", message, {"cmd": "cancel"})])
        return HideWindowAction()


if __name__ == "__main__":
    PowerExtension().run()
