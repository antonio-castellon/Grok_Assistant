"""A theme file next to the executable can replace the built-in colors."""

import json

from grok_assistant.notebook.settings import Settings
from grok_assistant.ui import theme


def test_noche_matches_the_shipped_window_and_the_tray_color(tmp_path, monkeypatch):
    monkeypatch.setattr(theme, "user_dir", lambda: tmp_path)
    item = theme.theme_by_id("noche")
    assert item.name == "Noche"
    assert item.colors["bg"] == "#14181e"
    assert item.colors["menu_bg"] == "#0e1418"
    assert theme.colorref("#0e1418") == 0x0018140E
    assert theme.colorref("#3a4656") == 0x0056463A
    theme.apply_saved("noche")
    assert theme.look.bg == "#14181e"
    assert theme.look.id == "noche"


def test_a_file_beside_the_exe_overrides_and_fills_missing_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(theme, "user_dir", lambda: tmp_path)
    (tmp_path / "noche.json").write_text('{"name": "Noche", "bg": "#111111"}', encoding="utf-8")
    (tmp_path / "casa.json").write_text('{"name": "Casa", "bg": "#222222"}', encoding="utf-8")
    item = theme.theme_by_id("noche")
    assert item.colors["bg"] == "#111111"
    assert item.colors["ink"] == "#e7eef2"
    ids = [row.id for row in theme.available()]
    assert ids[0] == "noche"
    assert "casa" in ids
    assert theme.theme_by_id("no-such").id == "noche"


def test_the_extra_themes_keep_their_own_colors(tmp_path, monkeypatch):
    monkeypatch.setattr(theme, "user_dir", lambda: tmp_path)
    expect = {
        "aurora": ("Aurora", "#22243a", "#f4f5fb"),
        "cobre": ("Cobre", "#3a2c24", "#f8f1e8"),
        "lino": ("Lino", "#f7f4ec", "#241e16"),
        "oliva": ("Oliva", "#243028", "#f2f6f0"),
    }
    ids = [row.id for row in theme.available()]
    assert ids[0] == "noche"
    for theme_id, (name, bg, ink) in expect.items():
        item = theme.theme_by_id(theme_id)
        assert item.name == name
        assert item.colors["bg"] == bg
        assert item.colors["ink"] == ink
        assert theme_id in ids


def test_changing_theme_repaints_the_window(tmp_path):
    import tkinter as tk

    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    root = tk.Tk()
    root.withdraw()
    try:
        app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
        root.update_idletasks()
        app._apply_theme("dia")
        root.update()
        assert theme.look.id == "dia"
        assert root.cget("bg") == "#f4f1ea"
        assert app.talk_hint.cget("bg") == "#f4f1ea"
        assert len(root.winfo_children()) > 0
        app._apply_theme("noche")
        root.update()
        assert root.cget("bg") == "#14181e"
        assert app.talk_hint.cget("bg") == "#14181e"
    finally:
        root.destroy()


def test_a_written_false_does_not_turn_file_edits_on(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"grok_files": "false", "theme": "mar"}), encoding="utf-8")
    item = Settings.load(path)
    assert item.grok_files is False
    assert item.theme == "mar"
    path.write_text(json.dumps({"grok_files": True}), encoding="utf-8")
    assert Settings.load(path).grok_files is True
