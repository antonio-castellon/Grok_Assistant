"""Local sessions, speaker prints, and the agent book. None of this is uploaded by itself."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path


SHARED = "compartida"
DAY = 24 * 60 * 60


def _read(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    if not isinstance(data, dict):
        return fallback
    return data


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class Session:
    name: str
    created: float
    grok_id: str | None = None
    lines: list[dict] = field(default_factory=list)
    shared: bool = False

    def expired(self, now: float) -> bool:
        return self.shared and now - self.created >= DAY


class SessionStore:
    def __init__(self, path: Path):
        self.path = path
        self.sessions: dict[str, Session] = {}
        self.active = SHARED
        self._load()

    def _load(self) -> None:
        data = _read(self.path, {})
        raw = data.get("sessions") or {}
        self.sessions = {}
        for name, item in raw.items():
            if not isinstance(item, dict):
                continue
            self.sessions[name] = Session(
                name=name,
                created=float(item.get("created") or time.time()),
                grok_id=item.get("grok_id"),
                lines=list(item.get("lines") or []),
                shared=bool(item.get("shared")),
            )
        if SHARED not in self.sessions:
            self.sessions[SHARED] = Session(SHARED, time.time(), shared=True)
        self.active = data.get("active") or SHARED
        if self.active not in self.sessions:
            self.active = SHARED
        self.roll(time.time())

    def save(self) -> None:
        _write(self.path, {
            "active": self.active,
            "sessions": {
                name: {
                    "created": item.created,
                    "grok_id": item.grok_id,
                    "lines": item.lines[-400:],
                    "shared": item.shared,
                }
                for name, item in self.sessions.items()
            },
        })

    def roll(self, now: float) -> None:
        current = self.sessions.get(SHARED)
        if current and current.expired(now):
            self.sessions[SHARED] = Session(SHARED, now, shared=True)
            if self.active == SHARED:
                self.active = SHARED
            self.save()

    def current(self) -> Session:
        return self.sessions[self.active]

    def names(self) -> list[str]:
        ordered = [SHARED] + sorted(name for name in self.sessions if name != SHARED)
        return ordered

    def resolve(self, name: str) -> str | None:
        key = name.casefold()
        for existing in self.sessions:
            if existing.casefold() == key:
                return existing
        return None

    def append(self, record: dict) -> None:
        self.sessions[self.active].lines.append(record)
        self.save()

    def create(self, name: str) -> str | None:
        clean = " ".join(name.split())
        if not clean or clean.casefold() == SHARED:
            return None
        found = self.resolve(clean)
        if found:
            return found
        self.sessions[clean] = Session(clean, time.time(), shared=False)
        self.save()
        return clean

    def open(self, name: str) -> str | None:
        found = self.resolve(name)
        if not found:
            return None
        self.active = found
        self.save()
        return found

    def close_to_shared(self) -> None:
        self.roll(time.time())
        self.active = SHARED
        self.save()

    def delete(self, name: str) -> str | None:
        found = self.resolve(name)
        if not found or found == SHARED:
            return None
        del self.sessions[found]
        if self.active == found:
            self.active = SHARED
        self.save()
        return found

    def grok_id(self, mint: bool) -> str | None:
        item = self.current()
        if item.grok_id:
            return item.grok_id
        if not mint:
            return None
        item.grok_id = str(uuid.uuid4())
        self.save()
        return item.grok_id

    def reset_grok_id(self) -> str:
        item = self.current()
        item.grok_id = str(uuid.uuid4())
        self.save()
        return item.grok_id


class SpeakerBook:
    def __init__(self, path: Path):
        self.path = path
        self.locked: str | None = None
        self.people: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        data = _read(self.path, {})
        self.locked = data.get("locked")
        people = data.get("people") or {}
        self.people = people if isinstance(people, dict) else {}
        if self.locked and self.locked not in self.people:
            self.locked = None

    def save(self) -> None:
        _write(self.path, {"locked": self.locked, "people": self.people})

    def names(self) -> list[str]:
        return sorted(self.people)

    def has_prints(self) -> bool:
        for person in self.people.values():
            if person.get("prints"):
                return True
        return False

    def resolve(self, name: str) -> str | None:
        key = " ".join(name.split()).casefold()
        for existing in self.people:
            if existing.casefold() == key:
                return existing
        return None

    def greeting(self, name: str, now: float, extra: str) -> str:
        person = self.people.get(name) or {}
        last = person.get("last")
        if last is None:
            gap = None
        else:
            gap = now - float(last)
        if gap is not None and gap < 3600:
            said = "Dime."
        elif gap is not None and gap < 5 * 3600:
            said = f"Hola de nuevo, {name}."
        else:
            said = f"Hola, {name}. {extra}".strip()
        person = self.people.setdefault(name, {"prints": [], "last": None})
        person["last"] = now
        self.save()
        return said

    def add(self, name: str, prints: list[list[float]] | None, lock: bool) -> str:
        clean = " ".join(name.split())
        found = self.resolve(clean)
        key = found or clean
        self.people[key] = {"prints": prints or [], "last": time.time()}
        if lock and prints:
            self.locked = key
        self.save()
        return key

    def delete(self, name: str) -> str | None:
        found = self.resolve(name)
        if not found:
            return None
        del self.people[found]
        if self.locked == found:
            self.locked = None
        self.save()
        return found

    def closest(self, vector: list[float] | None, threshold: float = 0.55) -> str | None:
        if not vector:
            return None
        best_name = None
        best = threshold
        for name, person in self.people.items():
            for print_ in person.get("prints") or []:
                score = _cosine(vector, print_)
                if score > best:
                    best = score
                    best_name = name
        return best_name


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return -1.0
    return dot / (na * nb)


@dataclass
class AgentRecord:
    name: str
    path: Path
    grok_id: str | None = None


class AgentBook:
    """Definitions live in the Grok account folder. Local sessions do not."""

    def __init__(self, definitions: Path, state_path: Path):
        self.definitions = definitions
        self.state_path = state_path
        self.active: str | None = None
        self._ids: dict[str, str] = {}
        self._load_state()

    def _load_state(self) -> None:
        data = _read(self.state_path, {})
        self.active = data.get("active")
        ids = data.get("ids") or {}
        self._ids = {str(k): str(v) for k, v in ids.items()} if isinstance(ids, dict) else {}

    def save(self) -> None:
        _write(self.state_path, {"active": self.active, "ids": self._ids})

    def _title(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            head = text[3:end] if end != -1 else ""
            for line in head.splitlines():
                if line.startswith("name:"):
                    return line.split(":", 1)[1].strip().strip('"')
        return path.stem

    def list(self) -> list[AgentRecord]:
        if not self.definitions.exists():
            return []
        found = []
        for path in sorted(self.definitions.glob("*.md")):
            try:
                name = self._title(path)
            except OSError:
                continue
            found.append(AgentRecord(name, path, self._ids.get(name)))
        return found

    def resolve(self, name: str) -> AgentRecord | None:
        key = " ".join(name.split()).casefold()
        for record in self.list():
            if record.name.casefold() == key or record.path.stem.casefold() == key:
                return record
        return None

    def grok_id(self, name: str, mint: bool) -> str | None:
        if name in self._ids:
            return self._ids[name]
        if not mint:
            return None
        self._ids[name] = str(uuid.uuid4())
        self.save()
        return self._ids[name]

    def reset_grok_id(self, name: str) -> str:
        self._ids[name] = str(uuid.uuid4())
        self.save()
        return self._ids[name]

    def create(self, name: str) -> AgentRecord:
        clean = " ".join(name.split())
        slug = "-".join(part for part in "".join(
            ch.lower() if ch.isalnum() else " " for ch in clean
        ).split()) or "agente"
        self.definitions.mkdir(parents=True, exist_ok=True)
        path = self.definitions / f"{slug}.md"
        n = 2
        while path.exists():
            path = self.definitions / f"{slug}-{n}.md"
            n += 1
        body = (
            f"---\nname: {clean}\n"
            "description: Agente personal del asistente de voz. Recuerda fechas, sitios y listas.\n"
            "prompt_mode: full\nmodel: grok-4.7\npermission_mode: default\nagents_md: false\n"
            "---\n\n"
            "Eres un agente personal. Hablas español, en frases cortas, sin markdown, "
            "sin listas y sin emoji. Recuerdas fechas, lugares y listas. Puedes buscar "
            "en internet. No inventes que has tocado el ordenador de la persona. "
            "Si no estás seguro, dilo en una frase.\n"
        )
        path.write_text(body, encoding="utf-8")
        return AgentRecord(clean, path, None)

    def open(self, name: str) -> AgentRecord | None:
        record = self.resolve(name)
        if not record:
            return None
        self.active = record.name
        self.save()
        return record

    def close(self) -> None:
        self.active = None
        self.save()
