"""Ulauncher 5 GNOME power and session extension, Extension API 2.0."""
from __future__ import annotations

import json
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

# Awake is first, and also has an independent 'awake ' trigger.
ENTRIES = [
    ("awake-toggle", "Awake", "开关电池与插电的空闲自动挂起；屏幕可以正常熄灭", "awake keep on off 保持运行 防挂起"),
    ("display-sleep", "Sleep Display · 熄屏（实验）", "锁屏并请求 GNOME 熄屏；尚未验证立即关闭物理屏幕", "display screen off 熄屏 黑屏"),
    ("lock", "Lock · 锁屏", "锁定 GNOME 会话", "lock 锁屏"),
    ("suspend", "Suspend · 挂起", "挂起整机，SSH 和 Cora 将断开", "suspend sleep 挂起"),
    ("logout", "Log out · 注销", "退出当前 GNOME 会话", "logout 注销"),
    ("reboot", "Restart · 重启", "重新启动计算机", "restart reboot 重启"),
    ("shutdown", "Shut down · 关机", "关闭计算机", "shutdown poweroff 关机"),
]
# Sleep Display requires confirmation until hardware/network behavior is accepted.
CONFIRM = {"display-sleep", "suspend", "logout", "reboot", "shutdown"}
VALID = {row[0] for row in ENTRIES}


def item(name, description, data):
    return ExtensionResultItem(
        name=name, description=description, icon=ICON,
        on_enter=ExtensionCustomAction(data, keep_app_open=True),
    )


def call(action):
    try:
        proc = subprocess.run([sys.executable, str(CTL), action], capture_output=True,
                              text=True, timeout=14, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (proc.stdout if proc.returncode == 0 else proc.stderr).strip()
    return proc.returncode == 0, output or f"Exit code {proc.returncode}"


def awake_state():
    """Read real GSettings and plugin backup; never equate a backup file to ON."""
    try:
        proc = subprocess.run([sys.executable, str(CTL), "status"], capture_output=True,
                              text=True, timeout=3, check=False)
        if proc.returncode != 0:
            return "UNKNOWN"
        data = json.loads(proc.stdout)
        return data["state"] if data.get("state") in ("ON", "OFF", "INCONSISTENT") else "UNKNOWN"
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return "UNKNOWN"


def entries_for_query(search, *, direct_awake=False, state="UNKNOWN"):
    """Pure, testable menu factory; no duplicate Wake Display item."""
    search = (search or "").strip().casefold()
    results = []
    for action, title, description, terms in ENTRIES:
        if direct_awake and action != "awake-toggle":
            continue
        if search and search not in f"{title} {description} {terms}".casefold():
            continue
        if action == "awake-toggle":
            labels = {
                "ON": ("Awake ON · 点击关闭", "当前已禁止电池与插电空闲挂起；点击恢复原设置"),
                "OFF": ("Awake OFF · 点击开启", "点击后禁止电池与插电空闲挂起，不影响正常熄屏"),
                "INCONSISTENT": ("Awake 状态不一致 · 需检查", "备份与电源设置不一致；不会静默覆盖其他设置"),
                "UNKNOWN": ("Awake · 状态未知", "无法读取系统设置；选择后会显示错误或处理结果"),
            }
            title, description = labels.get(state, labels["UNKNOWN"])
        results.append(item(title, description, {"cmd": "execute", "action": action}))
    return results


class PowerExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, Queries())
        self.subscribe(ItemEnterEvent, Commands())


class Queries(EventListener):
    def on_event(self, event, extension):
        query = event.get_argument() or ""
        keyword = event.get_keyword()
        direct_awake = keyword == extension.preferences.get("awake_keyword", "awake")
        results = entries_for_query(query, direct_awake=direct_awake, state=awake_state())
        if not results:
            results = [item("没有匹配的操作", "可以输入 awake 或 power",
                            {"cmd": "cancel"})]
        return RenderResultListAction(results)


class Commands(EventListener):
    def on_event(self, event, extension):
        data = event.get_data() or {}
        mode, action = data.get("cmd"), data.get("action")
        if mode == "cancel":
            return HideWindowAction()
        if mode not in {"execute", "confirmed"} or action not in VALID:
            return RenderResultListAction([item("未知操作", "未执行", {"cmd": "cancel"})])
        if mode == "execute" and action in CONFIRM:
            name = next(row[1] for row in ENTRIES if row[0] == action)
            description = (
                "实验功能：不保证物理屏幕立即熄灭；不要无人值守使用"
                if action == "display-sleep" else "再次回车才执行；会话或网络可能断开"
            )
            return RenderResultListAction([
                item("确认：" + name, description, {"cmd": "confirmed", "action": action}),
                item("取消", "不执行任何操作", {"cmd": "cancel"}),
            ])
        if action == "display-sleep":
            # Give Ulauncher time to hide before locking. Failures are notified
            # by powerctl, never swallowed silently by a shell wrapper.
            try:
                subprocess.Popen(
                    [sys.executable, str(CTL), action, "--delay", "1.0"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True, cwd=str(BASE),
                )
            except OSError as exc:
                return RenderResultListAction([item("启动失败", str(exc), {"cmd": "cancel"})])
            return HideWindowAction()
        ok, message = call(action)
        if not ok:
            return RenderResultListAction([item("执行失败", message, {"cmd": "cancel"})])
        return HideWindowAction()


if __name__ == "__main__":
    PowerExtension().run()
