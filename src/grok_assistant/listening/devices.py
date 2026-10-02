"""Input and output devices. An empty choice is the system default.

Windows lists the same endpoint once per driver. WASAPI is the set Windows
itself shows. The older drivers also publish loopbacks, such as PC Speaker
and Stereo Mix, and those are not microphones.
"""

from __future__ import annotations


def normalize_device(value) -> str:
    """The stored device name. Empty means the system default."""
    text = " ".join(str(value or "").split())
    if len(text) > 180:
        text = text[:180].rstrip()
    return text


normalize_microphone = normalize_device


def _wasapi_host(hostapis) -> int | None:
    if not hostapis:
        return None
    for index, host in enumerate(hostapis):
        name = str(host.get("name") if isinstance(host, dict) else host)
        if "WASAPI" in name.upper():
            return index
    return None


def _rejected(name: str, channel: str) -> bool:
    folded = name.casefold()
    blocked = (
        "loopback",
        "sound mapper",
        "primary sound capture",
        "primary sound driver",
    )
    if channel == "max_input_channels":
        blocked = blocked + (
            "stereo mix",
            "stereomix",
            "mezcla estereo",
            "mezcla estéreo",
            "what u hear",
            "pc speaker",
        )
    return any(needle in folded for needle in blocked)


def _collect(devices, channel: str, only: int | None) -> list[dict]:
    rows = []
    for position, device in enumerate(devices):
        try:
            count = int(device[channel])
        except (KeyError, TypeError, ValueError):
            continue
        if count <= 0:
            continue
        name = " ".join(str(device.get("name") or "").split())
        if not name or _rejected(name, channel):
            continue
        try:
            host = int(device["hostapi"])
        except (KeyError, TypeError, ValueError):
            host = 0
        if only is not None and host != only:
            continue
        try:
            number = int(device["index"])
        except (KeyError, TypeError, ValueError):
            number = position
        rows.append({"index": number, "name": name, "hostapi": host})
    return rows


def _dedupe(rows: list[dict], default_hostapi: int) -> list[dict]:
    chosen: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        key = row["name"]
        if key not in chosen:
            chosen[key] = row
            order.append(key)
            continue
        current = chosen[key]
        if row["hostapi"] == default_hostapi and current["hostapi"] != default_hostapi:
            chosen[key] = row
    return [
        {"index": chosen[key]["index"], "name": chosen[key]["name"], "hostapi": chosen[key]["hostapi"]}
        for key in order
    ]


def _ends(devices, default_hostapi: int, hostapis, channel: str) -> list[dict]:
    only = _wasapi_host(hostapis)
    rows = _collect(devices, channel, only)
    if only is not None and not rows:
        rows = _collect(devices, channel, None)
    return _dedupe(rows, default_hostapi)


def list_inputs(devices, default_hostapi: int, hostapis=None) -> list[dict]:
    """One row per microphone name. WASAPI wins on Windows. Output-only rows stay out."""
    return _ends(devices, default_hostapi, hostapis, "max_input_channels")


def list_outputs(devices, default_hostapi: int, hostapis=None) -> list[dict]:
    """One row per speaker name. WASAPI wins on Windows."""
    return _ends(devices, default_hostapi, hostapis, "max_output_channels")


def _query():
    import sounddevice as sd

    return list(sd.query_devices()), int(sd.default.hostapi), list(sd.query_hostapis())


def listed_inputs() -> list[dict] | None:
    """None when the device list cannot be read. An empty list means no microphones."""
    try:
        devices, host, hostapis = _query()
    except Exception:
        return None
    return list_inputs(devices, host, hostapis)


def listed_outputs() -> list[dict] | None:
    """None when the device list cannot be read. An empty list means no speakers."""
    try:
        devices, host, hostapis = _query()
    except Exception:
        return None
    return list_outputs(devices, host, hostapis)


def _resolve(saved: str, rows: list[dict] | None, listed) -> tuple[str, int | None]:
    """The name to keep, and the device index. An unread list keeps the name and uses the default."""
    name = normalize_device(saved)
    if rows is None:
        rows = listed()
    if rows is None:
        return name, None
    if not name:
        return "", None
    for row in rows:
        if row["name"] == name:
            return name, int(row["index"])
    return "", None


def resolve_microphone(saved: str, mics: list[dict] | None = None) -> tuple[str, int | None]:
    return _resolve(saved, mics, listed_inputs)


def resolve_output(saved: str, speakers: list[dict] | None = None) -> tuple[str, int | None]:
    return _resolve(saved, speakers, listed_outputs)


def _invalid_rate(exc: BaseException) -> bool:
    text = str(exc).casefold()
    return "invalid sample rate" in text or "-9997" in text


def _native_rate(index: int | None) -> int | None:
    """The rate the endpoint actually opens at. WASAPI often refuses 16 kHz."""
    import sounddevice as sd

    try:
        if index is None:
            chosen = sd.default.device[0]
            if chosen is None or int(chosen) < 0:
                return None
            info = sd.query_devices(int(chosen))
        else:
            info = sd.query_devices(int(index))
        rate = int(round(float(info["default_samplerate"])))
    except Exception:
        return None
    return rate if rate > 0 else None


def _resample(samples, source_rate: int, target_rate: int):
    import numpy as np

    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    if audio.size == 0 or source_rate == target_rate:
        return audio
    length = int(round(audio.size * target_rate / source_rate))
    if length <= 1:
        return audio[:1]
    positions = np.linspace(0.0, audio.size - 1, length)
    return np.interp(positions, np.arange(audio.size, dtype=np.float64), audio).astype(np.float32)


class _ResampledInput:
    """A stream opened at the device rate whose read() returns the recognizer rate."""

    def __init__(self, stream, source_rate: int, target_rate: int):
        self._stream = stream
        self._source = source_rate
        self._target = target_rate

    def read(self, frames: int):
        count = max(1, int(round(frames * self._source / self._target)))
        data, overflow = self._stream.read(count)
        audio = _resample(data, self._source, self._target)
        import numpy as np

        if audio.size < frames:
            audio = np.pad(audio, (0, frames - audio.size))
        elif audio.size > frames:
            audio = audio[:frames]
        return audio, overflow

    def __enter__(self):
        self._stream.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._stream.__exit__(exc_type, exc, tb)

    def start(self):
        return self._stream.start()

    def stop(self):
        return self._stream.stop()

    def close(self):
        return self._stream.close()


def open_input(saved: str, samplerate: int = 16000, latency: float | None = None):
    """Open the chosen input, or the system default when the name is empty or gone.

    The recognizer wants 16 kHz. A WASAPI microphone often accepts only its own
    mix rate, so that stream is opened there and each read is brought back.
    """
    import sounddevice as sd

    wanted = int(samplerate)
    kwargs = {"channels": 1, "dtype": "float32", "samplerate": wanted}
    if latency is not None:
        kwargs["latency"] = latency
    _name, index = resolve_microphone(saved)
    if index is not None:
        kwargs["device"] = index
    try:
        return sd.InputStream(**kwargs)
    except Exception as exc:
        if not _invalid_rate(exc):
            raise
        native = _native_rate(index)
        if native is None or native == wanted:
            raise
        kwargs["samplerate"] = native
        return _ResampledInput(sd.InputStream(**kwargs), native, wanted)


def _play_on(audio, rate: int, index: int | None) -> bool:
    import sounddevice as sd

    kwargs = {}
    if index is not None:
        kwargs["device"] = index
    try:
        sd.play(audio, rate, **kwargs)
        sd.wait()
        return True
    except Exception:
        try:
            sd.stop()
        except Exception:
            pass
        return False


def play_samples(audio, rate: int, saved: str = "") -> bool:
    """Play samples on the chosen speaker. A missing name uses the system default."""
    _name, index = resolve_output(saved)
    if _play_on(audio, rate, index):
        return True
    if index is None:
        return False
    return _play_on(audio, rate, None)


def play_wav(path: str, saved: str = "") -> bool:
    """Play a wav file on the chosen speaker."""
    import wave

    import numpy as np

    try:
        with wave.open(path, "rb") as handle:
            rate = handle.getframerate()
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            frames = handle.readframes(handle.getnframes())
    except (OSError, wave.Error):
        return False
    if not frames or rate <= 0 or width not in (1, 2, 4):
        return False
    kind = {1: np.uint8, 2: np.int16, 4: np.int32}[width]
    audio = np.frombuffer(frames, dtype=kind)
    if width == 1:
        audio = (audio.astype(np.float32) - 128.0) / 128.0
    else:
        audio = audio.astype(np.float32) / float(np.iinfo(kind).max)
    if channels > 1:
        audio = audio.reshape(-1, channels)
    return play_samples(audio, rate, saved)
