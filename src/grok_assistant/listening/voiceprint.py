"""A local voice fingerprint. Audio stays on this PC."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from grok_assistant.paths import default_data_dir

_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
    "speaker-recongition-models/3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx"
)
_NAME = "3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx"


class VoicePrint:
    def __init__(self, folder: Path | None = None):
        root = folder or default_data_dir() / "models"
        self.path = root / _NAME
        self._extractor = None

    def ready(self) -> bool:
        return self.path.exists() and self.path.stat().st_size > 1_000_000

    def ensure(self) -> bool:
        if self.ready():
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        part = self.path.with_name(self.path.name + ".part")
        try:
            request = urllib.request.Request(_URL, headers={"User-Agent": "GrokAssistant"})
            with urllib.request.urlopen(request, timeout=120) as response, part.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)
            part.replace(self.path)
        except (OSError, TimeoutError):
            part.unlink(missing_ok=True)
            return False
        return self.ready()

    def embed(self, samples) -> list[float] | None:
        if samples is None or not self.ensure():
            return None
        try:
            import numpy as np
            import sherpa_onnx
        except ImportError:
            return None
        audio = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        if audio.size < 16000 // 2:
            return None
        try:
            if self._extractor is None:
                # sherpa-onnx 1.13 takes one config object. Keyword arguments
                # raise TypeError, and that used to throw away a heard take.
                config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                    model=str(self.path),
                    num_threads=1,
                    debug=False,
                    provider="cpu",
                )
                self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
            stream = self._extractor.create_stream()
            stream.accept_waveform(16000, audio)
            stream.input_finished()
            if not self._extractor.is_ready(stream):
                return None
            vector = self._extractor.compute(stream)
            return [float(item) for item in vector]
        except (OSError, RuntimeError, ValueError, TypeError):
            return None
