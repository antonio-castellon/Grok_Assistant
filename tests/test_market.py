from grok_assistant.rules.hub import build
from grok_assistant.mind.local_llm import parse_intent
from grok_assistant.house.marketplace import cpu_windows_zip, offers, progress_percent


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t

    def wall(self):
        return 1_700_000_000.0


class FakeCLI:
    def __init__(self):
        self.calls = []

    def classify(self, text, model):
        self.calls.append(("classify", text))
        return {"accion": "ignorar", "orden": "", "texto": ""}

    def converse(self, text, *, model, effort, session_id, first, agent_path, system=None, files=False):
        self.calls.append(("converse", text))
        return "Son las tres."


def test_the_footer_shows_the_release_numbers():
    from grok_assistant import __release__, __version__
    from grok_assistant.buildinfo import build_line
    from grok_assistant.i18n import activate, code
    from grok_assistant.ui.chrome import _version_line

    previous = code()
    try:
        assert __version__ == "1.0.3"
        assert __release__ == "v1.0.3-rc"
        line = f"v1.0.3-rc ({build_line()})"
        for language in ("es", "en", "fr", "de"):
            activate(language)
            assert _version_line() == line
    finally:
        activate(previous)


def test_language_packs_share_the_same_labels():
    import json
    from grok_assistant.i18n import bundled_dir

    packs = {
        path.stem: set(json.loads(path.read_text(encoding="utf-8"))["ui"])
        for path in bundled_dir().glob("*.json")
    }
    assert set(packs) >= {"es", "fr", "de", "en"}
    missing = {code: sorted(packs["es"] - keys) for code, keys in packs.items() if keys != packs["es"]}
    assert missing == {}


def test_extra_piper_voices_stay_in_the_selected_language():
    from grok_assistant.house.marketplace import extra_piper_offers, offers_for

    index = {
        "fr_FR-siwis-medium": {
            "name": "siwis",
            "language": {"family": "fr", "country_english": "France"},
            "quality": "medium",
            "num_speakers": 1,
            "files": {
                "fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx": {"size_bytes": 60_000_000},
                "fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json": {"size_bytes": 1000},
            },
        },
        "fr_FR-gilles-low": {
            "name": "gilles",
            "language": {"family": "fr", "country_english": "France"},
            "quality": "low",
            "num_speakers": 1,
            "files": {
                "fr/fr_FR/gilles/low/fr_FR-gilles-low.onnx": {"size_bytes": 63_000_000},
                "fr/fr_FR/gilles/low/fr_FR-gilles-low.onnx.json": {"size_bytes": 800},
            },
        },
        "en_US-libritts-high": {
            "name": "libritts",
            "language": {"family": "en", "country_english": "United States"},
            "quality": "high",
            "num_speakers": 904,
            "files": {
                "en/en_US/libritts/high/en_US-libritts-high.onnx": {"size_bytes": 100},
                "en/en_US/libritts/high/en_US-libritts-high.onnx.json": {"size_bytes": 10},
            },
        },
        "de_DE-thorsten-high": {
            "name": "thorsten",
            "language": {"family": "de", "country_english": "Germany"},
            "quality": "high",
            "num_speakers": 1,
            "files": {
                "de/de_DE/thorsten/high/de_DE-thorsten-high.onnx": {"size_bytes": 70_000_000},
                "de/de_DE/thorsten/high/de_DE-thorsten-high.onnx.json": {"size_bytes": 900},
            },
        },
    }
    french = extra_piper_offers("fr", index)
    assert [item.id for item in french] == ["piper-fr_FR-gilles-low"]
    assert french[0].use_label == "fr_FR gilles low"
    assert french[0].lang == "fr"
    assert french[0].size == "63 MB"
    german = extra_piper_offers("de", index)
    assert [item.title for item in german] == ["thorsten · Germany · high"]
    assert extra_piper_offers("en", index) == []

    def cached():
        return index

    import grok_assistant.house.marketplace as market

    original = market.piper_cached
    market.piper_cached = cached
    try:
        voices = [item for item in offers_for("fr") if item.kind == "voice"]
        assert any(item.id == "piper-fr_FR-gilles-low" for item in voices)
        assert {item.lang for item in voices} == {"fr"}
    finally:
        market.piper_cached = original


def test_voice_market_lists_only_the_selected_language():
    from grok_assistant.house.marketplace import offers_for
    from grok_assistant.speaking.speech import voice_lang

    spanish = [item for item in offers_for("es") if item.kind == "voice"]
    french = [item for item in offers_for("fr") if item.kind == "voice"]
    german = [item for item in offers_for("de") if item.kind == "voice"]
    english = [item for item in offers_for("en") if item.kind == "voice"]
    assert spanish and french and german and english
    assert {item.lang for item in spanish} == {"es"}
    assert {item.lang for item in french} == {"fr"}
    assert {item.lang for item in german} == {"de"}
    assert {item.lang for item in english} == {"en"}
    assert voice_lang("es_ES-davefx-medium") == "es"
    assert voice_lang("fr_FR-siwis-medium") == "fr"
    assert voice_lang("en-US") == "en"


def test_catalog_covers_voices_ears_and_the_local_model():
    kinds = {item.kind for item in offers()}
    assert kinds == {"voice", "stt", "llm"}
    assert "kroko" in {item.id for item in offers()}
    assert all(item.title and item.size and item.detail for item in offers())


def test_menu_ears_are_in_the_market():
    engines = {item.engine_id for item in offers() if item.kind == "stt"}
    assert engines == {"windows", "kroko", "zipfr", "zipen", "whisper", "base", "small", "canary", "cohere"}
    assert offers()[0].kind == "stt"


def test_new_ears_are_downloads_and_stay_in_their_language(tmp_path):
    import sys
    import types

    from grok_assistant.i18n import stt_language
    from grok_assistant.listening.kroko_ear import transcribe_clip
    from grok_assistant.listening.listen import EAR_LANG, ENGINE_DIRS, eligible_ears
    from grok_assistant.listening.offline_ear import OFFLINE_KINDS, OfflineEar
    from grok_assistant.listening import kroko_ear

    wanted = {
        "small": "sherpa-onnx-whisper-small.tar.bz2",
        "zipfr": "sherpa-onnx-streaming-zipformer-fr-2023-04-14.tar.bz2",
        "zipen": "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2",
        "cohere": "sherpa-onnx-cohere-transcribe-14-lang-int8-2026-04-01.tar.bz2",
    }
    rows = {item.engine_id: item for item in offers() if item.kind == "stt"}
    for engine, archive in wanted.items():
        item = rows[engine]
        assert item.files[0][0].endswith("/" + archive)
        assert item.files[0][1] == "models/" + archive
        assert ENGINE_DIRS[engine] == archive.removesuffix(".tar.bz2")
        assert item.ready(tmp_path) is False
    assert "small" in OFFLINE_KINDS and "cohere" in OFFLINE_KINDS
    assert kroko_ear.STREAMING_KINDS == ("kroko", "zipfr", "zipen")
    pool = ["teclado", "windows", "kroko", "whisper", "small", "cohere", "zipfr", "zipen"]
    assert eligible_ears(pool, "es") == ["windows", "kroko", "whisper", "small", "cohere"]
    assert eligible_ears(pool, "fr") == ["whisper", "small", "cohere", "zipfr"]
    assert eligible_ears(pool, "en") == ["whisper", "small", "cohere", "zipen"]
    assert eligible_ears(pool, "de") == ["whisper", "small", "cohere"]
    assert EAR_LANG["zipfr"] == "fr" and EAR_LANG["zipen"] == "en"

    seen = {}

    def missing(kind):
        seen["kind"] = kind
        return None

    original = kroko_ear.streaming_dir
    kroko_ear.streaming_dir = missing
    try:
        assert transcribe_clip(None, "zipen") == ""
    finally:
        kroko_ear.streaming_dir = original
    assert seen["kind"] == "zipen"

    folder = tmp_path / "model"
    folder.mkdir()
    (folder / "encoder.int8.onnx").write_bytes(b"e")
    (folder / "decoder.int8.onnx").write_bytes(b"d")
    (folder / "tokens.txt").write_text("a 1\n", encoding="utf-8")
    calls = {}

    class Rec:
        @staticmethod
        def from_whisper(**kwargs):
            calls["whisper"] = kwargs
            return "whisper"

        @staticmethod
        def from_cohere_transcribe(**kwargs):
            calls["cohere"] = kwargs
            return "cohere"

        @staticmethod
        def from_nemo_canary(**kwargs):
            calls["canary"] = kwargs
            return "canary"

    previous = sys.modules.get("sherpa_onnx")
    sys.modules["sherpa_onnx"] = types.SimpleNamespace(OfflineRecognizer=Rec)
    try:
        lang = stt_language()
        assert OfflineEar("small", lambda *_args: None)._recognizer(folder) == "whisper"
        assert calls["whisper"]["language"] == lang
        assert calls["whisper"]["task"] == "transcribe"
        assert OfflineEar("cohere", lambda *_args: None)._recognizer(folder) == "cohere"
        assert calls["cohere"]["language"] == lang
        assert calls["cohere"]["encoder"].endswith("encoder.int8.onnx")
        assert "canary" not in calls
    finally:
        if previous is None:
            sys.modules.pop("sherpa_onnx", None)
        else:
            sys.modules["sherpa_onnx"] = previous


def test_progress_percent_moves_as_soon_as_bytes_arrive():
    assert progress_percent(0, 0) == 0
    assert progress_percent(1, 491_000_000) == 1
    assert progress_percent(50, 200) == 25
    assert progress_percent(200, 200) == 100


class _Body:
    def __init__(self, data: bytes, status: int, headers: dict):
        self._data = data
        self.status = status
        self.headers = headers
        self._pos = 0

    def read(self, _size: int) -> bytes:
        chunk = self._data[self._pos:self._pos + _size]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> bool:
        return False

    def getcode(self) -> int:
        return self.status


def test_a_cut_download_keeps_the_partial_and_resumes(tmp_path, monkeypatch):
    from grok_assistant.house import marketplace

    dest = tmp_path / "models" / "piece.bin"
    dest.parent.mkdir(parents=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(b"abcd")
    ranges = []
    calls = {"n": 0}

    def fake_urlopen(request, timeout=0):
        assert timeout == 30
        asked = request.get_header("Range")
        ranges.append(asked)
        calls["n"] += 1
        if calls["n"] == 1:
            return _Body(b"ef", 206, {"Content-Length": "2", "Content-Range": "bytes 4-9/10"})
        return _Body(b"ghij", 206, {"Content-Length": "4", "Content-Range": "bytes 6-9/10"})

    monkeypatch.setattr(marketplace.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(marketplace.time, "sleep", lambda _delay: None)
    seen = []
    marketplace._fetch("https://example/piece.bin", dest, lambda got, total: seen.append((got, total)))
    assert dest.read_bytes() == b"abcdefghij"
    assert not part.exists()
    assert ranges == ["bytes=4-", "bytes=6-"]
    assert seen[0] == (4, 10)
    assert seen[-1] == (10, 10)


def test_a_failed_download_does_not_delete_what_already_arrived(tmp_path, monkeypatch):
    import urllib.error

    from grok_assistant.house import marketplace

    dest = tmp_path / "piece.bin"
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(b"12345")

    def fake_urlopen(_request, timeout=0):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(marketplace.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(marketplace.time, "sleep", lambda _delay: None)
    try:
        marketplace._fetch("https://example/piece.bin", dest)
    except urllib.error.URLError:
        pass
    else:
        raise AssertionError("expected the download to fail")
    assert part.read_bytes() == b"12345"
    assert not dest.exists()


def test_opening_an_archive_says_it_is_opening(tmp_path):
    import tarfile

    from grok_assistant.house.marketplace import _extract

    source = tmp_path / "tokens.txt"
    source.write_text("hola", encoding="utf-8")
    dest = tmp_path / "demo.tar.bz2"
    with tarfile.open(dest, "w:bz2") as packed:
        packed.add(source, arcname="demo/tokens.txt")
    notes = []
    _extract(dest, tmp_path / "out", notes.append, lambda value, caption="": notes.append(f"{value}:{caption}"))
    assert (tmp_path / "out" / "demo" / "tokens.txt").read_text(encoding="utf-8") == "hola"
    assert "abriendo el archivo" in " ".join(notes)


def test_a_closed_market_still_shows_the_download(tmp_path):
    import tkinter as tk

    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    root = tk.Tk()
    root.withdraw()
    try:
        app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
        app._downloads["small"] = {
            "percent": 75,
            "caption": "450 MB / 610 MB",
            "status": "descargando Whisper small…",
            "running": True,
            "done": False,
            "error": "",
        }
        app._build_market()
        root.update()
        app._market_win.destroy()
        app._build_market()
        root.update()
        row = app._download_rows["small"]
        assert row["percent"].get() == 75
        assert row["label"].get() == "450 MB / 610 MB"
        assert str(row["button"].cget("state")) == "disabled"
        assert row["bar"].winfo_manager()
        seen = []
        app.ui.put(lambda: (_ for _ in ()).throw(tk.TclError("ventana cerrada")))
        app.ui.put(lambda: seen.append("sigue"))
        app._pulse()
        assert seen == ["sigue"]
        app._closing = True
    finally:
        root.destroy()


def test_cpu_zip_is_not_taken_from_an_empty_latest_release():
    latest = [{"name": "nightly-tag.txt"}]
    builds = [
        {"name": "llama-b11216-bin-win-cuda-12.4-x64.zip"},
        {"name": "llama-b11216-bin-win-cpu-x64.zip", "browser_download_url": "https://example/cpu.zip"},
    ]
    assert cpu_windows_zip(latest) is None
    assert cpu_windows_zip(builds)["browser_download_url"] == "https://example/cpu.zip"


def test_local_models_only_sort_commands():
    names = [item.title for item in offers() if item.kind == "llm"]
    assert names == ["Qwen 0.5B", "SmolLM2 360M", "Llama 3.2 1B", "Qwen 1.5B"]


def test_a_partial_file_is_not_ready(tmp_path):
    item = next(offer for offer in offers() if offer.id == "kroko")
    dest = tmp_path / item.files[0][1]
    dest.parent.mkdir(parents=True)
    dest.with_name(dest.name + ".part").write_bytes(b"x" * 2000)
    assert item.ready(tmp_path) is False


def test_windows_spanish_is_an_installable_ear():
    item = next(item for item in offers() if item.id == "windows-es")
    assert item.local == "windows-speech"
    assert item.engine_id == "windows"


def test_keyboard_steps_aside_when_kroko_is_installed():
    from grok_assistant.listening.listen import preferred_recognizer

    assert preferred_recognizer("teclado", ["teclado", "kroko"]) == "kroko"
    assert preferred_recognizer("windows", ["teclado", "windows", "kroko"]) == "windows"
    assert preferred_recognizer("teclado", ["teclado"]) == "teclado"


def test_local_intent_parses_one_json_object():
    raw = 'listo {"accion": "comando", "orden": "subir volumen", "texto": ""}'
    assert parse_intent(raw)["orden"] == "subir volumen"
    assert parse_intent("no es json") is None


class Mind:
    def interpret(self, phrase, in_conversation):
        return {"accion": "comando", "orden": "subir volumen", "texto": ""}


def test_local_model_resolves_a_command_without_the_cloud(tmp_path):
    clock = Clock()
    cli = FakeCLI()
    hub = build(tmp_path / "data", tmp_path / "agents", cli, clock=clock, wall=clock.wall)
    hub.mind = Mind()
    result = hub.run("comando sube eso un poco")
    assert cli.calls == []
    assert any("Volumen" in line or "Has dicho" in line for line in result.spoken)
