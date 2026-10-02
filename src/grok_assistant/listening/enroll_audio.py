"""One recording of known phrases. The raw sound is the print; every listener is derived from it."""

from __future__ import annotations

from pathlib import Path

# Sixteen different phrases, once each. Four phrases said three times only
# remeasure the same words. These cover greetings, questions and orders, so the
# print and the score both see more of the voice. One take of each keeps the
# session short enough that one person stays one cluster.
PHRASES = (
    "hola grok",
    "estás ahí",
    "qué hora es",
    "pon una canción",
    "sube el volumen",
    "baja el volumen",
    "para la música",
    "buenos días",
    "hasta luego",
    "qué día es hoy",
    "me escuchas",
    "gracias",
    "abre la sesión",
    "cuenta hasta tres",
    "cómo estás",
    "dime la hora",
)


def enroll_phrases(name: str | None = None) -> tuple[str, ...]:
    """The greeting uses the current wake name. The other fifteen stay as written."""
    called = " ".join((name or "").split())
    if not called or called.casefold() == "grok":
        return PHRASES
    adapted = []
    for phrase in PHRASES:
        adapted.append(" ".join(called if word.casefold() == "grok" else word for word in phrase.split()))
    return tuple(adapted)


# A print locks only when this many takes sit in one voice.
MIN_KEEP = 12
# Same floor the door uses. A take under this is not stored as another person.
SAME = 0.55


def phrase_hit(expected: str, heard: str) -> bool:
    """True when the heard line contains the expected words, in order."""
    from grok_assistant.textutil import loose, normalize

    exp = normalize(expected).split()
    got = normalize(heard).split()
    if not exp or not got:
        return False
    found = 0
    start = 0
    for word in exp:
        for index in range(start, len(got)):
            if word == got[index] or loose(word, got[index]):
                found += 1
                start = index + 1
                break
    # Three words or fewer have to come through. A longer line may miss one.
    need = len(exp) if len(exp) <= 3 else len(exp) - 1
    return found >= need


def one_voice(vectors: list) -> list[int] | None:
    """Indexes of the takes that belong together.

    The largest group in which every pair is the same voice. A second group
    is dropped. If no group reaches MIN_KEEP, nothing is returned: the
    recording is not saved as another person.
    """
    usable = [(index, [float(item) for item in vector]) for index, vector in enumerate(vectors) if vector]
    count = len(usable)
    if count < MIN_KEEP:
        return None
    cos = [[1.0] * count for _ in range(count)]
    for left in range(count):
        for right in range(left + 1, count):
            score = _cosine(usable[left][1], usable[right][1])
            cos[left][right] = score
            cos[right][left] = score
    everyone = list(range(count))
    if _pairs_ok(everyone, cos):
        return [usable[index][0] for index in everyone]
    best: list[int] = []
    if count <= 20:
        for mask in range(1, 1 << count):
            chosen = [index for index in range(count) if mask & (1 << index)]
            if len(chosen) < MIN_KEEP or len(chosen) <= len(best):
                continue
            if _pairs_ok(chosen, cos):
                best = chosen
    else:
        best = _drop_until_one(cos)
    if len(best) < MIN_KEEP:
        return None
    return [usable[index][0] for index in best]


def write_wav(path: Path, samples) -> None:
    import wave

    import numpy as np

    audio = np.clip(np.ascontiguousarray(samples, dtype=np.float32).reshape(-1), -1.0, 1.0)
    pcm = (audio * 32767.0).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(pcm.tobytes())


def read_wav(path: Path):
    import wave

    import numpy as np

    if not path.exists():
        return None
    with wave.open(str(path), "rb") as handle:
        frames = handle.readframes(handle.getnframes())
        width = handle.getsampwidth()
        rate = handle.getframerate() or 16000
    if width != 2 or not frames:
        return None
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32767.0
    if rate == 16000:
        return np.ascontiguousarray(audio)
    target = int(audio.size * 16000 / rate)
    if target < 1:
        return None
    positions = np.linspace(0, audio.size - 1, target)
    return np.interp(positions, np.arange(audio.size), audio).astype(np.float32)


# A take stays open through a short breath. One second of quiet means the phrase ended.
TAKE_QUIET = 1.0
TAKE_MIN_VOICE = 0.8
TAKE_MAX_VOICE = 8.0


def tone(start: bool) -> tuple[int, int]:
    """A high short beep opens the microphone. A lower one closes it."""
    if start:
        return 880, 140
    return 494, 220


def play_tone(start: bool, output: str = "") -> None:
    frequency, duration = tone(start)
    if output and _tone_on_speaker(frequency, duration, output):
        return
    try:
        import winsound

        winsound.Beep(frequency, duration)
    except (ImportError, RuntimeError, OSError):
        return


def _tone_on_speaker(frequency: int, duration: int, output: str) -> bool:
    try:
        import numpy as np

        from grok_assistant.listening.devices import play_samples
    except Exception:
        return False
    rate = 16000
    count = max(1, int(rate * duration / 1000))
    step = np.arange(count, dtype=np.float32) / rate
    wave = (0.2 * np.sin(2 * np.pi * frequency * step)).astype(np.float32)
    fade = min(160, count // 4)
    if fade:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        wave[:fade] *= ramp
        wave[-fade:] *= ramp[::-1]
    return play_samples(wave, rate, output)


def record_phrase(read=None, seconds: float = 8.0):
    """Record one phrase from the microphone. None when the mic stays quiet."""
    import numpy as np

    own = None
    if read is None:
        own = _open_mic()
        if own is None:
            return None
        read = own
    speech: list = []
    voiced = 0.0
    silent = 0.0
    waited = 0.0
    try:
        while waited < seconds:
            chunk = read(1600)
            if chunk is None:
                break
            audio = np.ascontiguousarray(chunk, dtype=np.float32).reshape(-1)
            waited += 0.1
            loud = audio.size > 0 and float(np.sqrt(np.mean(audio * audio))) > 0.008
            if loud:
                speech.append(audio)
                voiced += 0.1
                silent = 0.0
            elif speech:
                speech.append(audio)
                silent += 0.1
            if speech and ((silent >= 0.7 and voiced >= 0.5) or voiced >= 6.0):
                return np.concatenate(speech)
        if speech and voiced >= 0.5:
            return np.concatenate(speech)
        return None
    finally:
        if own is not None:
            own.close()


class _Mic:
    def __init__(self):
        import sounddevice as sd

        self.source = sd.InputStream(channels=1, dtype="float32", samplerate=16000)
        self.source.start()

    def __call__(self, count: int):
        samples, _overflow = self.source.read(count)
        return samples

    def close(self) -> None:
        self.source.stop()
        self.source.close()


def _open_mic():
    try:
        return _Mic()
    except (OSError, ImportError, RuntimeError, ValueError):
        return None


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return -1.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = sum(a * a for a in left) ** 0.5
    norm_right = sum(b * b for b in right) ** 0.5
    if norm_left == 0 or norm_right == 0:
        return -1.0
    return dot / (norm_left * norm_right)


def _pairs_ok(chosen: list[int], cos: list[list[float]]) -> bool:
    for pos, left in enumerate(chosen):
        for right in chosen[:pos]:
            if cos[left][right] < SAME:
                return False
    return True


def _drop_until_one(cos: list[list[float]]) -> list[int]:
    chosen = list(range(len(cos)))
    while len(chosen) >= MIN_KEEP and not _pairs_ok(chosen, cos):
        worst = chosen[0]
        worst_hits = -1
        for left in chosen:
            hits = sum(1 for right in chosen if right != left and cos[left][right] < SAME)
            if hits > worst_hits:
                worst = left
                worst_hits = hits
        chosen.remove(worst)
    if len(chosen) >= MIN_KEEP and _pairs_ok(chosen, cos):
        return chosen
    return []
