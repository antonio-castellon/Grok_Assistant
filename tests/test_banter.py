"""Saved greetings and waiting lines. They never come from the network."""

from grok_assistant.speaking.banter import KINDS, THEMES, apply_choice, catalog, pool
from grok_assistant.notebook.settings import Settings


def test_each_language_has_every_kind_and_theme():
    for code in ("es", "en", "fr", "de"):
        rows = catalog(code)
        texts = [row["text"] for row in rows]
        assert len(texts) == len(set(texts))
        assert all(len(line) <= 220 for line in texts)
        for kind in KINDS:
            for theme in THEMES:
                found = [row for row in rows if row["kind"] == kind and row["theme"] == theme]
                assert len(found) >= 4, f"{code} {kind} {theme}"


def test_a_filter_keeps_only_the_chosen_kind_and_theme():
    lines = pool("es", ["joke"], ["sports"])
    assert len(lines) >= 4
    assert all("portería" in line or "balón" in line or "árbitro" in line or "carrera" in line or "entren" in line for line in lines)
    everything = pool("es", None, None)
    assert len(everything) > len(lines)


def test_mix_selects_every_kind_and_the_last_box_stays_on():
    assert apply_choice(["joke"], KINDS, "mix", True, mix=True) == list(KINDS)
    assert apply_choice(list(KINDS), KINDS, "mix", False, mix=True) == [KINDS[0]]
    assert apply_choice(["fact"], KINDS, "fact", False) == ["fact"]
    assert apply_choice(["fact"], KINDS, "joke", True) == ["joke", "fact"]


def test_an_old_config_starts_with_every_kind_and_theme(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"model": "grok-4.7"}', encoding="utf-8")
    loaded = Settings.load(path)
    assert loaded.line_kinds == list(KINDS)
    assert loaded.line_themes == list(THEMES)


def test_the_greeting_menu_uses_checkboxes(tmp_path):
    import tkinter as tk

    from conftest import tk_root
    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    root = tk_root()
    root.withdraw()
    try:
        app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
        root.update()
        bar = app.root.nametowidget(app.root["menu"])
        labels = [bar.entrycget(index, "label") for index in range(bar.index("end") + 1)]
        assert labels == ["Escucha", "Voz", "Charla", "Música", "Personas", "Ajustes", "Acerca de"]
        app._fill_voz()
        voice = []
        for index in range(app.menu_voz.index("end") + 1):
            try:
                voice.append(app.menu_voz.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert "Saludos" in voice
        assert "Personalidad" in voice
        app._fill_banter_kinds()
        kinds = app.menu_banter_kinds
        boxes = []
        for index in range(kinds.index("end") + 1):
            try:
                boxes.append(kinds.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert kinds.entrycget(0, "variable")
        assert boxes[0] == "Chistes muy cortos"
        assert "Mezcla de todo" in boxes
        app._banter_set("banter-theme:sports", False)
        assert "sports" not in app.hub.brain.settings.line_themes
        assert app.hub.brain.settings.line_themes
        tray = app._tray_items()
        voice_tray = next(item for item in tray if item[0] == "sub" and item[1] == "Voz")
        banter = next(item for item in voice_tray[2] if item[0] == "sub" and item[1] == "Saludos")
        kind_menu = banter[2][0][2]
        assert kind_menu[-1][2] == "banter-kind:mix"
        assert kind_menu[-1][3] is True
    finally:
        root.destroy()
