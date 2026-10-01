"""Local sessions, speaker prints, and the agent book. None of this is uploaded by itself."""

from __future__ import annotations

import json
import shutil
import threading
import time
import unicodedata
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
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        data = _read(self.path, {})
        self.locked = data.get("locked")
        people = data.get("people") or {}
        self.people = people if isinstance(people, dict) else {}
        if self.locked and self.locked not in self.people:
            self.locked = None

    def save(self) -> None:
        with self._lock:
            _write(self.path, {"locked": self.locked, "people": self.people})

    def raw_root(self) -> Path:
        return self.path.parent / "raw"

    def names(self) -> list[str]:
        return sorted(self.people)

    def _book(self, person: dict) -> dict[str, list]:
        raw = person.get("prints")
        if isinstance(raw, list):
            return {"teclado": raw} if raw else {}
        if isinstance(raw, dict):
            return {str(ear): list(rows) for ear, rows in raw.items() if isinstance(rows, list) and rows}
        return {}

    def has_prints(self, ear: str | None = None) -> bool:
        """A saved print follows the person on every listener."""
        del ear
        return any(self._match_vectors(person) for person in self.people.values())

    def count(self, name: str, ear: str) -> int:
        found = self.resolve(name)
        if not found:
            return 0
        book = self._book(self.people[found])
        if book.get(ear):
            return len(book[ear])
        return len(book.get("campplus") or [])

    def take_count(self, name: str) -> int:
        found = self.resolve(name)
        if not found:
            return 0
        person = self.people[found]
        raw = person.get("raw") or []
        if isinstance(raw, list) and raw:
            return len(raw)
        book = self._book(person)
        if book.get("campplus"):
            return len(book["campplus"])
        if not book:
            return 0
        return max(len(rows) for rows in book.values())

    def _match_vectors(self, person: dict) -> list:
        book = self._book(person)
        if book.get("campplus"):
            return list(book["campplus"])
        rows: list = []
        for items in book.values():
            rows.extend(items)
        return rows

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

    def add(self, name: str, prints: list[list[float]] | None, lock: bool, ear: str = "teclado") -> str:
        """Store this listener's print. Other listeners keep their own."""
        clean = " ".join(name.split())
        found = self.resolve(clean)
        key = found or clean
        person = self.people.get(key) or {"prints": {}, "last": None}
        book = self._book(person)
        if prints:
            book[ear or "teclado"] = list(prints)
        person["prints"] = book
        person["last"] = time.time()
        self.people[key] = person
        if lock and prints:
            self.locked = key
        self.save()
        return key

    def store_recording(self, name: str, clips: list[dict], vectors: list, lock: bool) -> str:
        """Save the raw phrases and one voice print derived from them."""
        from grok_assistant.enroll_audio import write_wav

        clean = " ".join(name.split())
        found = self.resolve(clean)
        key = found or clean
        person = self.people.get(key) or {"prints": {}, "last": None}
        self._clear_raw(person)
        slug = self._fresh_slug(key)
        stored = []
        for index, clip in enumerate(clips):
            rel = f"{slug}/{index:02d}.wav"
            write_wav(self.raw_root() / rel, clip["samples"])
            stored.append({"phrase": clip["phrase"], "file": rel})
        person["prints"] = {"campplus": [list(map(float, vector)) for vector in vectors]}
        person["raw"] = stored
        person["scores"] = {}
        person["last"] = time.time()
        self.people[key] = person
        if lock and vectors:
            self.locked = key
        self.save()
        return key

    def raw_clips(self, name: str) -> list[dict]:
        found = self.resolve(name)
        if not found:
            return []
        raw = self.people[found].get("raw") or []
        if not isinstance(raw, list):
            return []
        return [
            item for item in raw
            if isinstance(item, dict) and item.get("phrase") and item.get("file")
        ]

    def score_of(self, name: str, ear: str) -> tuple[int, int] | None:
        found = self.resolve(name)
        if not found:
            return None
        row = (self.people[found].get("scores") or {}).get(ear)
        if not isinstance(row, dict) or "hits" not in row or "total" not in row:
            return None
        return int(row["hits"]), int(row["total"])

    def accuracies(self, name: str) -> dict[str, int]:
        """Hit rate of each scored listener, as a whole percent."""
        found = self.resolve(name)
        if not found:
            return {}
        scores = self.people[found].get("scores") or {}
        if not isinstance(scores, dict):
            return {}
        rated: dict[str, int] = {}
        for ear, row in scores.items():
            if not isinstance(row, dict) or "hits" not in row or "total" not in row:
                continue
            total = int(row["total"])
            if total <= 0:
                continue
            rated[str(ear)] = round(100 * int(row["hits"]) / total)
        return rated

    def combined_accuracies(self) -> dict[str, int]:
        """Hit rate of each listener, pooling every saved print."""
        hits: dict[str, int] = {}
        total: dict[str, int] = {}
        for person in self.people.values():
            scores = person.get("scores") or {}
            if not isinstance(scores, dict):
                continue
            for ear, row in scores.items():
                if not isinstance(row, dict) or "hits" not in row or "total" not in row:
                    continue
                count = int(row["total"])
                if count <= 0:
                    continue
                key = str(ear)
                hits[key] = hits.get(key, 0) + int(row["hits"])
                total[key] = total.get(key, 0) + count
        return {
            ear: round(100 * hits[ear] / total[ear])
            for ear in hits
            if total[ear] > 0
        }

    def set_score(self, name: str, ear: str, hits: int, total: int) -> None:
        found = self.resolve(name)
        if not found:
            return
        scores = self.people[found].setdefault("scores", {})
        if not isinstance(scores, dict):
            scores = {}
            self.people[found]["scores"] = scores
        scores[ear] = {"hits": int(hits), "total": int(total)}
        self.save()

    def pending_scores(self, ears: list[str]) -> list[tuple[str, str]]:
        pending = []
        for name, person in self.people.items():
            if not person.get("raw"):
                continue
            have = person.get("scores") or {}
            if not isinstance(have, dict):
                have = {}
            for ear in ears:
                if ear and ear != "teclado" and ear not in have:
                    pending.append((name, ear))
        return pending

    def rename(self, old: str, new: str) -> str | None:
        found = self.resolve(old)
        if not found:
            return None
        clean = " ".join(new.split())
        if not clean:
            return None
        other = self.resolve(clean)
        if other and other != found:
            return None
        person = self.people.pop(found)
        self._move_raw(person, clean)
        self.people[clean] = person
        if self.locked == found:
            self.locked = clean
        self.save()
        return clean

    def delete(self, name: str) -> str | None:
        found = self.resolve(name)
        if not found:
            return None
        self._clear_raw(self.people[found])
        del self.people[found]
        if self.locked == found:
            self.locked = None
        self.save()
        return found

    def closest(self, vector: list[float] | None, ear: str | None = None, threshold: float = 0.55) -> str | None:
        """The same person matches on every listener. One recording is one print."""
        del ear
        if not vector:
            return None
        best_name = None
        best = threshold
        for name, person in self.people.items():
            for print_ in self._match_vectors(person):
                score = _cosine(vector, print_)
                if score > best:
                    best = score
                    best_name = name
        return best_name

    def _fresh_slug(self, name: str) -> str:
        slug = _slug(name)
        root = self.raw_root()
        candidate = slug
        number = 2
        while (root / candidate).exists():
            candidate = f"{slug}-{number}"
            number += 1
        return candidate

    def _clear_raw(self, person: dict) -> None:
        raw = person.get("raw") or []
        if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
            return
        folder = (self.raw_root() / str(raw[0].get("file") or "")).parent
        root = self.raw_root().resolve()
        try:
            if folder.resolve().parent == root and folder.is_dir():
                shutil.rmtree(folder)
        except OSError:
            return

    def _move_raw(self, person: dict, name: str) -> None:
        raw = person.get("raw") or []
        if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
            return
        old = (self.raw_root() / str(raw[0].get("file") or "")).parent
        if not old.is_dir():
            return
        slug = self._fresh_slug(name)
        dest = self.raw_root() / slug
        try:
            old.rename(dest)
        except OSError:
            return
        person["raw"] = [
            {"phrase": item.get("phrase"), "file": f"{slug}/{Path(str(item.get('file'))).name}"}
            for item in raw
            if isinstance(item, dict)
        ]


def _slug(name: str) -> str:
    text = unicodedata.normalize("NFD", name)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "voz"


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return -1.0
    return dot / (na * nb)


def _agent_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in name.strip())
    cleaned = cleaned.strip(".-") or "agente"
    return f"{cleaned[:80]}.md"


@dataclass
class AgentRecord:
    name: str
    path: Path
    grok_id: str | None = None
    origin: str = "local"


class AgentBook:
    """Local files plus the agents the signed-in account publishes. Sessions stay local."""

    def __init__(self, definitions: Path, state_path: Path, account_dir: Path | None = None, account_cache: Path | None = None):
        self.definitions = definitions
        self.state_path = state_path
        self.account_dir = account_dir
        self.account_cache = account_cache
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
        """Local files win when the same name also exists on the account."""
        found: dict[str, AgentRecord] = {}
        for origin, folder in (
            ("account", self.account_dir),
            ("account", self.account_cache),
            ("local", self.definitions),
        ):
            for record in self._read_dir(folder, origin):
                found[record.name.casefold()] = record
        return sorted(found.values(), key=lambda record: record.name.casefold())

    def _read_dir(self, folder: Path | None, origin: str) -> list[AgentRecord]:
        if folder is None or not folder.exists():
            return []
        found = []
        for path in sorted(folder.glob("*.md")):
            try:
                name = self._title(path)
            except OSError:
                continue
            found.append(AgentRecord(name, path, self._ids.get(name), origin))
        return found

    def refresh_account(self) -> None:
        """Copy the account's agents into the cache. A failed read leaves the previous copy."""
        if self.account_cache is None:
            return
        from grok_assistant.account_agents import fetch_account_agents

        found = fetch_account_agents()
        if not found:
            return
        self.account_cache.mkdir(parents=True, exist_ok=True)
        keep = set()
        for name, body in found.items():
            path = self.account_cache / _agent_filename(name)
            keep.add(path.name)
            if path.exists():
                try:
                    if path.read_text(encoding="utf-8") == body:
                        continue
                except OSError:
                    pass
            temporary = path.with_suffix(".md.tmp")
            temporary.write_text(body, encoding="utf-8")
            temporary.replace(path)
        for path in self.account_cache.glob("*.md"):
            if path.name not in keep:
                path.unlink(missing_ok=True)

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
