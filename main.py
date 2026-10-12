"""Ulauncher 5 extension: GNOME power and session actions (Extension API v2)."""
from __future__ import annotations

import os
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
ICON = "images/icon.svg"

ENTRIES = [
    ("display-sleep", "Sleep Display · 熄屏", "锁屏并请求 GNOME 关闭显示；保持网络在线（待实机验证物理熄屏）", "display screen off 熄屏 黑屏"),
    ("display-wake", "Wake Display · 恢复显示", "请求 GNOME 重新点亮屏幕（不绕过锁屏）", "wake screen 唤醒"),
    ("awake-toggle", "Awake · 开关空闲挂起", "电池与插电同时切换，保留合盖动作", "awake keep 保持运行"),
    ("lock", "Lock · 锁屏", "仅锁定 GNOME 会话", "lock 锁屏"),
    ("suspend", "Suspend · 挂起", "挂起整机，SSH 与 Cora 将断开", "suspend sleep 挂起"),
    ("logout", "Log out · 注销", "退出当前 GNOME 会话", "logout 注销"),
    ("reboot", "Restart · 重启", "重新启动计算机", "restart reboot 重启"),
    ("shutdown", "Shut down · 关机", "关闭计算机", "shutdown poweroff 关机"),
]
CONFIRM = {"suspend", "logout", "reboot", "shutdown"}
VALID = {row[0] for row in ENTRIES}


def item(name, description, data):
    return ExtensionResultItem(name=name, description=description, icon=ICON,
                               on_enter=ExtensionCustomAction(data, keep_app_open=True))


def call(action):
    try:
        proc = subprocess.run([sys.executable, str(CTL), action], capture_output=True,
                              text=True, timeout=14, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    message = (proc.stdout if proc.returncode == 0 else proc.stderr).strip()
    return proc.returncode == 0, message or f"Exit code {proc.returncode}"


class PowerExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, Queries())
        self.subscribe(ItemEnterEvent, Commands())


class Queries(EventListener):
    def on_event(self, event, extension):
        search = (event.get_argument() or "").strip().casefold()
        state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
        state = state / "ulauncher-power-session/ulauncher-power-session.json"
        awake = "ON" if state.is_file() else "OFF"
        entries = []
        for action, title, description, terms in ENTRIES:
            if search and search not in f"{title} {description} {terms}".casefold():
                continue
            if action == "awake-toggle":
                title = f"Awake {awake} · 点击切换"
            entries.append(item(title, description, {"cmd": "execute", "action": action}))
        if not entries:
            entries.append(item("无匹配操作", "尝试 sleep、awake、lock、reboot",
                                {"cmd": "cancel"}))
        return RenderResultListAction(entries)


class Commands(EventListener):
    def on_event(self, event, extension):
        data = event.get_data() or {}
        mode, action = data.get("cmd"), data.get("action")
        if mode == "cancel":
            return HideWindowAction()
        if mode not in {"execute", "confirmed"} or action not in VALID:
            return RenderResultListAction([item("未知操作", "未执行任何操作", {"cmd": "cancel"})])
        if mode == "execute" and action in CONFIRM:
            title = next(row[1] for row in ENTRIES if row[0] == action)
            return RenderResultListAction([
                item("确认：" + title, "再次回车执行；可能导致会话或网络断开",
                     {"cmd": "confirmed", "action": action}),
                item("取消", "不执行", {"cmd": "cancel"}),
            ])
        if action == "display-sleep":
            try:
                subprocess.Popen([sys.executable, str(CTL), action, "--delay", "1.0"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True,
                                 cwd=str(BASE))
            except OSError as exc:
                return RenderResultListAction([item("启动失败", str(exc), {"cmd": "cancel"})])
            return HideWindowAction()
        ok, message = call(action)
        if not ok:
            return RenderResultListAction([item("执行失败", message, {"cmd": "cancel"})])
        return HideWindowAction()


if __name__ == "__main__":
    PowerExtension().run()
