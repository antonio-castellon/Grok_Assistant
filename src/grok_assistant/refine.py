"""A second reading of the same audio, so English names survive a Spanish ear."""

from __future__ import annotations

from grok_assistant.offline_ear import model_dir

# Whisper base keeps foreign names. Canary in Spanish mode translates them.
_ORDER = ("base", "whisper")
_LABELS = {"base": "Whisper base", "whisper": "Whisper pequeño"}


def choose_transcript(first: str, second: str) -> str:
    cleaned = (second or "").strip()
    if cleaned:
        return cleaned
    return (first or "").strip()


class Refiner:
    def __init__(self):
        self.kind = ""
        self._recognizer = None

    def label(self) -> str:
        return _LABELS.get(self.kind, "")

    def load(self) -> bool:
        if self._recognizer is not None:
            return True
        for kind in _ORDER:
            if model_dir(kind) is None:
                continue
            try:
                self._recognizer = self._build(kind)
            except (OSError, RuntimeError, ValueError, ImportError):
                continue
            self.kind = kind
            return True
        return False

    def transcribe(self, samples) -> str:
        if samples is None or not self.load():
            return ""
        try:
            import numpy as np
        except ImportError:
            return ""
        audio = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        if audio.size < 1600:
            return ""
        stream = self._recognizer.create_stream()
        stream.accept_waveform(16000, audio)
        self._recognizer.decode_stream(stream)
        return str(getattr(stream.result, "text", "") or "").strip()

    def _build(self, kind: str):
        import sherpa_onnx

        folder = model_dir(kind)
        encoder = _file(folder, "encoder")
        decoder = _file(folder, "decoder")
        tokens = _file(folder, "tokens")
        return sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(encoder),
            decoder=str(decoder),
            tokens=str(tokens),
            language="",
            task="transcribe",
            num_threads=4,
        )


def _file(folder, role: str):
    if role == "tokens":
        found = sorted(folder.glob("*tokens.txt"))
    else:
        found = sorted(folder.glob(f"*{role}*.onnx"))
        small = [path for path in found if "int8" in path.name]
        found = small or found
    if not found:
        raise FileNotFoundError(role)
    return found[0]
