"""Local orders. One wrong character still matches. Two do not. Nothing here calls the network."""

from __future__ import annotations

from dataclasses import dataclass

from grok_assistant.textutil import edit_distance, loose, normalize, tokenize

WAKES = (
    "hola grok",
    "ok grok",
    "despierta grok",
    "estas ahi grok",
    "grok estas ahi",
    "pola grove",
    "hola grop",
)

SONG_PREFIXES = (
    "pon la cancion de",
    "pon una cancion de",
    "ponme la cancion",
    "poner la cancion",
    "pon la cancion",
    "pon una cancion",
    "poner cancion",
    "pon cancion",
)

_YES = {"si", "vale", "yes"}
_CLOSE_VERBS = ("cierra", "cerrar", "acaba", "acabar", "termina", "terminar", "salir", "corta", "cortar")
_ADIOS = {
    "adios",
    "hasta luego",
    "chao",
    "chau",
    "cuando quieras seguimos",
    "ya esta",
    "nada mas",
    "basta",
    "dejalo",
    "vale ya esta",
}
_NOTHING = {
    "no necesito nada",
    "no quiero nada",
    "ya no necesito nada",
    "no me hace falta nada",
    "no necesito nada mas",
}

# strict, phrases, confirm, admin
_FIXED: tuple[tuple[str, tuple[str, ...], bool, bool], ...] = (
    ("subir volumen", ("subir volumen", "sube volumen", "sube el volumen", "subir el volumen"), False, False),
    ("bajar volumen", ("bajar volumen", "baja volumen", "baja el volumen", "bajar el volumen"), False, False),
    ("otra voz", ("otra voz", "siguiente voz"), False, False),
    ("otro reconocedor", ("otro reconocedor", "siguiente reconocedor"), False, False),
    ("pausa musica", ("pausa musica", "pausar musica", "pausa la musica"), False, False),
    ("seguir musica", ("seguir musica", "continua la musica", "reanuda la musica", "sigue la musica"), False, False),
    ("para la musica", ("para la musica", "parar la musica", "para musica", "detener la musica"), False, False),
    ("listar sesiones", ("listar sesiones", "lista sesiones", "lista las sesiones"), False, False),
    ("cerrar sesion", ("cerrar sesion", "cierra sesion", "cierra la sesion"), False, False),
    ("listar agentes", ("listar agentes", "lista agentes", "lista los agentes"), False, False),
    ("cerrar agente", ("cerrar agente", "cierra agente", "cierra el agente"), False, False),
    ("ayuda", ("ayuda", "help"), False, False),
    ("prueba", ("prueba", "test"), False, False),
    ("identifica mi voz", ("identifica mi voz",), False, False),
    ("lista las personas", ("lista las personas", "listar las personas", "lista personas"), False, True),
    ("apagar", ("apagar", "apaga", "apaga el dispositivo", "apagar el dispositivo"), True, False),
    ("modo administrador", ("modo administrador", "administrador"), False, True),
)

_LEADING = {"de", "del", "la", "el", "una", "un", "mi", "por", "favor", "quiero", "porfa", "con"}
_AGENT_VERBS_OPEN = {"abrir", "abre", "hablar", "habla", "cargar", "carga", "iniciar", "inicia"}
_SESSION_GROUPS = {
    "listar": {"listar", "lista"},
    "cerrar": {"cerrar", "cierra"},
    "crear": {"crear", "crea"},
    "abrir": {"abrir", "abre"},
    "borrar": {"borrar", "borra", "eliminar", "elimina"},
}
_AGENT_GROUPS = {
    "listar": {"listar", "lista"},
    "cerrar": {"cerrar", "cierra"},
    "crear": {"crear", "crea"},
    "abrir": set(_AGENT_VERBS_OPEN),
}


@dataclass(frozen=True)
class Hit:
    strict: str
    arg: str = ""
    confirm: bool = False
    admin: bool = False


@dataclass(frozen=True)
class Song:
    title: str = ""
    matched: bool = False
    too_long: bool = False


def words_norm(text: str) -> list[str]:
    return [norm for _, norm in tokenize(text)]


def is_yes(norms: list[str]) -> bool:
    return len(norms) == 1 and norms[0] in _YES


def is_wake(norms: list[str]) -> bool:
    if norms == ["hola"]:
        return True
    blob = " ".join(norms)
    for target in WAKES:
        size = len(target.split())
        if len(norms) >= size and loose(" ".join(norms[:size]), target):
            return True
        if loose(blob, target):
            return True
    return False


def wake_is_presence(norms: list[str]) -> bool:
    head = " ".join(norms[:3])
    return loose(head, "estas ahi grok") or loose(head, "grok estas ahi") or loose(" ".join(norms), "estas ahi grok")


def is_test_word(norms: list[str]) -> bool:
    return len(norms) == 1 and (loose(norms[0], "prueba") or loose(norms[0], "test"))


def strip_comando(norms: list[str]) -> tuple[bool, list[str]]:
    if norms and loose(norms[0], "comando") and abs(len(norms[0]) - len("comando")) <= 1:
        return True, norms[1:]
    return False, norms


def closer(norms: list[str]) -> str | None:
    """Return adios, denada, or vale when the talk should end locally. None keeps it open."""
    if not norms or len(norms) > 8:
        return None
    if "gracias" in norms:
        return "denada"
    blob = " ".join(norms)
    if norms[0] in {"adios", "chao", "chau"} and len(norms) <= 3:
        return "adios"
    if blob in _ADIOS or any(loose(blob, item) for item in _ADIOS):
        return "adios"
    if blob in _NOTHING or any(loose(blob, item) for item in _NOTHING):
        return "vale"
    if "conversacion" in norms and _token_in(norms, _CLOSE_VERBS):
        return "adios"
    if "gracias" in norms:
        return "denada"
    if norms == ["vale"]:
        return "vale"
    return None


def song_of(pairs: list[tuple[str, str]]) -> Song:
    if not pairs:
        return Song()
    norms = [norm for _, norm in pairs]
    raws = [raw for raw, _ in pairs]
    for prefix in SONG_PREFIXES:
        parts = prefix.split()
        size = len(parts)
        if len(norms) <= size:
            continue
        if edit_distance(" ".join(norms[:size]), prefix, 1) <= 1:
            if len(norms) > 16:
                return Song(matched=True, too_long=True)
            return Song(title=" ".join(raws[size:]), matched=True)
    return Song()


def parse_order(pairs: list[tuple[str, str]]) -> Hit | None:
    """Parse the words after 'comando'. Pairs are (raw, normalized)."""
    if not pairs:
        return None
    norms = [norm for _, norm in pairs]
    if "agente" in norms or "agentes" in norms:
        hit = _match_agent(pairs)
        if hit:
            return hit
    if "sesion" in norms or "sesiones" in norms:
        hit = _match_session(pairs)
        if hit:
            return hit
    song = song_of(pairs)
    if song.title:
        return Hit("pon cancion", song.title)
    fixed = _match_fixed(" ".join(norms))
    if fixed:
        return fixed
    return _match_prefix(pairs)


def canonicalize(text: str) -> Hit | None:
    """Map an interpreter line back onto a strict order. Exact, then one character."""
    pairs = tokenize(text)
    if not pairs:
        return None
    return parse_order(pairs)


def _token_in(norms: list[str], options: tuple[str, ...] | set[str]) -> bool:
    for word in norms:
        for option in options:
            if abs(len(word) - len(option)) <= 1 and edit_distance(word, option, 1) <= 1:
                return True
    return False


def _first_kind(norms: list[str], groups: dict[str, set[str]], skip: set[str]) -> str | None:
    for word in norms:
        if word in skip:
            continue
        found = [name for name, options in groups.items() if _token_in([word], options)]
        if len(found) == 1:
            return found[0]
    return None


def _leftover(pairs: list[tuple[str, str]], verbs: set[str], keywords: set[str]) -> str:
    kept: list[str] = []
    for raw, norm in pairs:
        if norm in keywords or _token_in([norm], verbs):
            continue
        kept.append(raw)
    while kept and normalize(kept[0]) in _LEADING:
        kept.pop(0)
    return " ".join(kept).strip()


def _match_session(pairs: list[tuple[str, str]]) -> Hit | None:
    norms = [norm for _, norm in pairs]
    kind = _first_kind(norms, _SESSION_GROUPS, {"sesion", "sesiones", "de", "del", "la", "el"})
    if kind == "listar":
        return Hit("listar sesiones")
    if kind == "cerrar":
        return Hit("cerrar sesion")
    name = _leftover(pairs, set(_SESSION_GROUPS.get(kind, ())), {"sesion", "sesiones", "comando"})
    if kind == "crear":
        return Hit("crear sesion", name, confirm=True)
    if kind == "abrir":
        return Hit("abrir sesion", name)
    if kind == "borrar":
        return Hit("borrar sesion", name, confirm=True)
    return None


def _match_agent(pairs: list[tuple[str, str]]) -> Hit | None:
    norms = [norm for _, norm in pairs]
    if "conversacion" in norms:
        return None
    kind = _first_kind(norms, _AGENT_GROUPS, {"agente", "agentes", "de", "del", "la", "el"})
    if kind == "listar":
        return Hit("listar agentes")
    if kind == "cerrar":
        return Hit("cerrar agente")
    name = _leftover(pairs, set(_AGENT_GROUPS.get(kind, ())), {"agente", "agentes", "comando"})
    if kind == "crear":
        return Hit("crear agente", name, admin=True)
    if kind == "abrir":
        return Hit("abrir agente", name)
    return None


def _match_fixed(blob: str) -> Hit | None:
    best: Hit | None = None
    best_d = 2
    tie = False
    for strict, phrases, confirm, admin in _FIXED:
        for phrase in phrases:
            dist = edit_distance(blob, phrase, 1)
            if dist < best_d:
                best_d = dist
                best = Hit(strict, confirm=confirm, admin=admin)
                tie = False
            elif dist == best_d and best is not None and best.strict != strict:
                tie = True
    if best_d <= 1 and best is not None and not tie:
        return best
    return None


def _match_prefix(pairs: list[tuple[str, str]]) -> Hit | None:
    norms = [norm for _, norm in pairs]
    raws = [raw for raw, _ in pairs]
    if not norms:
        return None
    head = norms[0]
    rest = " ".join(raws[1:]).strip()
    if loose(head, "voz") and len(norms) == 2 and norms[1].isdigit():
        return Hit("voz", norms[1])
    if loose(head, "reconocedor") and len(norms) == 2 and norms[1] in {"kroko", "whisper", "base", "canary"}:
        return Hit("reconocedor", norms[1])
    if loose(head, "borra") or (loose(head, "borrar") and "sesion" not in norms and "agente" not in norms):
        if rest:
            return Hit("borra", rest, confirm=True, admin=True)
    return None


def display_order(hit: Hit) -> str:
    if hit.arg:
        return f"{hit.strict} {hit.arg}".strip()
    return hit.strict


def normalize_name(name: str) -> str:
    return normalize(name)
