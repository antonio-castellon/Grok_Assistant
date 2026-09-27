"""Local ears. Audio is not a network protocol."""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

from grok_assistant.paths import bundle_root
from grok_assistant.quiet import no_window


def dictation_script() -> Path:
    return bundle_root() / "listeners" / "dictation.ps1"


ENGINE_DIRS = {
    "kroko": "sherpa-onnx-streaming-zipformer-es-kroko-2025-08-06",
    "whisper": "sherpa-onnx-whisper-tiny",
    "base": "sherpa-onnx-whisper-base",
    "canary": "sherpa-onnx-nemo-canary-180m-flash-en-es-de-fr-int8",
}

RECOGNIZER_LABELS = {
    "teclado": "Teclado",
    "windows": "Windows español",
    "kroko": "Kroko",
    "whisper": "Whisper pequeño",
    "base": "Whisper base",
    "canary": "Canary",
}


def discover_recognizers() -> list[str]:
    """Engines that exist on this machine. The keyboard is always one of them."""
    found = ["teclado"]
    if windows_spanish_available():
        found.append("windows")
    roots = [
        bundle_root() / "models",
        Path.home() / ".grok" / "assistant-models",
    ]
    seen = set(found)
    for root in roots:
        for key, folder in ENGINE_DIRS.items():
            if key not in seen and (root / folder).is_dir():
                found.append(key)
                seen.add(key)
    return found


def windows_spanish_available() -> bool:
    script = dictation_script()
    if os.name != "nt" or not script.exists():
        return False
    try:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(script), "-Probe"],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
            **no_window(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "READY" in (done.stdout or "")


class Dictation:
    """Windows Spanish dictation, stopped by a pause file while the assistant speaks."""

    def __init__(self, on_line, pause_file: Path):
        self.on_line = on_line
        self.pause_file = pause_file
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if self._proc is not None or os.name != "nt":
            return False
        try:
            self._proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-File", str(dictation_script()), "-PauseFile", str(self.pause_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                **no_window(),
            )
        except OSError:
            self._proc = None
            return False
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()
        return True

    def set_paused(self, paused: bool) -> None:
        if paused:
            self.pause_file.parent.mkdir(parents=True, exist_ok=True)
            self.pause_file.write_text("1", encoding="utf-8")
        elif self.pause_file.exists():
            try:
                self.pause_file.unlink()
            except OSError:
                pass

    def stop(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is not None and proc.poll() is None:
            proc.terminate()

    def _read(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            text = line.strip()
            if text.startswith("LINE:"):
                heard = text[5:].strip()
                if heard:
                    self.on_line(heard)
