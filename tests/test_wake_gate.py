"""The phoneme door. No model is downloaded, and no microphone is opened."""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from grok_assistant.notebook.settings import Settings, resolve_wake_gate


def test_old_settings_load_texto(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"wake_name": "grok", "recognizer": "kroko"}), encoding="utf-8")
    assert Settings.load(path).wake_gate == "texto"


def test_odd_wake_gate_loads_texto(tmp_path):
    path = tmp_path / "settings.json"
    for odd in ("sonar", "phoneme", "", None):
        path.write_text(json.dumps({"wake_gate": odd}), encoding="utf-8")
        assert Settings.load(path).wake_gate == "texto"


def test_keyboard_request_stays_texto():
    assert resolve_wake_gate("fonema", recognizer="teclado", wake_name="grok", phrase_ready=True) == ("texto", "micro")
    assert resolve_wake_gate("fonema", recognizer="teclado", wake_name="Miguel", phrase_ready=False) == ("texto", "micro")


def test_a_name_or_a_missing_line_stays_texto():
    assert resolve_wake_gate("fonema", recognizer="kroko", wake_name="Miguel", phrase_ready=True) == ("texto", "nombre")
    assert resolve_wake_gate("fonema", recognizer="kroko", wake_name="Grok", phrase_ready=False) == ("texto", "frase")
    assert resolve_wake_gate("fonema", recognizer="kroko", wake_name="grok", phrase_ready=True) == ("fonema", "")
    assert resolve_wake_gate("texto", recognizer="kroko", wake_name="grok", phrase_ready=True) == ("texto", "")


def test_a_phrase_line_needs_phonemes_and_the_mark(tmp_path):
    """The phones below are only a format fixture. They are not a checked «hola grok» line."""
    from grok_assistant.listening.phoneme_ear import prepared_line

    assert prepared_line(tmp_path) == ""
    path = tmp_path / "hola_grok.txt"
    path.write_text("# nota\n:1.5 #0.25 @HOLA_GROK\n", encoding="utf-8")
    assert prepared_line(tmp_path) == ""
    path.write_text("HH OW L AH G R AA K @HOLA_GROK :1.2 #0.25\n", encoding="utf-8")
    assert prepared_line(tmp_path) == "HH OW L AH G R AA K @HOLA_GROK :1.2 #0.25"


def _spy_cloud(hub):
    seen = []
    real = hub.brain._cloud

    def spy(heard):
        seen.append(heard)
        return real(heard)

    hub.brain._cloud = spy
    return seen


def test_fake_trigger_with_a_tail_calls_cloud_and_does_not_say_hola(world):
    hub, cli, _clock = world
    seen = _spy_cloud(hub)
    result = hub.hear_phoneme("hola grok, ¿qué hora es?")
    assert seen == ["qué hora es"]
    assert "Hola." not in result.spoken
    assert cli.calls[0][0] == "converse"
    assert cli.calls[0][1] == "qué hora es"
    assert hub.brain.in_conversation


def test_words_without_the_name_still_go_to_cloud(world):
    hub, cli, _clock = world
    seen = _spy_cloud(hub)
    result = hub.hear_phoneme("qué hora es")
    assert seen == ["qué hora es"]
    assert "Hola." not in result.spoken
    assert cli.calls[0][1] == "qué hora es"
    assert hub.brain.in_conversation


def test_fake_trigger_with_greeting_only_opens_and_greets(world):
    hub, cli, _clock = world
    seen = _spy_cloud(hub)
    result = hub.hear_phoneme("hola grok")
    assert seen == []
    assert hub.brain.in_conversation
    assert result.spoken == ["Hola."]
    assert cli.calls == []


def test_an_empty_reading_uses_the_wake_greeting(world):
    hub, cli, _clock = world
    result = hub.hear_phoneme("")
    assert hub.brain.in_conversation
    assert result.spoken == ["Hola."]
    assert cli.calls == []


def test_fake_trigger_with_another_voiceprint_does_not_open(world):
    hub, cli, _clock = world
    hub.brain.embedder_ready = True
    hub.brain.speakers.add("Ana", [[1.0, 0.0]], lock=True)
    result = hub.hear_phoneme("hola grok, ¿qué hora es?", speaker_id="Luis")
    assert result.spoken == []
    assert not hub.brain.in_conversation
    assert cli.calls == []
    opened = hub.hear_phoneme("hola grok", speaker_id="Ana")
    assert opened.spoken
    assert hub.brain.in_conversation


class _Spotter:
    def __init__(self):
        self.n = 0
        self.last_times: list[float] = []

    def accept(self, _chunk) -> str:
        self.n += 1
        if self.n == 10:
            self.last_times = [0.4]
            return "@HOLA_GROK"
        return ""

    def reset(self) -> None:
        self.last_times = []


def _ear(on_phrase, closed=None):
    from grok_assistant.listening.phoneme_ear import PhonemeEar

    ear = PhonemeEar(on_phrase, closed=closed)
    spotter = _Spotter()
    ear._armed = True
    ear._spotter = spotter
    return ear, spotter


def test_a_closed_or_paused_detector_takes_no_audio():
    chunk = np.zeros(1600, dtype=np.float32)
    closed, spotter = _ear(lambda _keyword, _phrase: True, closed=lambda: True)
    assert closed.feed(chunk) is False
    assert spotter.n == 0
    paused, other = _ear(lambda _keyword, _phrase: True)
    paused.set_paused(True)
    assert paused.feed(chunk) is False
    assert other.n == 0


def test_a_fake_trigger_waits_out_the_tail_and_keeps_the_preroll():
    seen = []

    def on_phrase(keyword, phrase):
        seen.append((keyword.copy(), phrase.copy()))
        return True

    ear, spotter = _ear(on_phrase)
    chunk = np.zeros(1600, dtype=np.float32)
    for _index in range(10):
        assert ear.feed(chunk) is True
    assert seen == []
    assert spotter.n == 10
    for _index in range(11):
        assert ear.feed(chunk) is True
    assert seen == []
    assert spotter.n == 10
    assert ear.feed(chunk) is True
    assert len(seen) == 1
    keyword, phrase = seen[0]
    assert phrase.size > keyword.size
    assert keyword.size >= int(0.4 * 16000)
    assert spotter.n == 10
    assert ear.feed(chunk) is False


def test_start_without_the_prepared_line_does_not_open_the_microphone(tmp_path, monkeypatch):
    from grok_assistant.listening import phoneme_ear

    monkeypatch.setattr(phoneme_ear, "model_dir", lambda: None)
    ear = phoneme_ear.PhonemeEar(lambda _keyword, _phrase: True)
    assert ear.start() is False
    assert ear.error == "falta la frase preparada"
    monkeypatch.setattr(phoneme_ear, "model_dir", lambda: tmp_path)
    (tmp_path / "tokens.txt").write_text("a\n", encoding="utf-8")
    again = phoneme_ear.PhonemeEar(lambda _keyword, _phrase: True)
    assert again.start() is False
    assert again.error == "falta la frase preparada"


@pytest.fixture
def gate_app(world, monkeypatch):
    import queue

    from grok_assistant.listening import phoneme_ear
    from grok_assistant.ui.ears import EarMixin
    from grok_assistant.ui.worker import WorkerMixin

    hub, cli, clock = world
    hub.brain.settings.wake_gate = "fonema"
    hub.brain.settings.recognizer = "kroko"
    hub.brain.settings.wake_name = "grok"
    hub.brain.persist()
    made = []

    class FakeEar:
        def __init__(self, on_phrase, on_status=None, device="", closed=None):
            self.on_phrase = on_phrase
            self.device = str(device or "")
            self._closed = closed or (lambda: False)
            self.stopped = False
            self.paused = False
            self.feeds = 0
            made.append(self)

        def start(self):
            return True

        def stop(self):
            self.stopped = True

        def join(self, timeout=1.5):
            return None

        def set_paused(self, paused):
            self.paused = bool(paused)

        def feed(self, _samples):
            if self.stopped or self.paused or self._closed():
                return False
            self.feeds += 1
            return True

    monkeypatch.setattr(phoneme_ear, "PhonemeEar", FakeEar)
    monkeypatch.setattr(phoneme_ear, "phrase_ready", lambda _name: True)

    class App(EarMixin, WorkerMixin):
        def __init__(self):
            self.hub = hub
            self.user_paused = False
            self._ears_suspended = False
            self._mic_held = False
            self._speaking = False
            self.phoneme = None
            self._phoneme_failed = ""
            self.dictation = None
            self.kroko = None
            self.offline = None
            self.music = SimpleNamespace(loaded=False, user_paused=False)
            self.logs = []
            self.spoken = []
            self.jobs = queue.Queue()
            self.voiceprint = SimpleNamespace(embed=lambda _audio: [0.0, 1.0])

        def _hearing_device(self):
            return ""

        def _note(self, text):
            self.logs.append(text)

        def say(self, text):
            if text:
                self.spoken.append(text)

        def _apply(self, result):
            return None

        def _refresh(self):
            return None

        def _ask(self, title):
            return ""

        def _write_crash(self, exc):
            raise exc

    return App(), hub, cli, clock, made


def test_open_chat_feeds_the_detector_nothing_and_quiet_brings_it_back(gate_app):
    app, hub, _cli, clock, made = gate_app
    chunk = np.zeros(1600, dtype=np.float32)
    app._sync_ear()
    live = app.phoneme
    assert live is not None
    assert live.feed(chunk) is True
    app.music.loaded = True
    assert live.feed(chunk) is False
    app.music.loaded = False
    assert live.feed(chunk) is True
    hub.brain.in_conversation = True
    app._sync_ear()
    assert app.phoneme is None
    assert live.stopped
    assert live.feed(chunk) is False
    clock.t += float(hub.brain.settings.quiet_minutes) * 60.0 + 1.0
    app._job("tick", "")
    assert not hub.brain.in_conversation
    assert app.spoken == []
    assert app.phoneme is not None
    assert app.phoneme is not live
    assert not app.phoneme.stopped
    assert app.phoneme.feed(chunk) is True
    assert len(made) == 2


def test_gracias_brings_the_detector_back(gate_app):
    app, hub, cli, _clock, _made = gate_app
    hub.brain.in_conversation = True
    app._sync_ear()
    assert app.phoneme is None
    app._job("phrase", "gracias", None, None, "")
    assert "De nada." in app.spoken
    assert not hub.brain.in_conversation
    assert cli.calls == []
    assert app.phoneme is not None
    assert app.phoneme.feed(np.zeros(160, dtype=np.float32)) is True


def test_another_voiceprint_does_not_queue_the_phrase(gate_app):
    app, hub, _cli, _clock, _made = gate_app
    hub.brain.embedder_ready = True
    hub.brain.speakers.add("Ana", [[1.0, 0.0]], lock=True)
    app._sync_ear()
    audio = np.zeros(1600, dtype=np.float32)
    assert app._on_phoneme_phrase(audio, audio) is False
    assert app.jobs.empty()
    assert not hub.brain.in_conversation
    assert app.phoneme.feed(audio) is True


def test_renaming_away_from_grok_returns_to_texto(gate_app):
    app, hub, _cli, _clock, _made = gate_app
    app._sync_ear()
    assert app.phoneme is not None
    app._job("rename", "Miguel")
    assert hub.brain.settings.wake_name == "Miguel"
    assert hub.brain.settings.wake_gate == "texto"
    assert app.phoneme is None
    assert any("escrita" in line for line in app.logs)


def test_the_simple_tab_keeps_fonema_beside_the_talk_mode_and_keyboard_stays_texto(tmp_path):
    import tkinter as tk

    from grok_assistant.i18n import activate
    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    root = tk.Tk()
    root.geometry("1100x800+40+40")
    root.attributes("-alpha", 0)
    root.withdraw()
    try:
        hub = build(tmp_path, tmp_path / "agents")
        hub.brain.settings.recognizer = "teclado"
        hub.brain.persist()
        activate("es")
        app = TrayApp(root, hub)
        hub.brain.settings.recognizer = "teclado"
        app._paint_simple()
        root.deiconify()
        root.update()
        assert app.gate_label.cget("text") == "Inicio de la charla"
        assert app.talk_mode_box.master.master is app.gate_box.master.master
        assert app.talk_mode_box.master.winfo_y() == app.gate_box.master.winfo_y()
        assert app.talk_mode_box.master.winfo_x() != app.gate_box.master.winfo_x()
        app.gate_box.set("Fonema")
        app._pick_wake_gate()
        root.update()
        assert hub.brain.settings.wake_gate == "texto"
        assert app.gate_box.get() == "Texto"
        assert any("micrófono" in line for line in hub.brain.logs)
    finally:
        activate("es")
        root.destroy()
