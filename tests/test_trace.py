"""A requested zip of what was heard, what the local model said, and what was decided."""

import json
import zipfile

import numpy as np

from grok_assistant.house.tracepack import save_trace
from grok_assistant.rules.hub import build


def test_the_zip_holds_the_wav_the_model_text_and_the_decision(tmp_path):
    hub = build(tmp_path / "data", tmp_path / "agents", account_dir=tmp_path / "account")
    hub.brain.keep_heard(
        "comando pregunta",
        np.zeros(1600, dtype=np.float32),
        primary="Comando pregunta.",
        second="",
        heard_by="Whisper small",
        who="antonio",
    )
    hub.brain.note_model(
        "comando pregunta",
        "cerrada",
        "No inventes órdenes.",
        {"accion": "ilegible", "orden": "", "texto": ""},
    )
    hub.run("comando pregunta")
    path = save_trace(hub.brain, hub.sent, tmp_path)
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert "registro.txt" in names
        assert "decisiones.json" in names
        assert "llm.json" in names
        assert "nube.json" in names
        assert "ajustes.json" in names
        assert "audio/01.wav" in names
        assert "audio/index.json" in names
        assert archive.read("audio/01.wav")[:4] == b"RIFF"
        heard = json.loads(archive.read("audio/index.json"))
        assert heard[0]["heard"] == "comando pregunta"
        assert heard[0]["heard_by"] == "Whisper small"
        model = json.loads(archive.read("llm.json"))
        assert model[0]["raw"] == "No inventes órdenes."
        assert model[0]["parsed"]["accion"] == "ilegible"
        decisions = json.loads(archive.read("decisiones.json"))
        assert any(item["heard"] == "comando pregunta" for item in decisions)
        assert "password" not in archive.read("ajustes.json").decode("utf-8")


def test_the_trace_button_sits_under_the_text_box(tmp_path):
    import tkinter as tk

    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    root = tk.Tk()
    root.withdraw()
    try:
        app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
        root.update()
        slaves = list(app.page_debug.pack_slaves())
        assert slaves.index(app.trace_row) == slaves.index(app.entry.master) + 1
        assert app.trace_button.cget("text") == "Guardar traza"
    finally:
        root.destroy()
