"""Where the program keeps its own notebook, away from the git checkout."""

from __future__ import annotations

import os
from pathlib import Path


def lines_dir() -> Path:
    return Path(__file__).resolve().parent / "lines"


def load_lines(name: str) -> list[str]:
    path = lines_dir() / name
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def default_data_dir() -> Path:
    if os.name == "nt":
        root = os.environ.get("APPDATA") or str(Path.home())
        return Path(root) / "GrokAssistant"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "grok-assistant"
    return Path.home() / ".config" / "grok-assistant"


def default_agents_dir() -> Path:
    return Path.home() / ".grok" / "agents"
