"""Offline greetings and waiting lines. Nothing here is fetched."""

from __future__ import annotations

import json

from grok_assistant.paths import lines_dir

KINDS = ("joke", "saying", "anecdote", "fact")
THEMES = ("science", "history", "politics", "sports", "nature", "culture")

_cache: dict[str, list[dict]] = {}


def normalize_choice(raw, allowed: tuple[str, ...]) -> list[str]:
    """Known names, in catalog order. An empty or broken choice means all of them."""
    if not isinstance(raw, list):
        return list(allowed)
    picked = {str(item) for item in raw}
    chosen = [name for name in allowed if name in picked]
    return chosen or list(allowed)


def apply_choice(selected, allowed: tuple[str, ...], item: str, enabled: bool, *, mix: bool = False) -> list[str]:
    """Turn one checkbox on or off. The last remaining choice stays on."""
    if mix:
        return list(allowed) if enabled else [allowed[0]]
    current = normalize_choice(selected, allowed)
    if item not in allowed:
        return current
    if enabled:
        if item not in current:
            current = list(current) + [item]
    elif item in current and len(current) > 1:
        current = [name for name in current if name != item]
    return [name for name in allowed if name in current]


def catalog(language: str) -> list[dict]:
    code = language if language in {"es", "en", "fr", "de"} else "es"
    if code not in _cache:
        _cache[code] = _read(code)
    return _cache[code]


def pool(language: str, kinds, themes) -> list[str]:
    """Lines for the selected kinds and themes, in file order."""
    use_kinds = set(normalize_choice(kinds, KINDS))
    use_themes = set(normalize_choice(themes, THEMES))
    rows = catalog(language)
    found = [row["text"] for row in rows if row["kind"] in use_kinds and row["theme"] in use_themes]
    if found:
        return found
    return [row["text"] for row in rows]


def _read(code: str) -> list[dict]:
    path = lines_dir() / "banter.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    rows = []
    for theme in THEMES:
        kinds = data.get(theme)
        if not isinstance(kinds, dict):
            continue
        for kind in KINDS:
            packs = kinds.get(kind)
            if not isinstance(packs, dict):
                continue
            lines = packs.get(code)
            if not isinstance(lines, list):
                continue
            for text in lines:
                line = " ".join(str(text).split())
                if line:
                    rows.append({"theme": theme, "kind": kind, "text": line})
    return rows
