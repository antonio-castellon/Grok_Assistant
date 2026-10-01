"""Score each listening engine on the saved phrases. The words are already known."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from grok_assistant.listening.enroll_audio import phrase_hit, read_wav
from grok_assistant.listening.listen import dictation_script
from grok_assistant.quiet import no_window


def score_person(book, name: str, ear: str, transcribe=None) -> tuple[int, int]:
    """How many saved phrases this engine heard. The result is stored on the person."""
    if transcribe is None and ear == "windows":
        return _score_windows(book, name)
    clips = book.raw_clips(name)
    hear = transcribe or (lambda kind, audio: _transcribe(kind, audio))
    hits = 0
    for clip in clips:
        audio = read_wav(book.raw_root() / clip["file"])
        text = hear(ear, audio) if audio is not None else ""
        if phrase_hit(clip["phrase"], text or ""):
            hits += 1
    total = len(clips)
    book.set_score(name, ear, hits, total)
    return hits, total


def _transcribe(ear: str, samples) -> str:
    try:
        from grok_assistant.listening.kroko_ear import STREAMING_KINDS
        from grok_assistant.listening.kroko_ear import transcribe_clip as stream_clip
        from grok_assistant.listening.offline_ear import OFFLINE_KINDS
        from grok_assistant.listening.offline_ear import transcribe_clip as offline_clip

        if ear in STREAMING_KINDS:
            return stream_clip(samples, ear)
        if ear in OFFLINE_KINDS:
            return offline_clip(ear, samples)
    except (OSError, RuntimeError, ValueError, ImportError):
        return ""
    return ""


def _score_windows(book, name: str) -> tuple[int, int]:
    clips = book.raw_clips(name)
    heard: dict[str, str] = {}
    if clips:
        folder = (book.raw_root() / clips[0]["file"]).parent
        heard = transcribe_windows(folder)
    hits = 0
    for clip in clips:
        text = heard.get(Path(clip["file"]).name, "")
        if phrase_hit(clip["phrase"], text):
            hits += 1
    total = len(clips)
    book.set_score(name, "windows", hits, total)
    return hits, total


def transcribe_windows(folder: Path) -> dict[str, str]:
    """One Windows pass over a folder of wavs. The key is the file name."""
    script = dictation_script()
    if os.name != "nt" or not script.exists() or not folder.is_dir():
        return {}
    try:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(script), "-ScoreDir", str(folder)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            **no_window(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    found: dict[str, str] = {}
    for line in (done.stdout or "").splitlines():
        if not line.startswith("LINE:"):
            continue
        body = line[5:]
        filename, _, text = body.partition("|")
        if filename:
            found[filename] = text.strip()
    return found
