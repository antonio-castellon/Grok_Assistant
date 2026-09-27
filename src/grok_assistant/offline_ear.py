"""Offline ears for Whisper and Canary. Audio stays here. A finished phrase is text."""

from __future__ import annotations

import threading
from pathlib import Path

from grok_assistant.listen import ENGINE_DIRS
from grok_assistant.paths import bundle_root, default_data_dir

OFFLINE_KINDS = ("whisper", "base", "canary")


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


class OfflineEar:
    def __init__(self, kind: str, on_line, on_status=None):
        self.kind = kind
        self.on_line = on_line
        self.on_status = on_status or (lambda _text: None)
        self.error = ""
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None

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
        self._thread = threading.Thread(target=self._loop, daemon=True)
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

    def _recognizer(self, folder: Path):
        import sherpa_onnx

        encoder = _onnx(folder, "encoder")
        decoder = _onnx(folder, "decoder")
        tokens = _tokens(folder)
        if not all([encoder, decoder, tokens]):
            raise FileNotFoundError("al modelo le faltan archivos")
        if self.kind == "canary":
            return sherpa_onnx.OfflineRecognizer.from_nemo_canary(
                encoder=str(encoder),
                decoder=str(decoder),
                tokens=str(tokens),
                src_lang="es",
                tgt_lang="es",
                num_threads=2,
            )
        return sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(encoder),
            decoder=str(decoder),
            tokens=str(tokens),
            language="es",
            task="transcribe",
            num_threads=2,
        )

    def _loop(self) -> None:
        import numpy as np
        import sounddevice as sd

        folder = model_dir(self.kind)
        if folder is None:
            self.error = "ese modelo no está en el disco"
            self._report(self.error)
            return
        try:
            recognizer = self._recognizer(folder)
            source = sd.InputStream(channels=1, dtype="float32", samplerate=16000)
        except Exception as exc:
            self.error = f"el oído no arrancó: {exc}"
            self._report(self.error)
            return
        self._report("el oído local está escuchando el micrófono")
        rate = 16000
        block = int(0.1 * rate)
        speech: list = []
        voiced = 0.0
        silent = 0.0
        try:
            with source:
                while not self._stop.is_set():
                    samples, _overflow = source.read(block)
                    if self._paused.is_set():
                        speech.clear()
                        voiced = 0.0
                        silent = 0.0
                        continue
                    chunk = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
                    loud = float(np.sqrt(np.mean(chunk * chunk))) > 0.008
                    if loud:
                        speech.append(chunk)
                        voiced += 0.1
                        silent = 0.0
                    elif speech:
                        speech.append(chunk)
                        silent += 0.1
                    ended = speech and ((silent >= 0.7 and voiced >= 0.4) or voiced >= 30.0)
                    if not ended:
                        continue
                    audio = np.concatenate(speech)
                    speech.clear()
                    voiced = 0.0
                    silent = 0.0
                    stream = recognizer.create_stream()
                    stream.accept_waveform(rate, audio)
                    recognizer.decode_stream(stream)
                    text = str(getattr(stream.result, "text", "")).strip()
                    if text:
                        self.on_line(text)
        except Exception as exc:
            self.error = f"el oído se detuvo: {exc}"
            self._report(self.error)
