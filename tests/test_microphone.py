"""The Settings menu can pick an input other than the system default."""

import json

from grok_assistant.listening.devices import list_inputs, normalize_microphone, resolve_microphone
from grok_assistant.notebook.settings import Settings


def test_one_row_per_microphone_name():
    devices = [
        {"index": 0, "name": "Micrófono de la mesa", "hostapi": 0, "max_input_channels": 2},
        {"index": 1, "name": "Micrófono de la mesa", "hostapi": 1, "max_input_channels": 2},
        {"index": 2, "name": "Micrófono USB", "hostapi": 1, "max_input_channels": 1},
        {"index": 3, "name": "Auriculares", "hostapi": 0, "max_input_channels": 1},
        {"index": 4, "name": "Altavoces", "hostapi": 1, "max_input_channels": 0},
    ]
    rows = list_inputs(devices, 1)
    assert [(row["name"], row["index"]) for row in rows] == [
        ("Micrófono de la mesa", 1),
        ("Micrófono USB", 2),
        ("Auriculares", 3),
    ]


def test_a_missing_microphone_falls_back_to_the_default():
    mics = [{"index": 4, "name": "Micrófono USB", "hostapi": 0}]
    assert resolve_microphone("", mics) == ("", None)
    assert resolve_microphone("Micrófono USB", mics) == ("Micrófono USB", 4)
    assert resolve_microphone("  ya no está  ", mics) == ("", None)
    assert normalize_microphone("  a   b  ") == "a b"


def test_an_unread_device_list_keeps_the_saved_name(monkeypatch):
    monkeypatch.setattr("grok_assistant.listening.devices.listed_inputs", lambda: None)
    assert resolve_microphone("Micrófono USB") == ("Micrófono USB", None)


def test_settings_keep_a_microphone_name(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"microphone": "  Mesa  "}), encoding="utf-8")
    assert Settings.load(path).microphone == "Mesa"
    path.write_text("{}", encoding="utf-8")
    assert Settings.load(path).microphone == ""


def test_open_input_passes_the_chosen_index(monkeypatch):
    monkeypatch.setattr(
        "grok_assistant.listening.devices.listed_inputs",
        lambda: [{"index": 7, "name": "USB", "hostapi": 0}],
    )
    opened = {}

    class Stream:
        def __init__(self, **kwargs):
            opened.clear()
            opened.update(kwargs)

    import sys
    import types

    fake = types.ModuleType("sounddevice")
    fake.InputStream = Stream
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    from grok_assistant.listening.devices import open_input

    open_input("USB", 16000)
    assert opened["device"] == 7
    assert opened["samplerate"] == 16000
    open_input("", 16000)
    assert "device" not in opened


def test_settings_menu_picks_a_microphone_and_reopens_the_ear(tmp_path, monkeypatch):
    import tkinter as tk

    from grok_assistant.i18n import activate
    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    mics = [
        {"index": 1, "name": "Micrófono de la mesa", "hostapi": 0},
        {"index": 4, "name": "Micrófono USB", "hostapi": 0},
    ]
    monkeypatch.setattr("grok_assistant.listening.devices.listed_inputs", lambda: mics)
    created = []

    class Ear:
        def __init__(self, kind, on_line, on_status=None, silence=None, device=""):
            self.kind = kind
            self.device = device
            self.stopped = False
            created.append(self)

        def start(self):
            return True

        def stop(self):
            self.stopped = True

        def join(self, timeout=1.5):
            return None

    monkeypatch.setattr("grok_assistant.ui.ears.OfflineEar", Ear)
    root = tk.Tk()
    root.withdraw()
    try:
        activate("es")
        app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
        app._fill_settings()
        labels = []
        for index in range(app.menu_settings.index("end") + 1):
            try:
                labels.append(app.menu_settings.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert "Micrófono" in labels
        app._fill_microphone()
        choices = []
        for index in range(app.menu_microphone.index("end") + 1):
            try:
                choices.append(app.menu_microphone.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert choices[0].endswith("Predeterminado")
        assert "Micrófono USB" in choices
        app.hub.brain.settings.recognizer = "small"
        app._pick_microphone("Micrófono USB")
        assert app.hub.brain.settings.microphone == "Micrófono USB"
        assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["microphone"] == "Micrófono USB"
        assert created[-1].device == "Micrófono USB"
        app._pick_microphone("Micrófono de la mesa")
        assert created[0].stopped
        assert created[-1].device == "Micrófono de la mesa"
        app._pick_microphone("")
        assert app.hub.brain.settings.microphone == ""
        assert created[-1].device == ""
        rows = app._microphone_rows()
        assert rows[0][2] == "mic-default" and rows[0][3] is True
        activate("en")
        app._fill_settings()
        english = []
        for index in range(app.menu_settings.index("end") + 1):
            try:
                english.append(app.menu_settings.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert "Microphone" in english
    finally:
        activate("es")
        root.destroy()
