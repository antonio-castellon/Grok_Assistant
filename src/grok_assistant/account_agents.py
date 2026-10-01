"""Agents the signed-in Grok account already publishes. No prompt is sent."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

BUNDLE = "https://cli-chat-proxy.grok.com/v1/subagents/bundle"
SETTINGS = "https://grok.com/rest/user-settings"


def agents_from_bundle(payload: dict) -> dict[str, str]:
    """Name to markdown, from the account bundle. Empty when the shape is not that list."""
    agents = payload.get("agents") if isinstance(payload, dict) else None
    if not isinstance(agents, dict):
        return {}
    found = {}
    for name, body in agents.items():
        title = " ".join(str(name).split())
        if not title or not isinstance(body, str) or not body.strip():
            continue
        found[title] = body if body.endswith("\n") else body + "\n"
    return found


def agents_from_customizations(payload: dict) -> dict[str, str]:
    """Name to markdown, from grok.com agent customizations. Empty when there are none."""
    items = payload.get("agentCustomizations") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return {}
    found = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_name = item.get("name") or item.get("title") or item.get("displayName") or item.get("id")
        title = " ".join(str(raw_name or "").split())
        if not title:
            continue
        prompt = item.get("instructions") or item.get("systemPrompt") or item.get("prompt") or item.get("description") or ""
        found[title] = (
            f"---\nname: {title}\n"
            "description: Agente de la cuenta de Grok.\n"
            "prompt_mode: full\nmodel: grok-4.7\n---\n\n"
            f"{prompt}\n"
        )
    return found


def fetch_account_agents(auth_path: Path | None = None) -> dict[str, str]:
    """Agents linked to the signed-in account. {} when the account cannot be read."""
    creds = _creds(auth_path or Path.home() / ".grok" / "auth.json")
    if creds is None:
        return {}
    key, user_id = creds
    found = agents_from_bundle(_get(BUNDLE, key, user_id))
    custom = agents_from_customizations(_get(SETTINGS, key, user_id))
    found.update(custom)
    return found


def _creds(path: Path) -> tuple[str, str] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    for item in raw.values():
        if isinstance(item, dict) and item.get("key"):
            return str(item["key"]), str(item.get("user_id") or "")
    return None


def _get(url: str, key: str, user_id: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "GrokAssistant",
            "X-XAI-Token-Auth": "xai-grok-cli",
            "x-userid": user_id,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return {}
    return payload if isinstance(payload, dict) else {}
