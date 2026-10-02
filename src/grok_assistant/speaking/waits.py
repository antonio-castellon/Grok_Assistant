"""The short line while Grok is searching. Nothing here is fetched."""

from __future__ import annotations

import json

from grok_assistant.paths import lines_dir
from grok_assistant.speaking.banter import normalize_choice

STYLES = ("plain", "witty", "dry", "tech", "cheeky")
RARE = "cheeky"
RARE_EVERY = 8

_cache: dict[str, list[dict]] = {}


def catalog(language: str) -> list[dict]:
    code = language if language in {"es", "en", "fr", "de"} else "es"
    if code not in _cache:
        _cache[code] = _read(code)
    return _cache[code]


def buckets(language: str, styles) -> tuple[list[str], list[str]]:
    """Ordinary lines, then the cheeky ones. Cheeky stays a separate bucket."""
    chosen = set(normalize_choice(styles, STYLES))
    main: list[str] = []
    rare: list[str] = []
    for row in catalog(language):
        if row["style"] not in chosen:
            continue
        if row["style"] == RARE:
            rare.append(row["text"])
        else:
            main.append(row["text"])
    return main, rare


def pick(language: str, styles, index: int, previous: str = "") -> tuple[str, int]:
    """Next waiting line. With the other styles on, a cheeky line is one in eight."""
    index = max(0, int(index))
    main, rare = buckets(language, styles)
    if not main:
        bucket = rare or ["Un momento."]
        cursor = index % len(bucket)
    elif rare and index % RARE_EVERY == RARE_EVERY - 1:
        bucket = rare
        cursor = (index // RARE_EVERY) % len(bucket)
    else:
        bucket = main
        cursor = index % len(bucket)
    line = bucket[cursor]
    if line == previous and len(bucket) > 1:
        line = bucket[(cursor + 1) % len(bucket)]
    return line, index + 1


def _read(code: str) -> list[dict]:
    path = lines_dir() / "waits.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    rows = []
    for style in STYLES:
        packs = data.get(style)
        if not isinstance(packs, dict):
            continue
        lines = packs.get(code)
        if not isinstance(lines, list):
            continue
        for text in lines:
            line = " ".join(str(text).split())
            if line:
                rows.append({"style": style, "text": line})
    return rows
