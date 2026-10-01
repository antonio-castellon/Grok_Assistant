"""Small helpers shared by the window pieces."""

from __future__ import annotations

from grok_assistant.listening.listen import EAR_LANG, with_accuracy
from grok_assistant.ui.theme import look

def _ui(key: str, fallback: str = "") -> str:
    from grok_assistant.i18n import text

    return text(key, fallback)

def detail_line(snap: dict) -> str:
    """Each current setting as a label and a value in brackets."""
    parts = (
        ("window.detail_model", "modelo", snap.get("model", "")),
        ("window.detail_effort", "esfuerzo", snap.get("effort", "")),
        ("window.detail_voice", "voz", snap.get("voice", "")),
        ("window.detail_ear", "oído", snap.get("recognizer", "")),
        ("window.detail_identifier", "identificador", snap.get("identifier", "")),
        ("window.detail_session", "sesión", snap.get("session", "")),
        ("window.detail_volume", "volumen", f"{snap.get('volume', '')}%"),
    )
    return "   ".join(f"{_ui(key, label)} [{value}]" for key, label, value in parts)


def _version_line() -> str:
    from grok_assistant import __version__

    return f"{__version__} · {_ui('about.channel', 'still a release candidate')}"

def _used(active: bool) -> str:
    if not active:
        return ""
    return "✓  "

def _agent_label(record) -> str:
    if getattr(record, "origin", "local") != "account":
        return record.name
    return f"{record.name} · {_ui('menu.agent_account', 'cuenta')}"

def _outside_clause(blocked: list[str], title, rated: dict[str, int]) -> str:
    """Why a higher score stayed off: that ear only hears one language."""
    groups: list[tuple[str, list[str]]] = []
    index: dict[str, int] = {}
    for ear in blocked:
        locked = EAR_LANG.get(ear, "")
        if locked not in index:
            index[locked] = len(groups)
            groups.append((locked, []))
        groups[index[locked]][1].append(ear)
    parts = []
    for locked, members in groups:
        names = ", ".join(with_accuracy(title(ear), rated[ear]) for ear in members)
        verb = "queda" if len(members) == 1 else "quedan"
        heard = _HEARS.get(locked, locked or "otro idioma")
        parts.append(f"{names} {verb} fuera: solo oye {heard}.")
    return " ".join(parts)
