"""Conversation rules. A phrase leaves the machine only inside a Job."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from grok_assistant.notebook.auth import AdminAuth
from grok_assistant.listening.enroll_audio import PHRASES, enroll_phrases, one_voice
from grok_assistant.house.helptext import SCREEN_HELP, spoken_help
from grok_assistant.i18n import say, text
from grok_assistant.rules.match import (
    Hit,
    Song,
    canonicalize,
    closer,
    display_order,
    blank_phrase,
    is_presence,
    noise_phrase,
    is_test_word,
    thin_phrase,
    is_wake,
    is_yes,
    parse_order,
    song_of,
    strip_comando,
    tokenize,
    wake_is_presence,
)
from grok_assistant.notebook.store import SHARED, AgentBook, SessionStore, SpeakerBook

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_COMANDO = re.compile(r"^\s*COMANDO:\s*(.+?)\s*$", re.IGNORECASE)


def _ear_label(kind: str) -> str:
    from grok_assistant.listening.listen import RECOGNIZER_LABELS

    return RECOGNIZER_LABELS.get(kind, kind)


def _blank_enroll() -> dict:
    return {
        "stage": "name",
        "target": None,
        "spoken": "",
        "take": 0,
        "vectors": [],
        "clips": [],
        "misses": 0,
    }


@dataclass
class Job:
    kind: str
    text: str
    effort: str = "low"
    agent_name: str | None = None
    agent_path: str | None = None
    slot: str = "session"


@dataclass
class Turn:
    speak: list[str] = field(default_factory=list)
    effects: list[tuple] = field(default_factory=list)
    job: Job | None = None
    status: str | None = None


def split_commands(answer: str) -> tuple[list[str], str]:
    commands: list[str] = []
    kept: list[str] = []
    for line in (answer or "").splitlines() or [""]:
        matched = _COMANDO.match(line)
        if matched:
            commands.append(matched.group(1).strip())
        else:
            kept.append(line)
    return commands, "\n".join(kept).strip()


def for_speech(text: str) -> str:
    text = _ANSI.sub("", text or "")
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip().replace("**", "").replace("`", "")
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        if stripped.startswith(("- ", "* ")):
            stripped = stripped[2:].strip()
        if stripped:
            lines.append(stripped)
    return " ".join(lines).strip()


__all__ = [name for name in globals() if not name.startswith("__")]
