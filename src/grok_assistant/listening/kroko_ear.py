"""Streaming Zipformer ears. Kroko is the Spanish one. Audio stays in this process."""

from __future__ import annotations

import threading
from pathlib import Path

from grok_assistant.listening.listen import ENGINE_DIRS, RECOGNIZER_LABELS
from grok_assistant.paths import bundle_root, default_data_dir

STREAMING_KINDS = ("kroko", "zipfr", "zipen")


def streaming_dir(kind: str) -> Path | None:
    name = ENGINE_DIRS.get(kind)
    if not name:
        return None
    for root in (default_data_dir() / "models", bundle_root() / "models"):
        folder = root / name
        if folder.is_dir() and (folder / "tokens.txt").exists():
            return folder
    return None


def kroko_dir() -> Path | None:
    return streaming_dir("kroko")


def note_capture_speech(mark: str, heard: str, quiet: float, voiced: float) -> tuple[str, float, float]:
    """A new decoded word restarts the pause. The word is not matched to the phrase."""
    from grok_assistant.listening.enroll_audio import TAKE_MIN_VOICE

    heard = " ".join((heard or "").split())
    if heard and heard != mark:
        return heard, 0.0, max(voiced, TAKE_MIN_VOICE)
    return mark, quiet, voiced


def capture_has_sound(text: str, voiced: float) -> bool:
    """True when a timed-out take already caught sound worth keeping."""
    return bool(" ".join((text or "").split())) or voiced > 0


def _model(folder: Path, prefix: str) -> Path | None:
    files = list(folder.glob(f"{prefix}*.onnx"))
    if not files:
        return None
    int8 = [path for path in files if "int8" in path.name]
    return sorted(int8 or files)[0]


_clip_recognizers: dict = {}


def _label(kind: str) -> str:
    return RECOGNIZER_LABELS.get(kind, kind)


def transcribe_clip(samples, kind: str = "kroko") -> str:
    """Read one saved phrase. The live microphone is not involved."""
    try:
        import numpy as np
        import sherpa_onnx
    except ImportError:
        return ""
    folder = streaming_dir(kind)
    if folder is None or samples is None:
        return ""
    try:
        recognizer = _clip_recognizers.get(kind)
        if recognizer is None:
            encoder = _model(folder, "encoder")
            decoder = _model(folder, "decoder")
            joiner = _model(folder, "joiner")
            tokens = folder / "tokens.txt"
            if not all([encoder, decoder, joiner, tokens.exists()]):
                return ""
            recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=str(tokens),
                encoder=str(encoder),
                decoder=str(decoder),
                joiner=str(joiner),
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                enable_endpoint_detection=False,
            )
            _clip_recognizers[kind] = recognizer
        audio = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        if audio.size < 1600:
            return ""
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, audio)
        stream.accept_waveform(16000, np.zeros(int(16000 * 0.8), dtype=np.float32))
        stream.input_finished()
        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)
        result = recognizer.get_result(stream)
        text = result if isinstance(result, str) else getattr(result, "text", "")
        return str(text or "").strip()
    except (OSError, RuntimeError, ValueError, TypeError):
        return ""


class KrokoEar:
    def __init__(self, on_line, on_status=None, wake_name=None, kind: str = "kroko", on_partial=None, talk_mode=None):
        self.kind = kind if kind in STREAMING_KINDS else "kroko"
        self.on_line = on_line
        self.on_partial = on_partial or (lambda *_ignored: None)
        self.on_status = on_status or (lambda _text: None)
        self._wake_name = wake_name or (lambda: "grok")
        self._talk_mode = talk_mode or (lambda: "seguida")
        self.error = ""
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._capture = threading.Event()
        self._thread: threading.Thread | None = None
        self._partial_seq = 0
        self._last_partial = ""
        self._capture_mark = ""
        self._flush = threading.Event()
        self._hold = False

    def start(self) -> bool:
        folder = streaming_dir(self.kind)
        if folder is None:
            self.error = f"el modelo {_label(self.kind)} no está en el disco"
            return False
        try:
            import sherpa_onnx  # noqa: F401
            import sounddevice  # noqa: F401
        except ImportError:
            self.error = "falta el motor sherpa o el micrófono (sounddevice)"
            return False
        self._thread = threading.Thread(target=self._loop, args=(folder,), daemon=True)
        self._thread.start()
        return True

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def set_capture(self, capture: bool) -> None:
        """A voice-print take waits longer than a normal phrase."""
        if capture:
            self._capture.set()
        else:
            self._capture.clear()

    def set_hold(self, hold: bool) -> None:
        """While the print window is open, Seguir keeps the phrase and Reintentar clears it."""
        self._hold = bool(hold)

    def request_flush(self) -> None:
        """Hand back the open take when the wait runs out, words included."""
        self._flush.set()

    def stop(self) -> None:
        self._stop.set()

    def _ready(self, text: str, quiet: float, endpoint: bool) -> bool:
        from grok_assistant.rules.match import endpoint_quiet

        if not text:
            return False
        try:
            name = self._wake_name() or "grok"
        except Exception:
            name = "grok"
        try:
            mode = self._talk_mode() or "seguida"
        except Exception:
            mode = "seguida"
        limit = endpoint_quiet(text, name, mode)
        # «Primero el saludo» keeps a bare hello open for two seconds.
        # The other ways close at 0.7 s, or at the model's own endpoint.
        if quiet >= limit - 0.051:
            return True
        return bool(endpoint) and limit <= 0.7

    def _capture_ready(self, text: str, quiet: float, voiced: float) -> bool:
        """End the take on sound plus a pause. The words are not checked."""
        from grok_assistant.listening.enroll_audio import TAKE_MAX_VOICE, TAKE_MIN_VOICE, TAKE_QUIET

        if voiced >= TAKE_MAX_VOICE:
            return True
        if self._hold:
            return False
        if quiet < TAKE_QUIET:
            return False
        if voiced >= TAKE_MIN_VOICE:
            return True
        return bool(" ".join((text or "").split()))

    def _report(self, text: str) -> None:
        self.on_status(text)
        try:
            path = default_data_dir() / "ear.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except OSError:
            return

    def _loop(self, folder: Path) -> None:
        import numpy as np
        import sherpa_onnx
        import sounddevice as sd

        try:
            encoder = _model(folder, "encoder")
            decoder = _model(folder, "decoder")
            joiner = _model(folder, "joiner")
            tokens = folder / "tokens.txt"
            if not all([encoder, decoder, joiner, tokens.exists()]):
                self.error = f"al modelo {_label(self.kind)} le faltan archivos"
                self._report(self.error)
                return
            recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=str(tokens),
                encoder=str(encoder),
                decoder=str(decoder),
                joiner=str(joiner),
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                enable_endpoint_detection=True,
                # After the person stops, the phrase has to be ready in under two seconds.
                rule1_min_trailing_silence=1.0,
                rule2_min_trailing_silence=0.6,
                rule3_min_utterance_length=20,
            )
            stream = recognizer.create_stream()
            rate = 16000
            block = int(0.1 * rate)
            source = sd.InputStream(channels=1, dtype="float32", samplerate=rate)
        except Exception as exc:
            self.error = f"{_label(self.kind)} no arrancó: {exc}"
            self._report(self.error)
            return
        self._report(f"{_label(self.kind)} está escuchando el micrófono")
        try:
            with source:
                quiet = 0.0
                voiced = 0.0
                heard_audio: list = []
                parts: list[str] = []
                while not self._stop.is_set():
                    samples, _overflow = source.read(block)
                    if self._paused.is_set():
                        recognizer.reset(stream)
                        quiet = 0.0
                        voiced = 0.0
                        heard_audio.clear()
                        parts.clear()
                        self._last_partial = ""
                        self._capture_mark = ""
                        self._flush.clear()
                        continue
                    chunk = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
                    heard_audio.append(chunk)
                    stream.accept_waveform(rate, chunk)
                    while recognizer.is_ready(stream):
                        recognizer.decode_stream(stream)
                    result = recognizer.get_result(stream)
                    segment = result if isinstance(result, str) else getattr(result, "text", "")
                    segment = str(segment).strip()
                    capturing = self._capture.is_set()
                    if not capturing:
                        self._capture_mark = ""
                    loud = float(np.sqrt(np.mean(np.square(chunk)))) > (0.004 if capturing else 0.01)
                    quiet = 0.0 if loud else quiet + 0.1
                    if loud:
                        voiced += 0.1
                    # The model marks a pause at about 0.6 s. During a take that pause
                    # is only a breath: keep the audio and join the next words.
                    if capturing and recognizer.is_endpoint(stream):
                        if segment:
                            parts.append(segment)
                        recognizer.reset(stream)
                        segment = ""
                    heard = " ".join(part for part in [*parts, segment] if part) if capturing else segment
                    if capturing:
                        self._capture_mark, quiet, voiced = note_capture_speech(
                            self._capture_mark, heard, quiet, voiced
                        )
                    ready = (
                        self._capture_ready(heard, quiet, voiced)
                        if capturing
                        else self._ready(segment, quiet, recognizer.is_endpoint(stream))
                    )
                    flushing = self._flush.is_set()
                    if flushing:
                        self._flush.clear()
                    keep = flushing and capturing and capture_has_sound(heard, voiced)
                    if heard and heard != self._last_partial and not ready and not keep:
                        self._partial_seq += 1
                        self._last_partial = heard
                        self.on_partial(heard, self._partial_seq)
                    if ready or keep:
                        recognizer.reset(stream)
                        quiet = 0.0
                        voiced = 0.0
                        audio = np.concatenate(heard_audio) if heard_audio else None
                        heard_audio.clear()
                        parts.clear()
                        self._last_partial = ""
                        self._capture_mark = ""
                        if audio is not None and (heard or capturing):
                            self.on_line(heard, audio)
                    elif not capturing and recognizer.is_endpoint(stream) and not segment:
                        recognizer.reset(stream)
                        quiet = 0.0
                        voiced = 0.0
                        heard_audio.clear()
                        parts.clear()
                        self._last_partial = ""
        except Exception as exc:
            self.error = f"{_label(self.kind)} se detuvo: {exc}"
            self._report(self.error)
