"""Colors for the window. A JSON file next to the executable can add another theme."""

from __future__ import annotations

import json
from pathlib import Path

from grok_assistant.paths import exe_dir

KEYS = (
    "bg", "panel", "ink", "muted", "amber", "teal", "green", "field",
    "button", "button_active", "pause", "pause_active", "quit", "quit_active",
    "time", "mode_ink", "danger", "select", "chip_ink",
    "flow_on", "flow_off", "flow_dim",
    "menu_bg", "menu_hot", "menu_ink", "menu_muted", "menu_line",
)

FALLBACK = {
    "bg": "#14181e",
    "panel": "#1c232c",
    "ink": "#e7eef2",
    "muted": "#8ea0ab",
    "amber": "#e8a030",
    "teal": "#8fd0c4",
    "green": "#3ddc97",
    "field": "#0e1216",
    "button": "#2a3340",
    "button_active": "#3a4656",
    "pause": "#1c3a36",
    "pause_active": "#24564e",
    "quit": "#3a2a22",
    "quit_active": "#5a4030",
    "time": "#667884",
    "mode_ink": "#d7c4a3",
    "danger": "#e06a6a",
    "select": "#d7e2ea",
    "chip_ink": "#10241c",
    "flow_on": "#16302c",
    "flow_off": "#2c3844",
    "flow_dim": "#3a4656",
    "menu_bg": "#0e1418",
    "menu_hot": "#3a4656",
    "menu_ink": "#f4f7f8",
    "menu_muted": "#9aafbb",
    "menu_line": "#314552",
}


class Look:
    """The colors the window is using right now."""

    def __init__(self) -> None:
        self.id = "noche"
        self.name = "Noche"
        self.font = ("Segoe UI", 12)
        self.font_bold = ("Segoe UI", 18, "bold")
        self.mono = ("Consolas", 12)
        self._values = dict(FALLBACK)

    def __getattr__(self, key: str):
        if key in self._values:
            return self._values[key]
        raise AttributeError(key)

    def apply(self, item: "Theme") -> None:
        self.id = item.id
        self.name = item.name
        self._values = dict(item.colors)
        self.font = item.font
        self.font_bold = item.font_bold
        self.mono = item.mono


look = Look()


class Theme:
    def __init__(self, id: str, name: str, colors: dict, font, font_bold, mono) -> None:
        self.id = id
        self.name = name
        self.colors = colors
        self.font = font
        self.font_bold = font_bold
        self.mono = mono

    def menu_refs(self) -> dict[str, int]:
        return {key: colorref(self.colors[key]) for key in ("menu_bg", "menu_hot", "menu_ink", "menu_muted", "menu_line")}


def colorref(value: str) -> int:
    text = value.lstrip("#")
    red, green, blue = int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    return (blue << 16) | (green << 8) | red


def bundled_dir() -> Path:
    return Path(__file__).resolve().parent / "themes"


def user_dir() -> Path:
    """Folder beside GrokAssistant.exe. A source run uses dist/themes."""
    return exe_dir() / "themes"


def _font(raw, fallback: tuple) -> tuple:
    if isinstance(raw, list) and raw and all(isinstance(part, (str, int)) for part in raw):
        return tuple(raw)
    return fallback


def load_file(path: Path) -> Theme | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    colors = dict(FALLBACK)
    for key in KEYS:
        value = raw.get(key)
        if isinstance(value, str) and value.startswith("#") and len(value) == 7:
            colors[key] = value
    name = str(raw.get("name") or path.stem).strip() or path.stem
    return Theme(
        path.stem,
        name,
        colors,
        _font(raw.get("font"), ("Segoe UI", 12)),
        _font(raw.get("font_bold"), ("Segoe UI", 18, "bold")),
        _font(raw.get("mono"), ("Consolas", 12)),
    )


def available() -> list[Theme]:
    found: dict[str, Theme] = {}
    for folder in (bundled_dir(), user_dir()):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json")):
            item = load_file(path)
            if item is not None:
                found[item.id] = item
    if "noche" not in found:
        found["noche"] = Theme("noche", "Noche", dict(FALLBACK), ("Segoe UI", 12), ("Segoe UI", 18, "bold"), ("Consolas", 12))
    rows = list(found.values())
    rows.sort(key=lambda item: (item.id != "noche", item.name.casefold()))
    return rows


def theme_by_id(theme_id: str) -> Theme:
    wanted = (theme_id or "noche").strip() or "noche"
    for item in available():
        if item.id == wanted:
            return item
    for item in available():
        if item.id == "noche":
            return item
    return available()[0]


def apply_saved(theme_id: str) -> Theme:
    item = theme_by_id(theme_id)
    look.apply(item)
    return item
