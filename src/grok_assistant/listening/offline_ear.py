"""Offline ears for Whisper, Canary, and Cohere.

Audio stays here. The capture thread writes a temporary wav and, on a short
pause, asks the recognizer for the words so far. The phrase goes on after
1.2 seconds without a new word. The model is loaded once.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path

from grok_assistant.listening.enroll_audio import TAKE_MAX_VOICE, TAKE_MIN_VOICE, TAKE_QUIET
from grok_assistant.listening.listen import ENGINE_DIRS
from grok_assistant.paths import bundle_root, default_data_dir

OFFLINE_KINDS = ("whisper", "base", "small", "canary", "cohere")
_WORD_GAP = 0.3
_PARTIAL_STEP = 0.8
_REUSE_TAIL = 1.0


def model_dir(kind: str) -> Path | None:
    name = ENGINE_DIRS.get(kind)
    if not name:
        return None
    for root in (default_data_dir() / "models", bundle_root() / "models"):
        folder = root / name
        if folder.is_dir() and any(folder.glob("*tokens.txt")):
            return folder
    return None


def _onnx(folder: Path, role: str) -> Path | None:
    files = list(folder.glob(f"*{role}*.onnx"))
    if not files:
        return None
    int8 = [path for path in files if "int8" in path.name]
    return sorted(int8 or files)[0]


def _tokens(folder: Path) -> Path | None:
    found = list(folder.glob("*tokens.txt"))
    return sorted(found)[0] if found else None


_clip_recognizers: dict = {}


def transcribe_clip(kind: str, samples) -> str:
    """Read one saved phrase with Whisper or Canary."""
    if kind not in OFFLINE_KINDS or samples is None:
        return ""
    try:
        import numpy as np
    except ImportError:
        return ""
    try:
        recognizer = _clip_recognizers.get(kind)
        if recognizer is None:
            folder = model_dir(kind)
            if folder is None:
                return ""
            recognizer = OfflineEar(kind, lambda *_args: None)._recognizer(folder)
            _clip_recognizers[kind] = recognizer
        audio = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        if audio.size < 1600:
            return ""
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, audio)
        recognizer.decode_stream(stream)
        return str(getattr(stream.result, "text", "") or "").strip()
    except (OSError, RuntimeError, ValueError, TypeError, FileNotFoundError, ImportError):
        return ""


class OfflineEar:
    def __init__(self, kind: str, on_line, on_status=None, silence=None, device: str = "", on_partial=None):
        self.kind = kind
        self.device = str(device or "")
        self.on_line = on_line
        self.on_partial = on_partial or (lambda *_ignored: None)
        self.on_status = on_status or (lambda _text: None)
        self._silence = silence or (lambda: 1.2)
        self.error = ""
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._capture = threading.Event()
        self._flush = threading.Event()
        self._hold = False
        self._wake = threading.Event()
        self._word_arrived = threading.Event()
        self._lock = threading.Lock()
        self._partial_audio = None
        self._partial_seq = 0
        self._last_partial = ""
        self._decoded_n = 0
        self._decoded_text = ""
        self._offered_voice = 0.0
        self._gap_sent = False
        self._clips: queue.Queue = queue.Queue()
        self._recognizer_live = None
        self._model_ready = threading.Event()
        self._overflowed = False
        self._tape = None
        self._source = None
        self._source_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._decode_thread: threading.Thread | None = None

    def start(self) -> bool:
        if model_dir(self.kind) is None:
            self.error = "ese modelo no está en el disco"
            return False
        try:
            import sherpa_onnx  # noqa: F401
            import sounddevice  # noqa: F401
        except ImportError:
            self.error = "falta el motor sherpa o el micrófono (sounddevice)"
            return False
        self._decode_thread = threading.Thread(target=self._decode, name="ear-stt", daemon=True)
        self._thread = threading.Thread(target=self._loop, name="ear-capture", daemon=True)
        self._decode_thread.start()
        self._thread.start()
        return True

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def set_capture(self, capture: bool) -> None:
        if capture:
            self._capture.set()
        else:
            self._capture.clear()

    def set_hold(self, hold: bool) -> None:
        """While the print window is open, Seguir keeps the phrase and Reintentar clears it."""
        self._hold = bool(hold)

    def request_flush(self) -> None:
        """Hand back the open take when the wait runs out."""
        self._flush.set()

    def _bind_source(self, source) -> None:
        with self._source_lock:
            self._source = source

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        with self._source_lock:
            source = self._source
        from grok_assistant.listening.devices import abort_input

        abort_input(source)

    def join(self, timeout: float = 1.5) -> None:
        for thread in (self._thread, self._decode_thread):
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout)

    def _report(self, text: str) -> None:
        self.on_status(text)
        try:
            path = default_data_dir() / "ear.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except OSError:
            return

    def _recognizer(self, folder: Path):
        import sherpa_onnx

        encoder = _onnx(folder, "encoder")
        decoder = _onnx(folder, "decoder")
        tokens = _tokens(folder)
        if not all([encoder, decoder, tokens]):
            raise FileNotFoundError("al modelo le faltan archivos")
        from grok_assistant.i18n import stt_language

        lang = stt_language() if stt_language() in {"en", "es", "de", "fr"} else "es"
        if self.kind == "canary":
            return sherpa_onnx.OfflineRecognizer.from_nemo_canary(
                encoder=str(encoder),
                decoder=str(decoder),
                tokens=str(tokens),
                src_lang=lang,
                tgt_lang=lang,
                num_threads=2,
            )
        if self.kind == "cohere":
            return sherpa_onnx.OfflineRecognizer.from_cohere_transcribe(
                encoder=str(encoder),
                decoder=str(decoder),
                tokens=str(tokens),
                language=lang,
                num_threads=2,
            )
        return sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(encoder),
            decoder=str(decoder),
            tokens=str(tokens),
            language=lang,
            task="transcribe",
            num_threads=2,
        )

    def _decode(self) -> None:
        folder = model_dir(self.kind)
        if folder is None:
            self.error = "ese modelo no está en el disco"
            self._report(self.error)
            self._model_ready.set()
            return
        try:
            self._recognizer_live = self._recognizer(folder)
        except Exception as exc:
            self.error = f"el oído no arrancó: {exc}"
            self._report(self.error)
            self._model_ready.set()
            return
        self._model_ready.set()
        self._serve_clips()

    def _serve_clips(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(0.2)
            self._wake.clear()
            while not self._stop.is_set():
                try:
                    audio, capturing = self._clips.get_nowait()
                except queue.Empty:
                    break
                try:
                    self._transcribe(audio, capturing)
                except Exception as exc:
                    self._report(f"el reconocedor no pudo leer una frase: {exc}")
            partial = self._take_partial()
            if partial is None:
                continue
            try:
                self._transcribe_partial(partial)
            except Exception as exc:
                self._report(f"el reconocedor no pudo adelantar una palabra: {exc}")

    def _offer_partial(self, audio) -> None:
        with self._lock:
            self._partial_audio = audio
        self._wake.set()

    def _take_partial(self):
        with self._lock:
            audio = self._partial_audio
            self._partial_audio = None
        return audio

    def _submit(self, audio, capturing: bool) -> None:
        with self._lock:
            self._partial_audio = None
        waiting = self._clips.qsize()
        self._clips.put((audio, capturing))
        self._wake.set()
        if waiting:
            self._report(f"hay {waiting + 1} frases esperando al reconocedor")

    def _covers(self, audio) -> bool:
        shape = getattr(audio, "shape", None)
        if not shape or not self._decoded_text or self._decoded_n <= 0:
            return False
        extra = int(shape[0]) - self._decoded_n
        return 0 <= extra <= int(_REUSE_TAIL * 16000)

    def _read(self, audio) -> str:
        recognizer = self._recognizer_live
        if recognizer is None:
            return ""
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, audio)
        recognizer.decode_stream(stream)
        return str(getattr(stream.result, "text", "")).strip()

    def _transcribe(self, audio, capturing: bool) -> None:
        text = self._decoded_text if self._covers(audio) else self._read(audio)
        self._decoded_n = 0
        self._decoded_text = ""
        self._last_partial = ""
        if capturing or text:
            self.on_line(text, audio)

    def _transcribe_partial(self, audio) -> None:
        text = self._read(audio)
        shape = getattr(audio, "shape", None)
        self._decoded_n = int(shape[0]) if shape else 0
        self._decoded_text = text
        if self._clips.qsize() or not text or text == self._last_partial:
            return
        self._partial_seq += 1
        self._last_partial = text
        self._word_arrived.set()
        self.on_partial(text, self._partial_seq)

    def _consider_partial(self, speech, silent: float, loud: bool, voiced: float) -> None:
        if voiced < 0.4:
            return
        gap = (not loud) and silent >= _WORD_GAP and not self._gap_sent
        step = loud and (voiced - self._offered_voice) >= _PARTIAL_STEP
        if not gap and not step:
            return
        import numpy as np

        self._offer_partial(np.concatenate(speech))
        self._offered_voice = voiced
        if gap:
            self._gap_sent = True

    def _tape_write(self, chunk) -> None:
        if self._tape is None:
            from grok_assistant.listening.spool import PhraseTape

            self._tape = PhraseTape()
        self._tape.write(chunk)

    def _tape_finish(self, keep: bool) -> None:
        tape = self._tape
        self._tape = None
        if tape is not None:
            tape.finish(keep)

    def _reset_offer(self) -> None:
        self._offered_voice = 0.0
        self._gap_sent = False

    def _loop(self) -> None:
        import numpy as np

        if not self._model_ready.wait(30):
            return
        if self._recognizer_live is None or self._stop.is_set():
            return
        try:
            from grok_assistant.listening.devices import open_input

            # A deeper buffer keeps the words said while the recognizer is still busy.
            source = open_input(self.device, 16000, latency=0.5)
        except Exception as exc:
            self.error = f"el oído no arrancó: {exc}"
            self._report(self.error)
            return
        self._bind_source(source)
        try:
            if self._stop.is_set():
                from grok_assistant.listening.devices import close_input

                close_input(source)
                return
            self._report("el oído local está escuchando el micrófono")
            rate = 16000
            block = int(0.1 * rate)
            speech: list = []
            voiced = 0.0
            silent = 0.0
            with source:
                while not self._stop.is_set():
                    try:
                        samples, overflow = source.read(block)
                    except Exception:
                        if self._stop.is_set():
                            self._tape_finish(False)
                            return
                        raise
                    if overflow and not self._overflowed:
                        self._report("el micrófono llenó el búfer y se perdió un trozo")
                    self._overflowed = bool(overflow)
                    if self._paused.is_set():
                        speech.clear()
                        voiced = 0.0
                        silent = 0.0
                        self._reset_offer()
                        self._tape_finish(False)
                        self._flush.clear()
                        continue
                    chunk = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
                    capturing = self._capture.is_set()
                    loud = float(np.sqrt(np.mean(chunk * chunk))) > (0.004 if capturing else 0.008)
                    if loud:
                        speech.append(chunk)
                        voiced += 0.1
                        silent = 0.0
                        self._gap_sent = False
                    elif speech:
                        speech.append(chunk)
                        silent += 0.1
                    if speech:
                        self._tape_write(chunk)
                    if self._word_arrived.is_set():
                        self._word_arrived.clear()
                        if speech:
                            silent = 0.0
                    flushing = self._flush.is_set()
                    if flushing:
                        self._flush.clear()
                    if capturing:
                        ended = bool(speech) and (
                            voiced >= TAKE_MAX_VOICE
                            or (flushing and voiced > 0)
                            or (
                                not self._hold
                                and silent >= TAKE_QUIET
                                and voiced >= TAKE_MIN_VOICE
                            )
                        )
                    else:
                        try:
                            pause = float(self._silence())
                        except (TypeError, ValueError):
                            pause = 1.2
                        pause = min(2.0, max(1.2, pause))
                        if speech and silent >= pause and voiced < 0.4:
                            speech.clear()
                            voiced = 0.0
                            silent = 0.0
                            self._reset_offer()
                            self._tape_finish(False)
                            continue
                        self._consider_partial(speech, silent, loud, voiced)
                        ended = speech and ((silent >= pause and voiced >= 0.4) or voiced >= 30.0)
                    if not ended:
                        continue
                    audio = np.concatenate(speech)
                    speech.clear()
                    voiced = 0.0
                    silent = 0.0
                    self._reset_offer()
                    self._tape_finish(True)
                    self._submit(audio, capturing)
        except Exception as exc:
            self._tape_finish(False)
            if self._stop.is_set():
                return
            self.error = f"el oído se detuvo: {exc}"
            self._report(self.error)
        finally:
            self._bind_source(None)
