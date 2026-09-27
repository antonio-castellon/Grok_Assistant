"""Plain Spanish text helpers. Matching is accent-insensitive and local."""

from __future__ import annotations

import re
import unicodedata

_EDGE = re.compile(r"^[^\w]+|[^\w]+$", re.UNICODE)


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[tuple[str, str]]:
    """Return (raw, normalized) words, keeping the speaker's accents in raw."""
    pairs: list[tuple[str, str]] = []
    for chunk in text.split():
        raw = _EDGE.sub("", chunk)
        if not raw:
            continue
        norm = normalize(raw)
        if norm:
            pairs.append((raw, norm))
    return pairs


def edit_distance(a: str, b: str, limit: int = 1) -> int:
    """Levenshtein distance, or limit+1 once the distance is known to exceed it."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            best = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb))
            cur.append(best)
            if best < row_min:
                row_min = best
        if row_min > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def loose(a: str, b: str) -> bool:
    return edit_distance(a, b, 1) <= 1
