"""How much of the linked Grok account allowance is already used. No audio, no prompt."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

BILLING = "https://cli-chat-proxy.grok.com/v1/billing?format=credits"


def percent_used(payload: dict) -> int | None:
    """Weekly allowance already spent, 0–100. None when the account did not say."""
    config = payload.get("config") if isinstance(payload, dict) else None
    source = config if isinstance(config, dict) else payload
    if not isinstance(source, dict) or source.get("creditUsagePercent") is None:
        return None
    try:
        value = int(round(float(source["creditUsagePercent"])))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, value))


def fetch_account_percent(auth_path: Path | None = None) -> int | None:
    path = auth_path or Path.home() / ".grok" / "auth.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    key = ""
    if isinstance(raw, dict):
        for item in raw.values():
            if isinstance(item, dict) and item.get("key"):
                key = str(item["key"])
                break
    if not key:
        return None
    request = urllib.request.Request(
        BILLING,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "GrokAssistant"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
    return percent_used(payload)
