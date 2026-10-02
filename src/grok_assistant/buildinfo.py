"""The build baked into this copy. About shows it. The updater compares it."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _git(cwd: Path, *args: str) -> str:
    try:
        from grok_assistant.quiet import no_window

        out = subprocess.check_output(
            ["git", *args],
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stderr=subprocess.DEVNULL,
            timeout=5,
            **no_window(),
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.strip()


def _read_file(path: Path) -> tuple[str, str]:
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return "", ""
    ident = lines[0] if lines else ""
    when = lines[1] if len(lines) > 1 else ""
    if not ident or ident == "unknown":
        return "", when
    return ident, when


def read_stamp() -> tuple[str, str]:
    """Return the build id and the UTC time it was made. Empty strings when unknown."""
    if getattr(sys, "frozen", False):
        return _read_file(Path(getattr(sys, "_MEIPASS")) / "grok_assistant" / "build_stamp.txt")
    here = Path(__file__).resolve()
    checkout = here.parents[2]
    if (checkout / "scripts" / "speak.ps1").is_file():
        ident = _git(checkout, "rev-parse", "--short=12", "HEAD")
        if ident:
            return ident, _git(checkout, "log", "-1", "--format=%cI")
    return _read_file(here.parent / "build_stamp.txt")


def build_line() -> str:
    ident, _when = read_stamp()
    if not ident:
        return "build —"
    return f"build {ident}"


def write_stamp(path: Path | None = None) -> tuple[str, str]:
    """Write the source commit and the current UTC time. The executable and the wheel both call this."""
    dest = Path(path) if path else Path(__file__).resolve().parent / "build_stamp.txt"
    checkout = Path(__file__).resolve().parents[2]
    ident = _git(checkout, "rev-parse", "--short=12", "HEAD")
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dest.write_text(f"{ident}\n{when}\n", encoding="utf-8")
    return ident, when
