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
