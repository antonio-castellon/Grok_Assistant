"""Local orders. One wrong character still matches. Two do not. Nothing here calls the network."""

from __future__ import annotations

import re
from dataclasses import dataclass

from grok_assistant.textutil import edit_distance, loose, normalize, tokenize


def _list(key: str, fallback):
    from grok_assistant.i18n import command_list

    found = command_list(key)
    if not found:
        return list(fallback)
    return found


def _groups(key: str, fallback: dict[str, set[str]]) -> dict[str, set[str]]:
    from grok_assistant.i18n import command_map

    found = command_map(key)
    return found or fallback


def _fixed_rows():
    from grok_assistant.i18n import fixed_commands

    found = fixed_commands()
    return found or list(_FIXED)

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
    "poner una cancion de",
    "poner la cancion",
    "poner una cancion",
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
    ("cambiar nombre", ("cambiar nombre", "cambia el nombre", "cambiar el nombre"), False, False),
    ("lista las personas", ("lista las personas", "listar las personas", "lista personas"), False, True),
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
    return len(norms) == 1 and norms[0] in set(_list("yes", _YES))


def wake_targets(name: str = "grok", extras: tuple[str, ...] | list[str] = ()) -> list[str]:
    called = normalize(name) or "grok"
    patterns = _list("wake_patterns", ())
    if patterns:
        targets = [normalize(pattern.format(name=called)) for pattern in patterns]
        targets.append(called)
    else:
        targets = [
            f"hola {called}",
            f"ok {called}",
            f"despierta {called}",
            f"estas ahi {called}",
            f"{called} estas ahi",
            called,
        ]
    if called == "grok":
        targets.extend(_list("wake_aliases", WAKES))
    for extra in extras:
        heard = normalize(extra)
        if heard and heard not in targets:
            targets.append(heard)
    return targets


def is_exact_wake(norms: list[str], name: str = "grok", extras: tuple[str, ...] | list[str] = ()) -> bool:
    """The words match a greeting exactly. A near miss is left for the text identifier."""
    if not norms:
        return False
    blob = " ".join(norms)
    for target in wake_targets(name, extras):
        size = len(target.split())
        if blob == target or " ".join(norms[:size]) == target:
            return True
    return False


def is_wake(norms: list[str], name: str = "grok", extras: tuple[str, ...] | list[str] = ()) -> bool:
    return wake_split(norms, name, extras) is not None


def wake_split(norms: list[str], name: str = "grok", extras: tuple[str, ...] | list[str] = ()) -> list[str] | None:
    """Words after a loose greeting. [] is a greeting alone. None is not a greeting."""
    if not norms:
        return None
    best = 0
    matched = False
    blob = " ".join(norms)
    for target in wake_targets(name, extras):
        size = len(target.split())
        if len(norms) >= size and loose(" ".join(norms[:size]), target):
            matched = True
            if size > best:
                best = size
        elif loose(blob, target):
            matched = True
            if len(norms) > best:
                best = len(norms)
    if not matched:
        return None
    return norms[best:]


def near_greeting(text: str, name: str = "grok") -> str | None:
    """A short greeting whose name is a bad hearing of the wake name.

    One changed letter is already a wake. This catches a bigger slip,
    such as «miren» for Miguel. A bare word is not a greeting.
    Returns the cleaned greeting, for example «hola Miguel».
    """
    norms = words_norm(text)
    if not norms or len(norms) > 4 or is_wake(norms, name):
        return None
    called = normalize(name) or "grok"
    shown = " ".join((name or "").split()) or called
    limit = max(2, (len(called) + 1) // 2)
    for target in wake_targets(name):
        parts = target.split()
        if called not in parts or len(parts) < 2 or len(parts) != len(norms):
            continue
        if not _slip_matches(norms, parts, called, limit):
            continue
        return " ".join(shown if piece == called else piece for piece in parts)
    return None


def _slip_matches(norms: list[str], parts: list[str], called: str, limit: int) -> bool:
    for heard, piece in zip(norms, parts):
        if piece == called:
            if not heard or heard[0] != called[0]:
                return False
            if edit_distance(heard, called, limit) > limit:
                return False
            continue
        if not loose(heard, piece):
            return False
    return True


def endpoint_quiet(text: str, wake_name: str = "grok") -> float:
    """A bare greeting stays open for two seconds so the question can follow."""
    rest = wake_split(words_norm(text), wake_name)
    if rest == []:
        return 2.0
    return 0.7


_PRESENCE = (
    "me escuchas",
    "me oyes",
    "me oye",
    "estas ahi",
    "estas alli",
    "me estas oyendo",
)


def _presence_phrases() -> tuple[str, ...]:
    found = _list("presence", _PRESENCE)
    return tuple(found)


def without_wake(norms: list[str], name: str = "grok") -> list[str]:
    rest = wake_split(norms, name)
    if rest is None:
        return list(norms)
    return rest


def is_presence(norms: list[str], name: str = "grok") -> bool:
    rest = without_wake(norms, name)
    if not rest:
        return False
    blob = " ".join(rest)
    return any(blob == item or loose(blob, item) for item in _presence_phrases())


def wake_is_presence(norms: list[str], name: str = "grok") -> bool:
    called = normalize(name) or "grok"
    head = " ".join(norms[:4])
    return loose(head, f"estas ahi {called}") or loose(head, f"{called} estas ahi") or loose(" ".join(norms), f"estas ahi {called}")


def blank_phrase(text: str) -> bool:
    return not any(char.isalnum() for char in (text or ""))


def noise_phrase(text: str) -> bool:
    """Whisper marks like [MUSIC] or [BLANK_AUDIO]. They are not a question."""
    raw = (text or "").strip()
    if "[" not in raw or "]" not in raw:
        return False
    rest = re.sub(r"\[[^\[\]]*\]", " ", raw)
    return blank_phrase(rest)


def thin_phrase(text: str) -> bool:
    """Silence, or one short word. Outside a conversation this never leaves the house."""
    if blank_phrase(text):
        return True
    words = [word for word in (text or "").split() if any(char.isalnum() for char in word)]
    return len(words) == 1 and len(words[0]) <= 4


def is_test_word(norms: list[str]) -> bool:
    if len(norms) != 1:
        return False
    return any(loose(norms[0], word) for word in _list("test", ("prueba", "test")))


def strip_comando(norms: list[str]) -> tuple[bool, list[str]]:
    words = _list("comando", ("comando",))
    if norms and any(loose(norms[0], word) and abs(len(norms[0]) - len(word)) <= 1 for word in words):
        return True, norms[1:]
    return False, norms


def closer(norms: list[str]) -> str | None:
    """Return adios, denada, or vale when the talk should end locally. None keeps it open."""
    if not norms or len(norms) > 8:
        return None
    thanks = set(_list("thanks", ("gracias",)))
    if any(word in thanks for word in norms):
        return "denada"
    blob = " ".join(norms)
    ok_words = set(_list("ok_words", ("ok", "okay", "okey")))
    if len(norms) <= 3 and (norms[0] in ok_words or loose(norms[0], "ok")):
        return "vale"
    close_verbs = set(_list("close_verbs", _CLOSE_VERBS))
    if len(norms) <= 3 and norms[0] in close_verbs:
        return "adios"
    bye_words = set(_list("bye_words", ("adios", "chao", "chau")))
    if norms[0] in bye_words and len(norms) <= 3:
        return "adios"
    adios = _list("adios", _ADIOS)
    if blob in adios or any(loose(blob, item) for item in adios):
        return "adios"
    nothing = _list("nothing", _NOTHING)
    if blob in nothing or any(loose(blob, item) for item in nothing):
        return "vale"
    conversation = set(_list("conversation_word", ("conversacion",)))
    if any(word in conversation for word in norms) and _token_in(norms, close_verbs):
        return "adios"
    if any(word in thanks for word in norms):
        return "denada"
    if norms == ["vale"]:
        return "vale"
    return None


def song_of(pairs: list[tuple[str, str]]) -> Song:
    if not pairs:
        return Song()
    norms = [norm for _, norm in pairs]
    raws = [raw for raw, _ in pairs]
    for prefix in _list("song_prefixes", SONG_PREFIXES):
        parts = prefix.split()
        size = len(parts)
        if len(norms) < size:
            continue
        if len(norms) == size and edit_distance(" ".join(norms), prefix, 1) <= 1:
            return Song(matched=True)
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
    if any(word in set(_list("agent_words", ("agente", "agentes"))) for word in norms):
        hit = _match_agent(pairs)
        if hit:
            return hit
    if any(word in set(_list("session_words", ("sesion", "sesiones"))) for word in norms):
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
    while kept and normalize(kept[0]) in set(_list("leading", _LEADING)):
        kept.pop(0)
    return " ".join(kept).strip()


def _match_session(pairs: list[tuple[str, str]]) -> Hit | None:
    norms = [norm for _, norm in pairs]
    kind = _first_kind(norms, _groups("session_groups", _SESSION_GROUPS), set(_list("session_words", ("sesion", "sesiones"))) | {"de", "del", "la", "el"})
    if kind == "listar":
        return Hit("listar sesiones")
    if kind == "cerrar":
        return Hit("cerrar sesion")
    name = _leftover(pairs, set(_groups("session_groups", _SESSION_GROUPS).get(kind, ())), set(_list("session_words", ("sesion", "sesiones"))) | set(_list("comando", ("comando",))))
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
    kind = _first_kind(norms, _groups("agent_groups", _AGENT_GROUPS), set(_list("agent_words", ("agente", "agentes"))) | {"de", "del", "la", "el"})
    if kind == "listar":
        return Hit("listar agentes")
    if kind == "cerrar":
        return Hit("cerrar agente")
    name = _leftover(pairs, set(_groups("agent_groups", _AGENT_GROUPS).get(kind, ())), set(_list("agent_words", ("agente", "agentes"))) | set(_list("comando", ("comando",))))
    if kind == "crear":
        return Hit("crear agente", name, admin=True)
    if kind == "abrir":
        return Hit("abrir agente", name)
    return None


def _match_fixed(blob: str) -> Hit | None:
    best: Hit | None = None
    best_d = 2
    tie = False
    for strict, phrases, confirm, admin in _fixed_rows():
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


_EARS = ("teclado", "windows", "kroko", "zipfr", "zipen", "whisper", "base", "small", "canary", "cohere")


def _ear_name(norms: list[str]) -> str | None:
    ears = _list("ears", _EARS)
    for word in norms:
        hits = [name for name in ears if loose(word, name) or loose(word, name.split()[0])]
        if len(hits) == 1:
            return hits[0]
    return None


def _match_prefix(pairs: list[tuple[str, str]]) -> Hit | None:
    norms = [norm for _, norm in pairs]
    raws = [raw for raw, _ in pairs]
    if not norms:
        return None
    head = norms[0]
    rest = " ".join(raws[1:]).strip()
    if any(loose(head, word) for word in _list("voice_word", ("voz",))) and len(norms) == 2 and norms[1].isdigit():
        return Hit("voz", norms[1])
    if any(loose(head, word) for word in _list("recognizer_word", ("reconocedor",))):
        ear = _ear_name(norms[1:])
        if ear:
            return Hit("reconocedor", ear)
    if any(loose(head, word) for word in _list("delete_words", ("borra", "borrar"))) and "sesion" not in norms and "agente" not in norms:
        if rest:
            return Hit("borra", rest, confirm=True, admin=True)
    return None


def display_order(hit: Hit) -> str:
    if hit.arg:
        return f"{hit.strict} {hit.arg}".strip()
    return hit.strict


def normalize_name(name: str) -> str:
    return normalize(name)
