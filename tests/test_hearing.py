"""The microphone keeps the next phrase while the recognizer is still busy."""

import threading
from pathlib import Path


def test_a_busy_recognizer_keeps_the_next_phrase():
    from grok_assistant.listening.offline_ear import OfflineEar

    gate = threading.Event()
    entered = threading.Event()
    heard = []
    caller = threading.current_thread()

    class Stream:
        def __init__(self, text):
            self.result = type("Result", (), {"text": text})()

        def accept_waveform(self, _rate, _audio):
            return None

    class Recognizer:
        def __init__(self):
            self.pending = ["primero", "segundo"]

        def create_stream(self):
            return Stream(self.pending.pop(0))

        def decode_stream(self, stream):
            if stream.result.text == "primero":
                entered.set()
                assert gate.wait(2)

    ear = OfflineEar("small", lambda text, _audio: heard.append((text, threading.current_thread())))
    ear._recognizer_live = Recognizer()
    worker = threading.Thread(target=ear._serve_clips, daemon=True)
    worker.start()
    ear._clips.put(("uno", False))
    assert entered.wait(1)
    ear._clips.put(("dos", False))
    assert ear._clips.qsize() == 1
    gate.set()
    for _ in range(20):
        if len(heard) == 2:
            break
        threading.Event().wait(0.05)
    ear.stop()
    worker.join(1)
    assert [text for text, _thread in heard] == ["primero", "segundo"]
    assert heard[0][1] is not caller


def test_the_local_model_server_stays_running(tmp_path, monkeypatch):
    import grok_assistant.mind.local_llm as mind_mod
    from grok_assistant.mind.local_llm import LocalMind

    mind = LocalMind(tmp_path)
    up = {"ok": False}
    started = []

    class Proc:
        def poll(self):
            return None

    def popen(*_args, **_kwargs):
        started.append(1)
        up["ok"] = True
        return Proc()

    monkeypatch.setattr(mind, "available", lambda: True)
    monkeypatch.setattr(mind, "_healthy", lambda: up["ok"])
    monkeypatch.setattr(mind, "_model_file", lambda _folder: Path("model.gguf"))
    monkeypatch.setattr(mind_mod, "_llama_exe", lambda _folder: Path("llama-server.exe"))
    monkeypatch.setattr(mind_mod.subprocess, "Popen", popen)
    assert mind.warm() is True
    assert mind.warm() is True
    assert started == [1]
