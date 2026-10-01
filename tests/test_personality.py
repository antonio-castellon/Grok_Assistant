"""The spoken answer can wear a person, numeric traits, and a free behavior text."""

from grok_assistant.house.personality import compose, load_person, normalize_personality, voice_prompt
from grok_assistant.cloud.prompts import VOICE_SYSTEM
from grok_assistant.notebook.settings import Settings


def test_no_person_leaves_the_voice_prompt_alone():
    assert compose({}) == ""
    assert voice_prompt(load_person(""), VOICE_SYSTEM) == VOICE_SYSTEM


def test_restore_reads_the_original_numbers_and_text():
    from grok_assistant.house.personality import load_person

    stock = load_person("ines", stock=True)
    assert stock["humor"] == 25
    assert "torpe" in stock["behavior"]


def test_a_person_carries_meaning_traits_and_behavior():
    cfg = load_person("ines")
    assert cfg["warmth"] == 80
    assert "torpe" in cfg["behavior"]
    block = compose(cfg)
    assert "Inés" in block
    assert "la maestra" in block
    assert "calidez 80" in block
    assert "torpe" in block
    assert "techos" in block


def test_free_behavior_replaces_the_stock_paragraph():
    cfg = load_person("bruno")
    cfg["behavior"] = "Habla despacio y no hagas chistes hoy."
    cfg["humor"] = 12
    block = compose(cfg)
    assert "Habla despacio y no hagas chistes hoy." in block
    assert "humor 12" in block
    assert "No expliques el chiste" not in block


def test_traits_stay_between_zero_and_one_hundred():
    cfg = normalize_personality({"profile": "alex", "humor": 400, "warmth": -5, "tone": "no-such"})
    assert cfg["humor"] == 100
    assert cfg["warmth"] == 0
    assert cfg["tone"] == "auto"
    assert cfg["profile"] == "alex"


def test_settings_roundtrip_keeps_a_custom_person(tmp_path):
    path = tmp_path / "config.json"
    item = Settings()
    item.personality = load_person("marcos")
    item.personality["behavior"] = "Pregunta si hace falta Kubernetes."
    item.save(path)
    loaded = Settings.load(path)
    assert loaded.personality["profile"] == "marcos"
    assert loaded.personality["directness"] == 90
    assert loaded.personality["behavior"] == "Pregunta si hace falta Kubernetes."


def test_personality_window_saves_a_free_behavior(tmp_path):
    import tkinter as tk

    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    root = tk.Tk()
    root.withdraw()
    app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
    try:
        app._choose_person("ines")
        root.update()
        assert "ejemplo" in app._persona_meaning.get()
        assert "Inés" in app._persona_choice.get()
        app._persona_scales["humor"].set(11)
        app._persona_behavior.delete("1.0", "end")
        app._persona_behavior.insert("1.0", "Habla despacio y con un ejemplo.")
        app._persona_save()
        assert app._persona_win is None
        saved = app.hub.brain.settings.personality
        assert saved["profile"] == "ines"
        assert saved["humor"] == 11
        assert saved["behavior"] == "Habla despacio y con un ejemplo."
        assert "Habla despacio y con un ejemplo." in compose(saved)
        bar = app.root.nametowidget(app.root["menu"])
        labels = [bar.entrycget(index, "label") for index in range(bar.index("end") + 1)]
        assert labels[-1] == "Acerca de"
        assert "Mercado" not in labels
        assert "Acerca de + Ayuda" not in labels
        app._fill_settings()
        settings = []
        for index in range(app.menu_settings.index("end") + 1):
            try:
                settings.append(app.menu_settings.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert "Voice market" in settings
    finally:
        root.destroy()


def test_windows_follow_the_selected_language(tmp_path):
    import tkinter as tk

    from grok_assistant.rules.hub import build
    from grok_assistant.i18n import activate
    from grok_assistant.ui.app import TrayApp
    from grok_assistant.ui.theme import look

    root = tk.Tk()
    root.withdraw()
    try:
        hub = build(tmp_path, tmp_path / "agents")
        activate("en")
        app = TrayApp(root, hub)
        root.update()
        bar = app.root.nametowidget(app.root["menu"])
        labels = [bar.entrycget(index, "label") for index in range(bar.index("end") + 1)]
        assert labels == ["Listen", "Voice", "Chat", "Music", "People", "Settings", "About"]
        app._fill_voz()
        voice = []
        for index in range(app.menu_voz.index("end") + 1):
            try:
                voice.append(app.menu_voz.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert "Personality" in voice
        assert "Greetings" in voice
        talk = [app.menu_talk.entrycget(index, "label") for index in range(app.menu_talk.index("end") + 1)]
        assert talk == ["Model", "Session", "Agent"]
        assert app.pause_button.cget("text") == "Pause listening"
        assert app.send_button.cget("text") == "Send"
        app._build_personality()
        root.update()
        assert app._persona_win.title() == "Personality"
        assert app._persona_choice.get().startswith("No person")
        assert app._persona_tone.get() == "Automatic, from the phrase"
        app._build_about()
        root.update()
        assert app._about_win.title() == "About"
        app.hub.brain.settings.recognizer = "kroko"
        app._build_market()
        root.update()
        used = [
            (offer, button, chip)
            for offer, button, chip in app._market_marks
            if chip.cget("text") == "IN USE" and chip.winfo_manager()
        ]
        assert used
        offer, button, chip = used[0]
        assert offer.engine_id == "kroko"
        assert chip.cget("bg") == look.green
        assert not button.winfo_manager()
    finally:
        activate("es")
        root.destroy()


def test_an_old_config_without_personality_still_loads(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"model": "grok-4.7", "volume": 40}', encoding="utf-8")
    loaded = Settings.load(path)
    assert loaded.volume == 40
    assert loaded.personality["profile"] == ""
    assert compose(loaded.personality) == ""
