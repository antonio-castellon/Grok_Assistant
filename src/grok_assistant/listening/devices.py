"""Input devices. An empty choice is the system default."""

from __future__ import annotations


def normalize_microphone(value) -> str:
    """The stored device name. Empty means the system default."""
    text = " ".join(str(value or "").split())
    if len(text) > 180:
        text = text[:180].rstrip()
    return text


def list_inputs(devices, default_hostapi: int) -> list[dict]:
    """One row per input name. The default host API wins when a name is repeated."""
    rows = []
    for position, device in enumerate(devices):
        try:
            channels = int(device["max_input_channels"])
        except (KeyError, TypeError, ValueError):
            continue
        if channels <= 0:
            continue
        name = " ".join(str(device.get("name") or "").split())
        if not name:
            continue
        try:
            host = int(device["hostapi"])
        except (KeyError, TypeError, ValueError):
            host = 0
        try:
            number = int(device["index"])
        except (KeyError, TypeError, ValueError):
            number = position
        rows.append({"index": number, "name": name, "hostapi": host})
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


def listed_inputs() -> list[dict] | None:
    """None when the device list cannot be read. An empty list means no inputs."""
    try:
        import sounddevice as sd

        devices = list(sd.query_devices())
        host = int(sd.default.hostapi)
    except Exception:
        return None
    return list_inputs(devices, host)


def resolve_microphone(saved: str, mics: list[dict] | None = None) -> tuple[str, int | None]:
    """The name to keep, and the input index. An unread list keeps the name and uses the default."""
    name = normalize_microphone(saved)
    if mics is None:
        mics = listed_inputs()
    if mics is None:
        return name, None
    if not name:
        return "", None
    for mic in mics:
        if mic["name"] == name:
            return name, int(mic["index"])
    return "", None


def open_input(saved: str, samplerate: int = 16000):
    """Open the chosen input, or the system default when the name is empty or gone."""
    import sounddevice as sd

    _name, index = resolve_microphone(saved)
    if index is None:
        return sd.InputStream(channels=1, dtype="float32", samplerate=samplerate)
    return sd.InputStream(channels=1, dtype="float32", samplerate=samplerate, device=index)
