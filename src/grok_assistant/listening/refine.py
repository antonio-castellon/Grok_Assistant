"""A second reading of the same audio, so English names survive a Spanish ear."""

from __future__ import annotations

from grok_assistant.listening.offline_ear import model_dir

# Whisper base keeps foreign names. Canary in Spanish mode translates them.
_ORDER = ("base", "whisper")
_LABELS = {"base": "Whisper base", "whisper": "Whisper pequeño"}


def pick_transcript(primary: str, second: str, testing: bool) -> str:
    """Test mode keeps the selected ear. Outside it, a second reading may replace it."""
    if testing:
        return (primary or "").strip()
    return choose_transcript(primary, second)


def choose_transcript(first: str, second: str) -> str:
    """Keep the selected engine unless the reread is the same sentence."""
    from grok_assistant.rules.match import noise_phrase, thin_phrase

    cleaned = (second or "").strip()
    primary = (first or "").strip()
    if not cleaned or noise_phrase(cleaned):
        return primary or cleaned
    if not primary:
        return cleaned
    # A one-token reread such as "1.0" must not erase a real sentence.
    if thin_phrase(cleaned) and not thin_phrase(primary):
        return primary
    if _same_utterance(primary, cleaned):
        return cleaned
    return primary


_STOP = {
    "a", "al", "de", "del", "el", "la", "las", "lo", "los", "un", "una",
    "y", "o", "u", "en", "con", "por", "para", "que", "se", "me", "te", "es",
    "the", "of", "and", "to", "mi", "tu",
}


def _same_utterance(primary: str, second: str) -> bool:
    """True when the reread still says the selected engine's sentence."""
    from grok_assistant.rules.match import words_norm

    first = [word for word in words_norm(primary) if word not in _STOP and len(word) > 1]
    other = {word for word in words_norm(second) if word not in _STOP and len(word) > 1}
    if not first or not other:
        return False
    covered = [word for word in first if _covered(word, other)]
    if any(len(word) > 4 for word in first if word not in covered):
        return False
    if len(first) == 1:
        return bool(covered)
    return len(covered) >= 2 and len(covered) * 2 >= len(first)


def _covered(word: str, other: set[str]) -> bool:
    if word in other:
        return True
    if len(word) < 3:
        return False
    return any(word in token or token in word for token in other if len(token) >= 3)


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
