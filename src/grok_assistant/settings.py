"""App settings. The administrator password is not one of them."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Settings:
    model: str = "grok-4.7"
    hello_index: int = 0
    wait_index: int = 0
    extra_index: int = 0
    voice_index: int = 0
    recognizer: str = "teclado"
    volume: int = 70

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
        return item

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
