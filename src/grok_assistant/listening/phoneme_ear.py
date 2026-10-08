"""Keyword spotter for the closed chat.

One microphone capture feeds sherpa's KeywordSpotter and a short ring.
The spotter only listens for the prepared phrase. It does not decide
what Grok hears. The line for «hola grok» is not in this package: those
two words are not in the English lexicon, and a line is not treated as
ready until it has been checked on the real microphone. Until
``hola_grok.txt`` sits next to the model, the setting stays on text.
"""

from __future__ import annotations

import threading
from pathlib import Path

from grok_assistant.paths import bundle_root, default_data_dir

KWS_ARCHIVE = "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2"
KWS_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/" + KWS_ARCHIVE
MODEL_DIR = "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20"
PHRASE_FILE = "hola_grok.txt"
MARK = "@HOLA_GROK"

RATE = 16000
RING_SECONDS = 2.5
PRE_ROLL = 0.25
PHRASE_QUIET = 1.2
MIN_VOICE = 0.4
TAIL_MAX = 30.0
_LOUD = 0.01


def _onnx(folder: Path, role: str) -> Path | None:
    """chunk-16 matches the published example. The encoder and joiner prefer int8."""
    tagged = [path for path in folder.glob(f"*{role}*.onnx") if "chunk-16" in path.name]
    files = tagged or list(folder.glob(f"*{role}*.onnx"))
    if not files:
        return None
    if role == "decoder":
        plain = [path for path in files if "int8" not in path.name]
        return sorted(plain or files)[0]
    int8 = [path for path in files if "int8" in path.name]
    return sorted(int8 or files)[0]


def model_dir() -> Path | None:
    for root in (default_data_dir() / "models", bundle_root() / "models"):
        folder = root / MODEL_DIR
        if folder.is_dir() and (folder / "tokens.txt").is_file() and _onnx(folder, "encoder") is not None:
            return folder
    return None


def _phonemes(line: str) -> list[str]:
    parts = line.split()
    if MARK not in parts:
        return []
    head = parts[: parts.index(MARK)]
    return [token for token in head if token and not token.startswith(":") and not token.startswith("#")]


def prepared_line(folder: Path | None = None) -> str:
    """The hand-written phoneme line, or empty when it has not been left beside the model."""
    folder = model_dir() if folder is None else folder
    if folder is None:
        return ""
    path = folder / PHRASE_FILE
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for raw_line in text.splitlines():
        raw = " ".join(raw_line.split())
        if not raw or raw.startswith("#"):
            continue
        if _phonemes(raw):
            return raw
    return ""


def phrase_ready(wake_name: str) -> bool:
    from grok_assistant.notebook.settings import wake_name_is_grok

    if not wake_name_is_grok(wake_name):
        return False
    return bool(prepared_line())


def _keywords_path(line: str) -> Path:
    folder = default_data_dir() / "kws"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / PHRASE_FILE
    text = line.strip() + "\n"
    current = ""
    if path.is_file():
        try:
            current = path.read_text(encoding="utf-8")
        except OSError:
            current = ""
    if current != text:
        path.write_text(text, encoding="utf-8")
    return path


def _read_hit(result) -> tuple[str, list[float]]:
    if not result:
        return "", []
    if isinstance(result, str):
        return result.strip(), []
    keyword = getattr(result, "keyword", None)
    text = str(result).strip() if keyword is None else str(keyword).strip()
    times: list[float] = []
    raw = getattr(result, "timestamps", None)
    if raw:
        for item in raw:
            try:
                times.append(float(item))
            except (TypeError, ValueError):
                continue
    return text, times


class Ring:
    """The last few seconds at 16 kHz. Older samples fall out."""

    def __init__(self, samples: int):
        self.samples = max(1, int(samples))
        self.data = None
        self.count = 0
        self.pos = 0

    def clear(self) -> None:
        self.count = 0
        self.pos = 0

    def write(self, chunk) -> None:
        import numpy as np

        audio = np.ascontiguousarray(chunk, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            return
        if self.data is None:
            self.data = np.zeros(self.samples, dtype=np.float32)
        if audio.size >= self.samples:
            self.data[:] = audio[-self.samples :]
            self.pos = 0
            self.count = self.samples
            return
        end = self.pos + int(audio.size)
        if end <= self.samples:
            self.data[self.pos : end] = audio
        else:
            first = self.samples - self.pos
            self.data[self.pos :] = audio[:first]
            self.data[: audio.size - first] = audio[first:]
        self.pos = (self.pos + int(audio.size)) % self.samples
        self.count = min(self.samples, self.count + int(audio.size))

    def snapshot(self):
        import numpy as np

        if self.data is None or self.count <= 0:
            return np.zeros(0, dtype=np.float32)
        if self.count < self.samples:
            return self.data[: self.count].copy()
        return np.concatenate((self.data[self.pos :], self.data[: self.pos]))


class _SherpaSpotter:
    def __init__(self, spotter, stream):
        self._spotter = spotter
        self._stream = stream
        self.last_times: list[float] = []

    def accept(self, chunk) -> str:
        import numpy as np

        audio = np.ascontiguousarray(chunk, dtype=np.float32).reshape(-1)
        self._stream.accept_waveform(RATE, audio)
        found = ""
        while self._spotter.is_ready(self._stream):
            self._spotter.decode_stream(self._stream)
            keyword, times = _read_hit(self._spotter.get_result(self._stream))
            if keyword:
                found = keyword
                self.last_times = times
                self._spotter.reset_stream(self._stream)
        return found

    def reset(self) -> None:
        self.last_times = []
        self._spotter.reset_stream(self._stream)


def _build_spotter(folder: Path, line: str) -> _SherpaSpotter:
    import sherpa_onnx

    encoder = _onnx(folder, "encoder")
    decoder = _onnx(folder, "decoder")
    joiner = _onnx(folder, "joiner")
    tokens = folder / "tokens.txt"
    if not all([encoder, decoder, joiner, tokens.is_file()]):
        raise FileNotFoundError("faltan archivos del detector")
    spotter = sherpa_onnx.KeywordSpotter(
        tokens=str(tokens),
        encoder=str(encoder),
        decoder=str(decoder),
        joiner=str(joiner),
        num_threads=2,
        max_active_paths=4,
        keywords_file=str(_keywords_path(line)),
        keywords_score=1.0,
        keywords_threshold=0.25,
        num_trailing_blanks=1,
        provider="cpu",
    )
    return _SherpaSpotter(spotter, spotter.create_stream())


class PhonemeEar:
    """Listens for the prepared phrase and hands back that audio plus the tail."""

    def __init__(self, on_phrase, on_status=None, device: str = "", closed=None):
        self.on_phrase = on_phrase
        self.on_status = on_status or (lambda _text: None)
        self.device = str(device or "")
        self._closed = closed or (lambda: False)
        self.error = ""
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._armed = False
        self._handoff = False
        self._thread: threading.Thread | None = None
        self._source = None
        self._source_lock = threading.Lock()
        self._spotter = None
        self._ring = Ring(int(RING_SECONDS * RATE))
        self._since = 0
        self._tailing = False
        self._phrase: list = []
        self._keyword_audio = None
        self._quiet_n = 0
        self._voice_n = 0
        self._tail_n = 0
        self._dropped = False

    def start(self) -> bool:
        folder = model_dir()
        line = prepared_line(folder)
        if folder is None or not line:
            self.error = "falta la frase preparada"
            return False
        try:
            import sherpa_onnx  # noqa: F401
            import sounddevice  # noqa: F401
        except ImportError:
            self.error = "falta el motor sherpa o el micrófono (sounddevice)"
            return False
        self._thread = threading.Thread(target=self._loop, args=(folder, line), daemon=True, name="phoneme-ear")
        self._thread.start()
        return True

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def accepts_audio(self) -> bool:
        if not self._armed or self._stop.is_set() or self._paused.is_set() or self._handoff:
            return False
        try:
            return not self._closed()
        except Exception:
            return False

    def feed(self, samples) -> bool:
        """Hand one chunk to the spotter. False when this ear is not listening."""
        import numpy as np

        audio = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        if audio.size == 0 or not self.accepts_audio():
            return False
        self._push(audio)
        return True

    def _bind_source(self, source) -> None:
        with self._source_lock:
            self._source = source

    def stop(self) -> None:
        self._stop.set()
        with self._source_lock:
            source = self._source
        from grok_assistant.listening.devices import abort_input

        abort_input(source)

    def join(self, timeout: float = 1.5) -> None:
        thread = self._thread
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

    def _drop_open(self) -> None:
        self._tailing = False
        self._phrase = []
        self._keyword_audio = None
        self._quiet_n = 0
        self._voice_n = 0
        self._tail_n = 0
        self._since = 0
        self._ring.clear()
        if self._spotter is not None and not self._dropped:
            self._spotter.reset()
            self._dropped = True

    def _push(self, chunk) -> None:
        self._dropped = False
        self._ring.write(chunk)
        self._since += int(chunk.size)
        if self._tailing:
            self._phrase.append(chunk.copy())
            self._tail_n += int(chunk.size)
            self._level(chunk)
            if self._tail_done():
                self._finish_tail()
            return
        spotter = self._spotter
        if spotter is None:
            return
        keyword = spotter.accept(chunk)
        if keyword:
            self._begin_tail(list(getattr(spotter, "last_times", []) or []))

    def _begin_tail(self, times: list[float]) -> None:
        snap = self._ring.snapshot()
        pre = int(PRE_ROLL * RATE)
        if times:
            start_kw = int(float(times[0]) * RATE)
        else:
            start_kw = max(0, self._since - int(0.9 * RATE))
        start_phrase = max(0, start_kw - pre)
        end = self._since
        origin = self._since - int(snap.size)

        def index(sample: int) -> int:
            return max(0, min(int(snap.size), int(sample) - origin))

        phrase = snap[index(start_phrase) : index(end)].copy()
        keyword = snap[index(start_kw) : index(end)].copy()
        if keyword.size == 0:
            keyword = phrase
        self._keyword_audio = keyword
        self._phrase = [phrase]
        self._voice_n = int(keyword.size)
        self._quiet_n = 0
        self._tail_n = 0
        self._tailing = True

    def _level(self, chunk) -> None:
        import numpy as np

        audio = np.ascontiguousarray(chunk, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            return
        loud = float(np.sqrt(np.mean(np.square(audio)))) > _LOUD
        if loud:
            self._quiet_n = 0
            self._voice_n += int(audio.size)
        else:
            self._quiet_n += int(audio.size)

    def _tail_done(self) -> bool:
        if self._tail_n >= int(TAIL_MAX * RATE) or self._voice_n >= int(TAIL_MAX * RATE):
            return True
        return self._quiet_n >= int(PHRASE_QUIET * RATE) and self._voice_n >= int(MIN_VOICE * RATE)

    def _finish_tail(self) -> None:
        import numpy as np

        parts = [part for part in self._phrase if part is not None and getattr(part, "size", 0)]
        phrase = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
        keyword = self._keyword_audio
        if keyword is None:
            keyword = phrase
        self._tailing = False
        self._phrase = []
        self._keyword_audio = None
        opened = False
        try:
            opened = bool(self.on_phrase(keyword, phrase))
        except Exception:
            opened = False
        if opened:
            self._handoff = True
            return
        self._since = 0
        if self._spotter is not None:
            self._spotter.reset()

    def _loop(self, folder: Path, line: str) -> None:
        import numpy as np

        try:
            self._spotter = _build_spotter(folder, line)
        except Exception as exc:
            self.error = f"el detector no arrancó: {exc}"
            self._report(self.error)
            return
        self._armed = True
        block = int(0.1 * RATE)
        from grok_assistant.listening.devices import open_input

        try:
            source = open_input(self.device, RATE)
        except Exception as exc:
            self.error = f"el detector no arrancó: {exc}"
            self._report(self.error)
            return
        self._bind_source(source)
        try:
            if self._stop.is_set():
                from grok_assistant.listening.devices import close_input

                close_input(source)
                return
            self._report("el detector de la frase de inicio está escuchando")
            with source:
                while not self._stop.is_set():
                    try:
                        samples, _overflow = source.read(block)
                    except Exception:
                        if self._stop.is_set():
                            return
                        raise
                    if self._handoff:
                        return
                    chunk = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
                    if not self.accepts_audio():
                        self._drop_open()
                        continue
                    self._push(chunk)
                    if self._handoff:
                        return
        except Exception as exc:
            if self._stop.is_set():
                return
            self.error = f"el detector se detuvo: {exc}"
            self._report(self.error)
        finally:
            self._bind_source(None)
