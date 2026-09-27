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
