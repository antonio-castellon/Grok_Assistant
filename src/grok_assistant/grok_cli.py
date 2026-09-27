"""The only door to the cloud: a finished phrase, already allowed by the rules."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from grok_assistant.prompts import AGENT_RULES, CLASSIFY_SYSTEM, VOICE_SYSTEM

CLASSIFY_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "accion": {"type": "string", "enum": ["comando", "ignorar"]},
        "orden": {"type": "string"},
        "texto": {"type": "string"},
    },
    "required": ["accion", "orden", "texto"],
    "additionalProperties": False,
}, ensure_ascii=False)


class GrokError(RuntimeError):
    pass


class GrokCLI:
    def __init__(self, binary: str, cwd: Path):
        self.binary = binary
        self.cwd = cwd

    @staticmethod
    def find() -> str | None:
        found = shutil.which("grok") or shutil.which("grok.exe")
        if found:
            return found
        name = "grok.exe" if os.name == "nt" else "grok"
        home = Path.home() / ".grok" / "bin" / name
        if home.exists():
            return str(home)
        return None

    def classify(self, text: str, model: str) -> dict:
        command = [
            self.binary, "-p", text,
            "--verbatim",
            "--model", model,
            "--reasoning-effort", "low",
            "--output-format", "json",
            "--json-schema", CLASSIFY_SCHEMA,
            "--system-prompt-override", CLASSIFY_SYSTEM,
            "--disable-web-search",
            "--max-turns", "1",
            "--no-subagents",
            "--cwd", str(self.cwd),
        ]
        raw = self._run(command, 60)
        return _parse_classify(raw)

    def converse(self, text: str, *, model: str, effort: str, session_id: str, first: bool, agent_path: str | None) -> str:
        command = [
            self.binary, "-p", text,
            "--verbatim",
            "--model", model,
            "--reasoning-effort", effort,
            "--output-format", "plain",
            "--max-turns", "4",
            "--no-subagents",
            "--tools", "web_search,web_fetch",
            "--always-approve",
            "--cwd", str(self.cwd),
        ]
        if agent_path:
            command += ["--agent", agent_path, "--rules", AGENT_RULES]
        else:
            command += ["--system-prompt-override", VOICE_SYSTEM]
        command += ["--session-id", session_id] if first else ["--resume", session_id]
        return self._run(command, 120).strip()

    def models(self) -> list[str]:
        command = [self.binary, "models"]
        try:
            raw = self._run(command, 30)
        except GrokError:
            return []
        found = []
        for line in raw.splitlines():
            piece = line.strip().lstrip("*").lstrip("-").strip()
            if piece.startswith("grok-"):
                name = piece.split()[0]
                if name not in found:
                    found.append(name)
        return found

    def _run(self, command: list[str], timeout: int) -> str:
        try:
            done = subprocess.run(
                command,
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GrokError("tiempo agotado") from exc
        except OSError as exc:
            raise GrokError("no encuentro el comando grok") from exc
        if done.returncode != 0:
            detail = (done.stderr or done.stdout or "").strip().splitlines()
            tail = detail[-1] if detail else f"salida {done.returncode}"
            raise GrokError(tail[:180])
        return done.stdout or ""


def interpret_models(stdout: str, stderr: str, code: int) -> str:
    """ready, signed_out, or broken. Does not look at credential files."""
    text = f"{stdout}\n{stderr}".lower()
    if code == 0 and ("logged in" in text or "available models" in text or "grok-" in text):
        return "ready"
    if "sign in" in text or "not logged" in text or "login" in text:
        return "signed_out"
    if code != 0:
        return "broken"
    return "signed_out"


def _parse_classify(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        raise GrokError("clasificador vacío")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise GrokError("clasificador ilegible")
        data = json.loads(raw[start:end + 1])
    if isinstance(data, dict) and "accion" in data:
        return data
    if isinstance(data, dict) and isinstance(data.get("text"), str):
        return _parse_classify(data["text"])
    raise GrokError("clasificador ilegible")
