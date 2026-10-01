"""The window. Each mixin is one area of the screen."""

from __future__ import annotations

import os
import tkinter as tk

from grok_assistant.rules.hub import build
from grok_assistant.ui.actions import ActionMixin
from grok_assistant.ui.ears import EarMixin
from grok_assistant.ui.flow import FlowMixin
from grok_assistant.ui.market import MarketMixin
from grok_assistant.ui.menus import MenuMixin
from grok_assistant.ui.prints_ui import PrintMixin
from grok_assistant.ui.window import WindowMixin
from grok_assistant.ui.worker import WorkerMixin


class TrayApp(FlowMixin, EarMixin, PrintMixin, WorkerMixin, MarketMixin, ActionMixin, MenuMixin, WindowMixin):
    """The listening window and the icon menu."""


def run() -> None:
    if os.name == "nt":
        try:
            ctypes_shell = __import__("ctypes").windll.shell32
            ctypes_shell.SetCurrentProcessExplicitAppUserModelID("xai.GrokAssistant")
        except Exception:
            pass
        from grok_assistant.ui.win_tray import install_white_submenu_arrows

        install_white_submenu_arrows()
    root = tk.Tk()
    app = TrayApp(root, build())
    app.start()
    root.mainloop()
