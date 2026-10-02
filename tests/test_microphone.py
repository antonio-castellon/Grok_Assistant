"""The Settings menu can pick an input other than the system default."""

import json

from grok_assistant.house.music import match_audio_device
from grok_assistant.listening.devices import list_inputs, list_outputs, normalize_microphone, resolve_microphone, resolve_output
from grok_assistant.notebook.settings import Settings


def test_one_row_per_microphone_name():
    devices = [
        {"index": 0, "name": "Micrófono de la mesa", "hostapi": 0, "max_input_channels": 2},
        {"index": 1, "name": "Micrófono de la mesa", "hostapi": 1, "max_input_channels": 2},
        {"index": 2, "name": "Micrófono USB", "hostapi": 1, "max_input_channels": 1},
        {"index": 3, "name": "Auriculares", "hostapi": 0, "max_input_channels": 1},
        {"index": 4, "name": "Altavoces", "hostapi": 1, "max_input_channels": 0},
        {"index": 5, "name": "PC Speaker (Realtek)", "hostapi": 3, "max_input_channels": 2},
        {"index": 6, "name": "Stereo Mix (Realtek)", "hostapi": 3, "max_input_channels": 2},
    ]
    rows = list_inputs(devices, 1)
    assert [(row["name"], row["index"]) for row in rows] == [
        ("Micrófono de la mesa", 1),
        ("Micrófono USB", 2),
        ("Auriculares", 3),
    ]


def test_windows_keeps_wasapi_microphones_and_speakers():
    devices = [
        {"index": 0, "name": "Microsoft Sound Mapper - Input", "hostapi": 0, "max_input_channels": 2, "max_output_channels": 0},
        {"index": 4, "name": "Microsoft Sound Mapper - Output", "hostapi": 0, "max_input_channels": 0, "max_output_channels": 2},
        {"index": 8, "name": "Microphone (Jabra Link 380)", "hostapi": 0, "max_input_channels": 1, "max_output_channels": 0},
        {"index": 25, "name": "Microphone Array (AMD Audio Device)", "hostapi": 2, "max_input_channels": 2, "max_output_channels": 0},
        {"index": 27, "name": "Microphone (Jabra Link 380)", "hostapi": 2, "max_input_channels": 1, "max_output_channels": 0},
        {"index": 22, "name": "Speakers (Jabra Link 380)", "hostapi": 2, "max_input_channels": 0, "max_output_channels": 2},
        {"index": 23, "name": "Speakers (Realtek(R) Audio)", "hostapi": 2, "max_input_channels": 0, "max_output_channels": 2},
        {"index": 30, "name": "PC Speaker (Realtek HD Audio output with HAP)", "hostapi": 3, "max_input_channels": 2, "max_output_channels": 0},
        {"index": 34, "name": "Stereo Mix (Realtek HD Audio Stereo input)", "hostapi": 3, "max_input_channels": 2, "max_output_channels": 0},
        {"index": 40, "name": "Speakers (Realtek(R) Audio) [Loopback]", "hostapi": 2, "max_input_channels": 2, "max_output_channels": 0},
    ]
    hostapis = [{"name": "MME"}, {"name": "Windows DirectSound"}, {"name": "Windows WASAPI"}, {"name": "Windows WDM-KS"}]
    mics = list_inputs(devices, 0, hostapis)
    speakers = list_outputs(devices, 0, hostapis)
    assert [(row["name"], row["index"]) for row in mics] == [
        ("Microphone Array (AMD Audio Device)", 25),
        ("Microphone (Jabra Link 380)", 27),
    ]
    assert [(row["name"], row["index"]) for row in speakers] == [
        ("Speakers (Jabra Link 380)", 22),
        ("Speakers (Realtek(R) Audio)", 23),
    ]
    assert resolve_output("Speakers (Jabra Link 380)", speakers) == ("Speakers (Jabra Link 380)", 22)
    assert resolve_output("PC Speaker (Realtek HD Audio output with HAP)", speakers) == ("", None)


def test_mpv_matches_the_speaker_name():
    listing = "\n".join([
        "  'auto' (Autoselect device)",
        "  'wasapi/{56ab2f0c-0d20-4960-92c1-1e5d605da0f6}' (Speakers (Jabra Link 380))",
        "  'wasapi/{e8a70259-f4fd-4e03-a114-7d62b4270863}' (Speakers (Realtek(R) Audio))",
    ])
    assert match_audio_device(listing, "Speakers (Jabra Link 380)") == "wasapi/{56ab2f0c-0d20-4960-92c1-1e5d605da0f6}"
    assert match_audio_device(listing, "Speakers") == ""
    assert match_audio_device(listing, "") == ""


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
    path.write_text(json.dumps({"output": "  Cascos  "}), encoding="utf-8")
    assert Settings.load(path).output == "Cascos"
    path.write_text("{}", encoding="utf-8")
    assert Settings.load(path).output == ""


def test_play_wav_uses_the_chosen_speaker(tmp_path, monkeypatch):
    import sys
    import types
    import wave

    path = tmp_path / "tone.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 80)
    played = {}

    def play(audio, rate, device=None):
        played["rate"] = rate
        played["device"] = device
        played["frames"] = len(audio)

    def wait():
        played["waited"] = True

    def stop():
        played["stopped"] = True

    fake = types.ModuleType("sounddevice")
    fake.play = play
    fake.wait = wait
    fake.stop = stop
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    monkeypatch.setattr(
        "grok_assistant.listening.devices.listed_outputs",
        lambda: [{"index": 22, "name": "Cascos", "hostapi": 2}],
    )
    from grok_assistant.listening.devices import play_wav

    assert play_wav(str(path), "Cascos") is True
    assert played["device"] == 22
    assert played["rate"] == 8000
    assert played["waited"] is True
    played.clear()
    assert play_wav(str(path), "") is True
    assert "device" not in played or played.get("device") is None


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

        def read(self, frames):
            return [0.1] * frames, False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

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


def test_open_input_follows_the_microphone_rate_when_16k_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "grok_assistant.listening.devices.listed_inputs",
        lambda: [{"index": 25, "name": "Microphone Array (AMD Audio Device)", "hostapi": 3}],
    )
    opened = []

    class Stream:
        def __init__(self, **kwargs):
            opened.append(dict(kwargs))
            if kwargs["samplerate"] == 16000:
                raise RuntimeError("Error opening InputStream: Invalid sample rate [PaErrorCode -9997]")

        def read(self, frames):
            return [0.25] * frames, False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    import sys
    import types

    fake = types.ModuleType("sounddevice")
    fake.InputStream = Stream
    fake.query_devices = lambda index=None: {"default_samplerate": 48000.0}
    fake.default = types.SimpleNamespace(device=(25, 5))
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    from grok_assistant.listening.devices import open_input

    source = open_input("Microphone Array (AMD Audio Device)", 16000, latency=0.5)
    assert opened[0]["samplerate"] == 16000
    assert opened[1]["samplerate"] == 48000
    assert opened[1]["device"] == 25
    audio, overflow = source.read(1600)
    assert len(audio) == 1600
    assert overflow is False
    assert float(audio[0]) == 0.25


def test_a_silent_wasapi_microphone_opens_in_exclusive_mode(monkeypatch):
    monkeypatch.setattr(
        "grok_assistant.listening.devices.listed_inputs",
        lambda: [{"index": 25, "name": "Microphone Array (AMD Audio Device)", "hostapi": 3}],
    )
    opened = []

    class Settings:
        def __init__(self, exclusive=False):
            self.exclusive = exclusive

    class Stream:
        def __init__(self, **kwargs):
            opened.append(dict(kwargs))
            self.exclusive = bool(getattr(kwargs.get("extra_settings"), "exclusive", False))

        def read(self, frames):
            value = 0.2 if self.exclusive else 0.0
            return [value] * frames, False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    import sys
    import types

    info = {
        "name": "Microphone Array (AMD Audio Device)",
        "hostapi": 0,
        "max_input_channels": 2,
        "default_samplerate": 48000.0,
    }
    fake = types.ModuleType("sounddevice")
    fake.InputStream = Stream
    fake.WasapiSettings = Settings
    fake.query_devices = lambda index=None: info if index is not None else [info]
    fake.query_hostapis = lambda: [{"name": "Windows WASAPI"}]
    fake.default = types.SimpleNamespace(device=(25, 5))
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    from grok_assistant.listening.devices import open_input

    source = open_input("Microphone Array (AMD Audio Device)", 16000, latency=0.5)
    assert any(bool(getattr(row.get("extra_settings"), "exclusive", False)) for row in opened)
    audio, overflow = source.read(1600)
    assert len(audio) == 1600
    assert overflow is False
    assert abs(float(audio[0]) - 0.2) < 1e-6


def _wasapi_open(monkeypatch, read):
    """List the AMD array and record every InputStream. `read(stream, frames)` supplies samples."""
    monkeypatch.setattr(
        "grok_assistant.listening.devices.listed_inputs",
        lambda: [{"index": 25, "name": "Microphone Array (AMD Audio Device)", "hostapi": 0}],
    )
    opened = []

    class Settings:
        def __init__(self, exclusive=False):
            self.exclusive = exclusive

    class Stream:
        def __init__(self, **kwargs):
            opened.append(dict(kwargs))
            self.exclusive = bool(getattr(kwargs.get("extra_settings"), "exclusive", False))
            self.rate = int(kwargs["samplerate"])
            self.sent = 0

        def read(self, frames):
            return read(self, frames)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    import sys
    import types

    info = {
        "name": "Microphone Array (AMD Audio Device)",
        "hostapi": 0,
        "max_input_channels": 2,
        "default_samplerate": 48000.0,
    }
    fake = types.ModuleType("sounddevice")
    fake.InputStream = Stream
    fake.WasapiSettings = Settings
    fake.query_devices = lambda index=None: info if index is not None else [info]
    fake.query_hostapis = lambda: [{"name": "Windows WASAPI"}]
    fake.default = types.SimpleNamespace(device=(25, 5))
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    return opened


def test_exclusive_mode_wins_when_shared_capture_stays_near_zero(monkeypatch):
    def read(stream, frames):
        if not stream.exclusive:
            return [1e-7] * frames, False
        # Exclusive capture is silent for the first instant, then the room arrives.
        silent = int(stream.rate * 0.2)
        if stream.sent >= silent:
            return [0.002] * frames, False
        stream.sent += frames
        if stream.sent <= silent:
            return [0.0] * frames, False
        early = frames - (stream.sent - silent)
        return [0.0] * early + [0.002] * (frames - early), False

    opened = _wasapi_open(monkeypatch, read)
    from grok_assistant.listening.devices import open_input

    open_input("Microphone Array (AMD Audio Device)", 16000, latency=0.5)
    assert opened[-1]["samplerate"] == 48000
    assert opened[-1]["extra_settings"].exclusive is True


def test_a_live_shared_microphone_stays_shared(monkeypatch):
    def read(stream, frames):
        value = 0.0003 if stream.exclusive else 0.0002
        return [value] * frames, False

    opened = _wasapi_open(monkeypatch, read)
    from grok_assistant.listening.devices import open_input

    open_input("Microphone Array (AMD Audio Device)", 16000, latency=0.5)
    assert not bool(getattr(opened[-1].get("extra_settings"), "exclusive", False))


def test_a_silent_exclusive_mode_keeps_the_shared_microphone(monkeypatch):
    def read(stream, frames):
        return [0.0] * frames, False

    opened = _wasapi_open(monkeypatch, read)
    from grok_assistant.listening.devices import open_input

    open_input("Microphone Array (AMD Audio Device)", 16000, latency=0.5)
    assert not bool(getattr(opened[-1].get("extra_settings"), "exclusive", False))


def test_a_driver_that_cannot_be_read_does_not_drop_a_live_microphone(monkeypatch):
    monkeypatch.setattr(
        "grok_assistant.listening.devices.listed_inputs",
        lambda: [{"index": 0, "name": "Mic", "hostapi": 0}],
    )
    opened = []
    devices = [
        {"name": "Mic", "hostapi": 0, "max_input_channels": 1, "default_samplerate": 16000.0},
        {"name": "Mic", "hostapi": 1, "max_input_channels": 1, "default_samplerate": 16000.0},
    ]

    class Stream:
        def __init__(self, **kwargs):
            if kwargs.get("device") == 1:
                raise RuntimeError("Unanticipated host error [PaErrorCode -9999]")
            opened.append(dict(kwargs))

        def read(self, frames):
            return [0.0002] * frames, False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    import sys
    import types

    fake = types.ModuleType("sounddevice")
    fake.InputStream = Stream
    fake.query_devices = lambda index=None: devices[index] if index is not None else devices
    fake.query_hostapis = lambda: [{"name": "Windows WASAPI"}, {"name": "Windows WDM-KS"}]
    fake.default = types.SimpleNamespace(device=(0, 1))
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    from grok_assistant.listening.devices import open_input

    open_input("Mic", 16000)
    assert opened
    assert all(row.get("device") == 0 for row in opened)


def test_open_input_still_raises_when_the_microphone_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        "grok_assistant.listening.devices.listed_inputs",
        lambda: [{"index": 7, "name": "USB", "hostapi": 0}],
    )

    class Stream:
        def __init__(self, **kwargs):
            raise RuntimeError("device unavailable")

    import sys
    import types

    fake = types.ModuleType("sounddevice")
    fake.InputStream = Stream
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    from grok_assistant.listening.devices import open_input

    try:
        open_input("USB", 16000)
    except RuntimeError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("a missing microphone must still be reported")


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
    speakers = [
        {"index": 22, "name": "Speakers (Jabra Link 380)", "hostapi": 2},
        {"index": 23, "name": "Altavoces", "hostapi": 2},
    ]
    monkeypatch.setattr("grok_assistant.listening.devices.listed_outputs", lambda: speakers)
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
        assert "Altavoz" in labels
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
        ears = len(created)
        app._fill_output()
        speaker_choices = []
        for index in range(app.menu_output.index("end") + 1):
            try:
                speaker_choices.append(app.menu_output.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert speaker_choices[0].endswith("Predeterminado")
        assert "Altavoces" in speaker_choices
        assert "PC Speaker" not in " ".join(speaker_choices)
        app._pick_output("Altavoces")
        assert app.hub.brain.settings.output == "Altavoces"
        assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["output"] == "Altavoces"
        assert len(created) == ears
        app._pick_output("")
        assert app.hub.brain.settings.output == ""
        out_rows = app._output_rows()
        assert out_rows[0][2] == "out-default" and out_rows[0][3] is True
        activate("en")
        app._fill_settings()
        english = []
        for index in range(app.menu_settings.index("end") + 1):
            try:
                english.append(app.menu_settings.entrycget(index, "label"))
            except tk.TclError:
                continue
        assert "Microphone" in english
        assert "Speaker" in english
    finally:
        activate("es")
        root.destroy()
