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


def test_a_written_false_does_not_turn_file_edits_on(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"grok_files": "false", "theme": "mar"}), encoding="utf-8")
    item = Settings.load(path)
    assert item.grok_files is False
    assert item.theme == "mar"
    path.write_text(json.dumps({"grok_files": True}), encoding="utf-8")
    assert Settings.load(path).grok_files is True
