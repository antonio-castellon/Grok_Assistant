"""Local mouths. Spanish when the machine has a Spanish voice, and never a cloud voice."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from grok_assistant.paths import bundle_root
from grok_assistant.quiet import no_window


class Speaker:
    def list_voices(self) -> list[str]:
        if os.name == "nt":
            return _windows_voices()
        return _linux_voices()

    def say(self, text: str, voice: str | None, volume: int) -> bool:
        text = (text or "").strip()
        if not text:
            return True
        volume = max(0, min(100, int(volume)))
        if os.name == "nt":
            return _windows_say(text, voice, volume)
        return _linux_say(text, voice, volume)


def _windows_voices() -> list[str]:
    script = bundle_root() / "scripts" / "voices.ps1"
    if not script.exists():
        return []
    try:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            **no_window(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    spanish = []
    others = []
    for line in (done.stdout or "").splitlines():
        if "|" not in line:
            continue
        name, culture = line.split("|", 1)
        name = name.strip()
        if not name:
            continue
        if culture.lower().startswith("es"):
            spanish.append(name)
        else:
            others.append(name)
    return spanish + others


def _windows_say(text: str, voice: str | None, volume: int) -> bool:
    script = bundle_root() / "scripts" / "speak.ps1"
    if not script.exists():
        return False
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False)
    try:
        handle.write(text)
        handle.close()
        done = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(script), handle.name, str(volume), voice or ""],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **no_window(),
        )
        return done.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        try:
            os.remove(handle.name)
        except OSError:
            pass


def _linux_voices() -> list[str]:
    if shutil.which("espeak-ng"):
        return ["es", "es-la", "es+m3", "es+f3", "es+m1"]
    if shutil.which("espeak"):
        return ["es", "es-la"]
    return []


def _linux_say(text: str, voice: str | None, volume: int) -> bool:
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        return False
    amplitude = str(max(0, min(200, volume * 2)))
    try:
        done = subprocess.run(
            [binary, "-v", voice or "es", "-a", amplitude, text],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **no_window(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0
