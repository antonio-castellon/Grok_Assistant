"""Start with Windows, for this user only. No administrator password."""

from __future__ import annotations

import sys
from pathlib import Path

_NAME = "GrokAssistant"
_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"


def quoted_command(executable: str) -> str:
    return f'"{executable}"'


def launch_command() -> str:
    if getattr(sys, "frozen", False):
        return quoted_command(sys.executable)
    exe = Path(__file__).resolve().parents[2] / "dist" / "GrokAssistant.exe"
    if exe.exists():
        return quoted_command(str(exe))
    return quoted_command(sys.executable) + " -m grok_assistant"


def enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN) as key:
            winreg.QueryValueEx(key, _NAME)
    except OSError:
        return False
    return True


def set_enabled(on: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, launch_command())
            return
        try:
            winreg.DeleteValue(key, _NAME)
        except OSError:
            return
