"""The cloud command is built so a phrase cannot wander into the coding tools."""

import json
from pathlib import Path

from grok_assistant.grok_cli import GrokCLI


class Capture(GrokCLI):
    def __init__(self, cwd: Path):
        super().__init__("grok", cwd)
        self.command: list[str] = []
        self.timeout = 0

    def _run(self, command, timeout):
        self.command = command
        self.timeout = timeout
        if "--json-schema" in command:
            return json.dumps({"text": json.dumps({"accion": "comando", "orden": "subir volumen", "texto": ""})})
        return "Son las tres."


def test_classify_is_one_turn_without_search_or_the_dev_tree(tmp_path):
    cli = Capture(tmp_path)
    data = cli.classify("sube el volumen", "grok-4.7")
    assert data["accion"] == "comando"
    assert "--disable-web-search" in cli.command
    assert "--max-turns" in cli.command
    assert cli.command[cli.command.index("--max-turns") + 1] == "1"
    assert "--no-subagents" in cli.command
    assert "--cwd" in cli.command
    assert cli.command[cli.command.index("--cwd") + 1] == str(tmp_path)
    assert "web_search" not in cli.command


def test_cloud_text_is_read_as_utf8(tmp_path, monkeypatch):
    seen = {}

    class Done:
        returncode = 0
        stdout = "mañana, mínima y máxima"
        stderr = ""

    def fake_run(_command, **kwargs):
        seen.update(kwargs)
        return Done()

    monkeypatch.setattr("grok_assistant.grok_cli.subprocess.run", fake_run)
    assert GrokCLI("grok", tmp_path)._run(["grok"], 5) == "mañana, mínima y máxima"
    assert seen["encoding"] == "utf-8"
    assert seen["errors"] == "replace"


def test_converse_can_search_and_cannot_inherit_this_checkout(tmp_path):
    cli = Capture(tmp_path)
    cli.converse(
        "qué hora es",
        model="grok-4.7",
        effort="low",
        session_id="11111111-1111-1111-1111-111111111111",
        first=True,
        agent_path=None,
    )
    assert "--tools" in cli.command
    tools = cli.command[cli.command.index("--tools") + 1]
    assert tools == "web_search,web_fetch"
    assert "--disable-web-search" not in cli.command
    assert "--no-subagents" in cli.command
    assert cli.command[cli.command.index("--cwd") + 1] == str(tmp_path)
    assert "--session-id" in cli.command
    assert "--system-prompt-override" in cli.command


def test_converse_sends_the_personality_with_the_answer(tmp_path):
    from grok_assistant.personality import load_person, voice_prompt
    from grok_assistant.prompts import VOICE_SYSTEM

    cli = Capture(tmp_path)
    cfg = load_person("marcos")
    cfg["behavior"] = "Pregunta si hace falta Kubernetes."
    cli.converse(
        "qué hora es",
        model="grok-4.7",
        effort="low",
        session_id="11111111-1111-1111-1111-111111111111",
        first=True,
        agent_path=None,
        system=voice_prompt(cfg, VOICE_SYSTEM),
    )
    override = cli.command[cli.command.index("--system-prompt-override") + 1]
    assert "Persona: Marcos" in override
    assert "Pregunta si hace falta Kubernetes." in override
    assert "una o dos frases" in override
