"""Language packs. Add a json file under lang/ and the menu can use it."""

from __future__ import annotations

import json
from pathlib import Path

from grok_assistant.paths import default_data_dir

_ORDER = ("es", "fr", "de", "en")
_current_code = "es"
_current: dict = {}


def bundled_dir() -> Path:
    return Path(__file__).resolve().parent / "lang"


def override_dir() -> Path:
    return default_data_dir() / "lang"


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _merge(base: dict, patch: dict) -> dict:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def codes() -> list[str]:
    found = {path.stem for path in bundled_dir().glob("*.json")}
    found.update(path.stem for path in override_dir().glob("*.json"))
    ordered = [code for code in _ORDER if code in found]
    ordered.extend(sorted(found - set(ordered)))
    return ordered or ["es"]


def languages() -> list[tuple[str, str]]:
    rows = []
    for code in codes():
        pack = _load(code)
        rows.append((code, str(pack.get("name") or code)))
    return rows


def _load(code: str) -> dict:
    pack = _read_json(bundled_dir() / f"{code}.json")
    pack = _merge(pack, _read_json(override_dir() / f"{code}.json"))
    pack["code"] = code
    return pack


def activate(code: str) -> dict:
    global _current_code, _current
    known = codes()
    _current_code = code if code in known else "es"
    _current = _load(_current_code)
    return _current


def current() -> dict:
    if not _current:
        activate(_current_code)
    return _current


def code() -> str:
    return current().get("code") or "es"


def text(key: str, fallback: str = "") -> str:
    value = (current().get("ui") or {}).get(key)
    return str(value) if value else fallback


def say(key: str, fallback: str, **kwargs) -> str:
    template = (current().get("speech") or {}).get(key) or fallback
    if kwargs:
        return str(template).format(**kwargs)
    return str(template)


def command_list(key: str) -> list[str]:
    raw = (current().get("commands") or {}).get(key)
    if not isinstance(raw, list) or not raw:
        return []
    return [str(item) for item in raw]


def command_map(key: str) -> dict[str, set[str]]:
    raw = (current().get("commands") or {}).get(key)
    if not isinstance(raw, dict) or not raw:
        return {}
    return {str(name): {str(word) for word in words} for name, words in raw.items()}


def fixed_commands() -> list[tuple]:
    raw = (current().get("commands") or {}).get("fixed")
    if not isinstance(raw, list) or not raw:
        return []
    rows = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        phrases = tuple(str(phrase) for phrase in item.get("phrases") or [])
        rows.append((str(item["id"]), phrases, bool(item.get("confirm")), bool(item.get("admin"))))
    return rows


def help_topics() -> list[tuple[str, str, str]]:
    raw = current().get("help")
    if not isinstance(raw, list) or not raw:
        return []
    rows = []
    for item in raw:
        if isinstance(item, dict) and item.get("title"):
            rows.append((str(item["title"]), str(item.get("body") or ""), str(item.get("example") or "")))
    return rows


def screen_help() -> str:
    return str(current().get("screen_help") or "")


def reply_rules() -> str:
    return str(current().get("reply") or "")


def agent_rules() -> str:
    return str(current().get("agent_rules") or "")


def stt_language() -> str:
    return str(current().get("stt") or "es")


def person_pack(person_id: str) -> dict | None:
    raw = (current().get("persons") or {}).get(person_id)
    return raw if isinstance(raw, dict) else None


def bundled_person(person_id: str) -> dict | None:
    """The shipped definition, ignoring edits saved from the application."""
    raw = (_read_json(bundled_dir() / f"{code()}.json").get("persons") or {}).get(person_id)
    return raw if isinstance(raw, dict) else None


def person_ids() -> list[str]:
    raw = current().get("persons") or {}
    return [str(key) for key in raw] if isinstance(raw, dict) else []


def save_section(section: str, value) -> None:
    """Write one section into the editable copy of the active language."""
    folder = override_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{code()}.json"
    pack = _read_json(path)
    pack[section] = value
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    activate(code())
