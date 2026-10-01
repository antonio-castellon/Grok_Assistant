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


def _rgb(photo, x, y) -> tuple[int, int, int]:
    pixel = photo.getpixel((x, y))
    return tuple(pixel[:3])


def _hex(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _near(left, right, tol: int = 12) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(left, right))


def test_the_status_line_names_each_setting():
    from grok_assistant.i18n import activate
    from grok_assistant.ui.chrome import detail_line

    activate("es")
    line = detail_line({
        "model": "grok-4.7",
        "effort": "bajo",
        "voice": "4. Sharvard · España",
        "recognizer": "Whisper small",
        "identifier": "sin identificador",
        "session": "compartida",
        "volume": 70,
    })
    assert "modelo [grok-4.7]" in line
    assert "esfuerzo [bajo]" in line
    assert "voz [4. Sharvard · España]" in line
    assert "oído [Whisper small]" in line
    assert "identificador [sin identificador]" in line
    assert "sesión [compartida]" in line
    assert "volumen [70%]" in line


def test_changing_theme_repaints_the_window(tmp_path):
    import tkinter as tk

    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    root = tk.Tk()
    root.withdraw()
    try:
        app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
        root.update_idletasks()
        assert app.shared_label.cget("text") == "Días que se recuerdan las conversaciones"
        assert app.detail_label.master.pack_slaves() == [app.detail_label]
        app.detail_var.set("modelo [grok-4.7]   esfuerzo [bajo]")
        ranges = app.detail_label.tag_ranges("value")
        assert app.detail_label.get(ranges[0], ranges[1]) == "grok-4.7"
        assert app.detail_label.get(ranges[2], ranges[3]) == "bajo"
        assert app.detail_label.get("1.0", "1.8") == "modelo ["
        assert "bold" in str(app.detail_label.tag_cget("value", "font")).lower()
        assert app.state_label.master.pack_info()["side"] == "right"
        assert app.state_label.master.pack_info()["anchor"] == "n"
        assert app.chrome.cget("bg") == theme.look.panel
        assert app.detail_label.cget("bg") == theme.look.panel
        assert app.state_label.cget("bg") == theme.look.panel
        assert app.pages._bar.master is app.chrome
        assert app.pages._bar.cget("bg") == theme.look.panel
        assert app.footer.cget("bg") == theme.look.panel
        app.pages.select(app.page_flow)
        root.update()
        assert str(app.pages.select()) == str(app.page_flow)
        assert app.page_flow.winfo_manager() == "pack"
        assert app.page_simple.winfo_manager() == ""
        app.pages.tab(0, text="Simple")
        app.pages.select(app.page_simple)
        root.update()

        def _plate_is_round(button, fill: str, ground: str | None = None) -> None:
            plate = button.plate
            width, height = plate.size
            expected = _hex(ground or theme.look.bg)
            assert _near(_rgb(plate, 0, 0), expected)
            assert _near(_rgb(plate, height // 4, 0), expected)
            assert _near(_rgb(plate, width // 2, height // 2), _hex(fill), tol=6)
            assert not _near(_rgb(plate, 0, 0), _hex(fill), tol=6)

        _plate_is_round(app.simple_pause, theme.look.pause)
        _plate_is_round(app.pages._tabs[0][1], theme.look.button_active, theme.look.panel)
        app._apply_theme("dia")
        root.update()
        assert theme.look.id == "dia"
        assert root.cget("bg") == "#f4f1ea"
        assert app.talk_hint.cget("bg") == "#f4f1ea"
        assert app.chrome.cget("bg") == "#e7e1d6"
        assert app.pages._bar.cget("bg") == "#e7e1d6"
        assert len(root.winfo_children()) > 0
        _plate_is_round(app.simple_pause, "#d5ebe4")
        app._apply_theme("noche")
        root.update()
        assert root.cget("bg") == "#14181e"
        assert app.talk_hint.cget("bg") == "#14181e"
        _plate_is_round(app.simple_pause, "#1c3a36")
    finally:
        root.destroy()


def _flow_text(app) -> str:
    return "\n".join(
        app.flow.itemcget(item, "text")
        for item in app.flow.find_all()
        if app.flow.type(item) == "text"
    )


def _box_fill(app, title: str) -> str:
    for item in app.flow.find_all():
        if app.flow.type(item) != "text" or app.flow.itemcget(item, "text") != title:
            continue
        x, y = app.flow.coords(item)[:2]
        for other in app.flow.find_all():
            if app.flow.type(other) != "rectangle":
                continue
            x1, y1, x2, y2 = app.flow.coords(other)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return app.flow.itemcget(other, "fill")
    return ""


def test_open_chat_shows_a_direct_path_to_grok(tmp_path):
    import tkinter as tk

    from grok_assistant.i18n import activate
    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    activate("es")
    root = tk.Tk()
    root.withdraw()
    try:
        app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
        app.pages.select(app.page_flow)
        root.geometry("980x760+-2400+-2400")
        root.deiconify()
        root.update_idletasks()
        root.update()
        snap = {
            "banner_kind": "wait",
            "identifier": "sin identificador",
            "model": "grok-4.7",
            "recognizer": "Whisper small",
            "voice": "4. Sharvard · España",
            "last_heard": "qué hora es",
        }
        app.hub.brain.settings.talk_mode = "abierta"
        app.hub.brain.in_conversation = False
        app._draw_flow(snap)
        chosen = _flow_text(app)
        assert "filtro de Grok" in chosen
        assert "Aún cerrada" not in chosen
        assert "¿Conversación abierta?" not in chosen
        assert _box_fill(app, "Modelo local") == theme.look.field
        assert _box_fill(app, "Grok") == theme.look.flow_on
        snap["banner_kind"] = "talk"
        app.hub.brain.in_conversation = True
        app._draw_flow(snap)
        opened = _flow_text(app)
        assert "filtro de Grok" in opened
        assert _box_fill(app, "Modelo local") == theme.look.field
        app.hub.brain.settings.talk_mode = "seguida"
        snap["banner_kind"] = "wait"
        app._draw_flow(snap)
        other = _flow_text(app)
        assert "¿Conversación abierta?" in other
        assert "filtro de Grok" not in other
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
