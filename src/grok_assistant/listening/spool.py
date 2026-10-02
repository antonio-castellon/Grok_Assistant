"""A temporary 16 kHz wav of the phrase being heard.

The microphone writes here while the recognizer reads the same samples.
Guardar traza can pick the file up later. Nothing here is uploaded.
"""

from __future__ import annotations

import time
import wave
from pathlib import Path

_KEEP = 30


class PhraseTape:
    def __init__(self, folder: Path | None = None):
        self._folder = folder
        self.path: Path | None = None
        self.frames = 0
        self._handle: wave.Wave_write | None = None

    def write(self, samples) -> None:
        import numpy as np

        audio = np.clip(np.ascontiguousarray(samples, dtype=np.float32).reshape(-1), -1.0, 1.0)
        if audio.size == 0:
            return
        pcm = (audio * 32767.0).astype("<i2")
        try:
            handle = self._open()
            handle.writeframes(pcm.tobytes())
            self.frames += int(pcm.size)
            patch = getattr(handle, "_patchheader", None)
            if patch is not None:
                patch()
        except (OSError, AttributeError):
            return

    def finish(self, keep: bool) -> Path | None:
        path = self.path
        handle = self._handle
        self._handle = None
        self.path = None
        frames = self.frames
        self.frames = 0
        if handle is not None:
            try:
                handle.close()
            except OSError:
                keep = False
        if path is None:
            return None
        if not keep or frames < 1600:
            try:
                path.unlink()
            except OSError:
                pass
            return None
        self._prune(path.parent)
        return path

    def _open(self) -> wave.Wave_write:
        if self._handle is not None:
            return self._handle
        folder = self._folder
        if folder is None:
            from grok_assistant.paths import default_data_dir

            folder = default_data_dir() / "live"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        suffix = f"{time.time_ns() % 1_000_000:06d}"
        path = folder / f"frase-{stamp}-{suffix}.wav"
        handle = wave.open(str(path), "wb")
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        self.path = path
        self._handle = handle
        return handle

    def _prune(self, folder: Path) -> None:
        files = sorted(folder.glob("frase-*.wav"), key=lambda item: item.stat().st_mtime)
        for old in files[:-_KEEP]:
            try:
                old.unlink()
            except OSError:
                continue
