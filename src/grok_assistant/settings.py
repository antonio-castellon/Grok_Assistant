"""App settings. The administrator password is not one of them."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from grok_assistant.banter import KINDS, THEMES, normalize_choice
from grok_assistant.personality import blank_personality, normalize_personality


@dataclass
class Settings:
    model: str = "grok-4.7"
    hello_index: int = 0
    wait_index: int = 0
    extra_index: int = 0
    voice_index: int = 0
    recognizer: str = "teclado"
    volume: int = 70
    local_llm: bool = True
    llm_file: str = ""
    wake_name: str = "grok"
    wake_heard: list = field(default_factory=list)
    language: str = "es"
    personality: dict = field(default_factory=blank_personality)
    line_kinds: list = field(default_factory=lambda: list(KINDS))
    line_themes: list = field(default_factory=lambda: list(THEMES))

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        known = {key: raw[key] for key in asdict(cls()) if key in raw}
        item = cls(**known)
        item.volume = max(0, min(100, int(item.volume)))
        item.hello_index = max(0, int(item.hello_index))
        item.wait_index = max(0, int(item.wait_index))
        item.extra_index = max(0, int(item.extra_index))
        item.voice_index = max(0, int(item.voice_index))
        item.wake_name = str(item.wake_name or "grok").strip() or "grok"
        if not isinstance(item.wake_heard, list):
            item.wake_heard = []
        item.personality = normalize_personality(item.personality)
        item.language = str(item.language or "es").strip().lower() or "es"
        item.line_kinds = normalize_choice(item.line_kinds, KINDS)
        item.line_themes = normalize_choice(item.line_themes, THEMES)
        return item

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
