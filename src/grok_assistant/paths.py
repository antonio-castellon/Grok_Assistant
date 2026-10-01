"""Where the program keeps its own notebook, away from the git checkout."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def bundle_root() -> Path:
    """Repo root in a checkout, or the unpacked folder inside the single executable."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


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


def exe_dir() -> Path:
    """Folder that holds GrokAssistant.exe. A source run uses dist/ next to the repo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2] / "dist"


def ensure_license(folder: Path | None = None, source: Path | None = None) -> Path | None:
    """Copy LICENSE.md beside the program when that copy is not there yet."""
    folder = exe_dir() if folder is None else folder
    source = bundle_root() / "LICENSE.md" if source is None else source
    target = folder / "LICENSE.md"
    if target.exists():
        return target
    if not source.is_file():
        return None
    try:
        folder.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    except OSError:
        return None
    return target


def speakers_file() -> Path:
    """Voice prints live beside the executable, so a rebuild does not wipe them."""
    folder = exe_dir() / "data"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "speakers.json"
    legacy = default_data_dir() / "speakers.json"
    if not path.exists() and legacy.exists():
        path.write_bytes(legacy.read_bytes())
    return path


def default_agents_dir() -> Path:
    return Path.home() / ".grok" / "agents"


def default_account_agents_dir() -> Path:
    """Agents the signed-in Grok client already stored for this account."""
    return Path.home() / ".grok" / "bundled" / "agents"
