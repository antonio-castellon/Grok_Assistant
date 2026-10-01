"""Pill buttons and tabs. Tk's own buttons stay square, so these draw the curve."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageTk

from grok_assistant.ui.theme import look

_rasters: dict[tuple, Image.Image] = {}


def _ground(widget) -> str:
    try:
        value = str(widget.cget("bg"))
    except tk.TclError:
        return look.bg
    if value.startswith("#") and len(value) == 7:
        return value
    return look.bg


def _plate(width: int, height: int, fill: str, ground: str) -> tuple[Image.Image, ImageTk.PhotoImage]:
    width = max(1, int(width))
    height = max(1, int(height))
    key = (width, height, fill.lower(), ground.lower())
    image = _rasters.get(key)
    if image is None:
        scale = 4
        big = Image.new("RGB", (width * scale, height * scale), ground)
        draw = ImageDraw.Draw(big)
        radius = (height * scale) // 2
        draw.rounded_rectangle((1, 1, width * scale - 2, height * scale - 2), radius=radius, fill=fill)
        image = big.resize((width, height), Image.Resampling.LANCZOS)
        _rasters[key] = image
    return image, ImageTk.PhotoImage(image)


class RoundButton(tk.Canvas):
    """A button whose ends are semicircles. Colors come from the active theme."""

    def __init__(
        self,
        parent,
        text: str = "",
        command=None,
        bg: str | None = None,
        fg: str | None = None,
        activebackground: str | None = None,
        activeforeground: str | None = None,
        font=None,
        padx: int = 16,
        pady: int = 8,
        width: int = 0,
        hover: bool = True,
        **_extra,
    ) -> None:
        ground = _ground(parent)
        super().__init__(parent, bg=ground, highlightthickness=0, bd=0, relief="flat", cursor="hand2")
        self._text = text
        self._command = command
        self._font = font or ("Segoe UI", 12)
        self._padx = padx
        self._pady = pady
        self._chars = width
        self._hover = hover
        self._state = "normal"
        self._ground = ground
        self._bg = bg or look.button
        self._fg = fg or look.ink
        self._active_bg = activebackground or look.button_active
        self._active_fg = activeforeground or self._fg
        self._fill = self._bg
        self._ink = self._fg
        self._raster: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self.bind("<Button-1>", self._press)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self._redraw()

    @property
    def plate(self) -> Image.Image | None:
        return self._raster

    def set_colors(self, bg: str, fg: str, activebackground: str, activeforeground: str) -> None:
        self._bg = bg
        self._fg = fg
        self._active_bg = activebackground
        self._active_fg = activeforeground
        self._fill = bg
        self._ink = fg
        self._redraw()

    def configure(self, cnf=None, **kw):
        if isinstance(cnf, dict):
            kw = {**cnf, **kw}
        changed = False
        if "text" in kw:
            self._text = str(kw.pop("text"))
            changed = True
        if "command" in kw:
            self._command = kw.pop("command")
        if "state" in kw:
            self._state = "disabled" if kw.pop("state") == "disabled" else "normal"
            changed = True
        if "bg" in kw:
            self._bg = kw.pop("bg")
            self._fill = self._bg
            changed = True
        if "fg" in kw:
            self._fg = kw.pop("fg")
            self._ink = self._fg
            changed = True
        if "font" in kw:
            self._font = kw.pop("font")
            changed = True
        if changed:
            self._redraw()
        if kw:
            return super().configure(**kw)
        return None

    config = configure

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "state":
            return self._state
        if key in ("bg", "background"):
            return self._fill
        if key in ("fg", "foreground"):
            return self._ink
        return super().cget(key)

    def _metrics(self) -> tuple[int, int]:
        font = tkfont.Font(font=self._font)
        text = self._text or " "
        width = font.measure(text) + self._padx * 2
        if self._chars:
            width = max(width, font.measure("0") * int(self._chars) + self._padx * 2)
        height = font.metrics("linespace") + self._pady * 2
        return max(width, height), max(height, 8)

    def _redraw(self) -> None:
        try:
            if not int(self.winfo_exists()):
                return
        except tk.TclError:
            return
        width, height = self._metrics()
        ink = look.muted if self._state == "disabled" else self._ink
        cursor = "hand2" if self._hover and self._state != "disabled" else "arrow"
        super().configure(width=width, height=height, bg=self._ground, cursor=cursor)
        self._raster, self._photo = _plate(width, height, self._fill, self._ground)
        self.delete("all")
        self.create_image(0, 0, image=self._photo, anchor="nw")
        self.create_text(width // 2, height // 2, text=self._text, fill=ink, font=self._font)

    def _press(self, _event=None) -> None:
        if self._state == "disabled" or self._command is None:
            return
        self._command()

    def _enter(self, _event=None) -> None:
        if not self._hover or self._state == "disabled":
            return
        self._fill = self._active_bg
        self._ink = self._active_fg
        self._redraw()

    def _leave(self, _event=None) -> None:
        if not self._hover:
            return
        self._fill = self._bg
        self._ink = self._fg
        self._redraw()


class RoundNotebook(tk.Frame):
    """Rounded tabs in front of one visible page. Same add, select, and tab calls as a notebook."""

    def __init__(self, parent, **_extra) -> None:
        super().__init__(parent, bg=look.bg, highlightthickness=0, bd=0)
        self._bar = tk.Frame(self, bg=look.bg, highlightthickness=0, bd=0)
        self._bar.pack(side="top", fill="x", pady=(2, 12))
        self._tabs: list[tuple[tk.Misc, RoundButton]] = []
        self._current: tk.Misc | None = None

    def add(self, page, text: str = "") -> None:
        button = RoundButton(
            self._bar,
            text=text,
            command=lambda chosen=page: self.select(chosen),
            bg=look.panel,
            fg=look.ink,
            activebackground=look.button_active,
            activeforeground=look.ink,
            font=("Segoe UI", 11),
            padx=16,
            pady=8,
        )
        button.pack(side="left", padx=(0, 8), pady=2)
        self._tabs.append((page, button))
        if self._current is None:
            self.select(page)
        else:
            self._paint()

    def select(self, page=None):
        if page is None:
            return self._current
        chosen = next((child for child, _button in self._tabs if child is page or str(child) == str(page)), None)
        if chosen is None:
            return self._current
        if self._current is not None and self._current is not chosen:
            self._current.pack_forget()
        if not chosen.winfo_manager():
            chosen.pack(fill="both", expand=True)
        self._current = chosen
        self._paint()
        return chosen

    def tab(self, index, text=None, **_kw):
        _page, button = self._tabs[index]
        if text is not None:
            button.configure(text=text)
        return button

    def _paint(self) -> None:
        for page, button in self._tabs:
            on = page is self._current
            button.set_colors(
                look.button_active if on else look.panel,
                look.ink,
                look.button_active,
                look.ink,
            )
