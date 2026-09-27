from grok_assistant.hub import build
from grok_assistant.local_llm import parse_intent
from grok_assistant.marketplace import cpu_windows_zip, offers, progress_percent


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

    def converse(self, text, *, model, effort, session_id, first, agent_path, system=None):
        self.calls.append(("converse", text))
        return "Son las tres."


def test_the_app_is_version_0_1_0_and_still_a_candidate():
    from grok_assistant import __version__
    from grok_assistant.i18n import activate, code, text

    previous = code()
    try:
        assert __version__ == "0.1.0"
        for language in ("es", "en", "fr", "de"):
            activate(language)
            channel = text("about.channel")
            assert channel
            assert "0.1.0" not in channel
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
    from grok_assistant.marketplace import extra_piper_offers, offers_for

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

    import grok_assistant.marketplace as market

    original = market.piper_cached
    market.piper_cached = cached
    try:
        voices = [item for item in offers_for("fr") if item.kind == "voice"]
        assert any(item.id == "piper-fr_FR-gilles-low" for item in voices)
        assert {item.lang for item in voices} == {"fr"}
    finally:
        market.piper_cached = original


def test_voice_market_lists_only_the_selected_language():
    from grok_assistant.marketplace import offers_for
    from grok_assistant.speech import voice_lang

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
    assert engines == {"windows", "kroko", "whisper", "base", "canary"}
    assert offers()[0].kind == "stt"


def test_progress_percent_moves_as_soon_as_bytes_arrive():
    assert progress_percent(0, 0) == 0
    assert progress_percent(1, 491_000_000) == 1
    assert progress_percent(50, 200) == 25
    assert progress_percent(200, 200) == 100


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
    from grok_assistant.listen import preferred_recognizer

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
