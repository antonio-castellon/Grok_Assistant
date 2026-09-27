"""Keep helper programs off the screen. A windowed app must not grow a console."""

from __future__ import annotations

import os
import subprocess


def no_window() -> dict:
    if os.name != "nt":
        return {}
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 0
    return {"startupinfo": info, "creationflags": subprocess.CREATE_NO_WINDOW}
