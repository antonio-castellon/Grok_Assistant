from grok_assistant.hub import build
from grok_assistant.local_llm import parse_intent
from grok_assistant.marketplace import offers


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

    def converse(self, text, *, model, effort, session_id, first, agent_path):
        self.calls.append(("converse", text))
        return "Son las tres."


def test_catalog_covers_voices_ears_and_the_local_model():
    kinds = {item.kind for item in offers()}
    assert kinds == {"voice", "stt", "llm"}
    assert "kroko" in {item.id for item in offers()}
    assert all(item.title and item.size and item.detail for item in offers())


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
    hub.run("hola grok")
    result = hub.run("sube eso un poco")
    assert cli.calls == []
    assert any("Volumen" in line or "Has dicho" in line for line in result.spoken)
