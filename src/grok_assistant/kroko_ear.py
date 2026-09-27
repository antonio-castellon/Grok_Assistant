"""Spanish Kroko ear. Audio stays in this process. A finished phrase is text."""

from __future__ import annotations

import threading
from pathlib import Path

from grok_assistant.listen import ENGINE_DIRS
from grok_assistant.paths import bundle_root, default_data_dir


def kroko_dir() -> Path | None:
    name = ENGINE_DIRS["kroko"]
    for root in (default_data_dir() / "models", bundle_root() / "models"):
        folder = root / name
        if folder.is_dir() and (folder / "tokens.txt").exists():
            return folder
    return None


def _model(folder: Path, prefix: str) -> Path | None:
    files = list(folder.glob(f"{prefix}*.onnx"))
    if not files:
        return None
    int8 = [path for path in files if "int8" in path.name]
    return sorted(int8 or files)[0]


class KrokoEar:
    def __init__(self, on_line, on_status=None):
        self.on_line = on_line
        self.on_status = on_status or (lambda _text: None)
        self.error = ""
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        folder = kroko_dir()
        if folder is None:
            self.error = "el modelo Kroko no está en el disco"
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

    def stop(self) -> None:
        self._stop.set()

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
                self.error = "al modelo Kroko le faltan archivos"
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
            self.error = f"Kroko no arrancó: {exc}"
            self._report(self.error)
            return
        self._report("Kroko está escuchando el micrófono")
        try:
            with source:
                quiet = 0.0
                while not self._stop.is_set():
                    samples, _overflow = source.read(block)
                    if self._paused.is_set():
                        recognizer.reset(stream)
                        quiet = 0.0
                        continue
                    chunk = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
                    stream.accept_waveform(rate, chunk)
                    while recognizer.is_ready(stream):
                        recognizer.decode_stream(stream)
                    result = recognizer.get_result(stream)
                    text = result if isinstance(result, str) else getattr(result, "text", "")
                    text = str(text).strip()
                    loud = float(np.sqrt(np.mean(np.square(chunk)))) > 0.01
                    quiet = 0.0 if loud else quiet + 0.1
                    # 0.7 s of quiet, or the model's own short endpoint. Either stays under two seconds.
                    if text and (quiet >= 0.7 or recognizer.is_endpoint(stream)):
                        recognizer.reset(stream)
                        quiet = 0.0
                        self.on_line(text)
                    elif recognizer.is_endpoint(stream):
                        recognizer.reset(stream)
                        quiet = 0.0
        except Exception as exc:
            self.error = f"Kroko se detuvo: {exc}"
            self._report(self.error)
