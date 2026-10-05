"""The microphone keeps the next phrase while the recognizer is still busy."""

import threading
from pathlib import Path


def test_stopping_the_ear_aborts_a_blocked_microphone():
    import grok_assistant.listening.devices as devices
    from grok_assistant.listening.kroko_ear import KrokoEar
    from grok_assistant.listening.offline_ear import OfflineEar

    started = threading.Event()
    released = threading.Event()

    class Source:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            released.set()
            return False

        def abort(self):
            self.aborted.set()

        def read(self, _frames):
            started.set()
            assert self.aborted.wait(2)
            raise RuntimeError("stream aborted")

        def close(self):
            released.set()

        def __init__(self):
            self.aborted = threading.Event()

    source = Source()
    original = devices.open_input
    devices.open_input = lambda *_args, **_kwargs: source
    try:
        ear = OfflineEar("canary", lambda *_args: None)
        ear._model_ready.set()
        ear._recognizer_live = object()
        worker = threading.Thread(target=ear._loop, daemon=True)
        worker.start()
        assert started.wait(1)
        ear.stop()
        worker.join(1.5)
        assert released.is_set()
        assert not worker.is_alive()
        assert ear.error == ""
    finally:
        devices.open_input = original

    calls = []

    class Held:
        def abort(self):
            calls.append("abort")

    kroko = KrokoEar(lambda *_args: None)
    kroko._bind_source(Held())
    kroko.stop()
    assert calls == ["abort"]


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


def test_a_known_word_is_shown_before_the_phrase_is_sent():
    import numpy as np

    from grok_assistant.listening.offline_ear import OfflineEar

    partials = []
    finals = []
    calls = []

    class Stream:
        def __init__(self, text):
            self.result = type("Result", (), {"text": text})()

        def accept_waveform(self, _rate, _audio):
            return None

    class Recognizer:
        def create_stream(self):
            calls.append("read")
            return Stream("hola")

        def decode_stream(self, _stream):
            return None

    ear = OfflineEar(
        "small",
        lambda text, _audio: finals.append(text),
        on_partial=lambda text, _seq: partials.append(text),
    )
    ear._recognizer_live = Recognizer()
    ear._transcribe_partial(np.zeros(16000, dtype=np.float32))
    ear._transcribe(np.zeros(24000, dtype=np.float32), False)
    assert partials == ["hola"]
    assert finals == ["hola"]
    assert calls == ["read"]


def test_a_failed_reading_does_not_drop_the_next_phrase():
    from grok_assistant.listening.offline_ear import OfflineEar

    notes = []
    heard = []

    class Stream:
        def __init__(self):
            self.result = type("Result", (), {"text": "segundo"})()

        def accept_waveform(self, _rate, _audio):
            return None

    class Recognizer:
        def __init__(self):
            self.n = 0

        def create_stream(self):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("roto")
            return Stream()

        def decode_stream(self, _stream):
            return None

    ear = OfflineEar("small", lambda text, _audio: heard.append(text))
    ear._recognizer_live = Recognizer()
    ear._report = notes.append
    worker = threading.Thread(target=ear._serve_clips, daemon=True)
    worker.start()
    ear._submit("uno", False)
    ear._submit("dos", False)
    for _ in range(40):
        if heard:
            break
        threading.Event().wait(0.05)
    ear.stop()
    worker.join(1)
    assert heard == ["segundo"]
    assert any("roto" in note for note in notes)


def test_the_live_wav_keeps_the_phrase_and_drops_a_rejected_one(tmp_path):
    import numpy as np

    from grok_assistant.listening.enroll_audio import read_wav
    from grok_assistant.listening.spool import PhraseTape

    tape = PhraseTape(tmp_path)
    tape.write(np.full(1600, 0.25, dtype=np.float32))
    kept = tape.finish(True)
    assert kept is not None and kept.exists()
    audio = read_wav(kept)
    assert audio is not None and audio.shape[0] == 1600
    assert abs(float(audio[0]) - 0.25) < 0.01
    rejected = PhraseTape(tmp_path)
    rejected.write(np.zeros(3200, dtype=np.float32))
    assert rejected.finish(False) is None
    assert kept.exists()
    for _ in range(31):
        extra = PhraseTape(tmp_path)
        extra.write(np.full(1600, 0.1, dtype=np.float32))
        extra.finish(True)
    assert len(list(tmp_path.glob("frase-*.wav"))) == 30


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
