"""Look for a newer GitHub release and, in the executable, replace this copy."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = "antonio-castellon/Grok_Assistant"
API = f"https://api.github.com/repos/{REPO}/releases?per_page=10"
PREFIX = f"https://github.com/{REPO}/releases/download/"
ASSET = "GrokAssistant.exe"


def parse_build(body: str) -> str:
    for line in (body or "").splitlines():
        text = line.strip().strip("`")
        if text.lower().startswith("build:"):
            return text.split(":", 1)[1].strip().strip("`")
    return ""


def asset_url(release: dict) -> str:
    for asset in release.get("assets") or []:
        if asset.get("name") != ASSET:
            continue
        url = str(asset.get("browser_download_url") or "")
        if url.startswith(PREFIX) and url.endswith("/" + ASSET):
            return url
    return ""


def choose_update(releases, local_build: str, local_when: str) -> dict | None:
    """The newest release that is later than this build, names a different build, and ships the executable."""
    if not local_build or not local_when:
        return None
    best = None
    for release in releases or []:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        published = str(release.get("published_at") or "")
        if not published or published <= local_when:
            continue
        remote = parse_build(str(release.get("body") or ""))
        if not remote or remote == local_build:
            continue
        url = asset_url(release)
        if not url:
            continue
        if best is None or published > best["published"]:
            best = {
                "tag": str(release.get("tag_name") or ""),
                "published": published,
                "build": remote,
                "url": url,
            }
    return best


def find_update() -> dict | None:
    """None unless this is the Windows executable and a newer release is published."""
    if not getattr(sys, "frozen", False) or os.name != "nt":
        return None
    from grok_assistant.buildinfo import read_stamp

    local_build, local_when = read_stamp()
    releases = _fetch_releases()
    if releases is None:
        return None
    return choose_update(releases, local_build, local_when)


def apply_update(offer: dict) -> bool:
    """Download the release and hand the replacement to a helper. The window closes afterwards."""
    if not getattr(sys, "frozen", False) or os.name != "nt":
        return False
    url = str((offer or {}).get("url") or "")
    if not (url.startswith(PREFIX) and url.endswith("/" + ASSET)):
        return False
    dest = Path(sys.executable).resolve()
    handle = tempfile.NamedTemporaryFile(prefix="GrokAssistant-", suffix=".exe", delete=False)
    downloaded = Path(handle.name)
    handle.close()
    if not _download(url, downloaded):
        downloaded.unlink(missing_ok=True)
        return False
    return _spawn_replacer(downloaded, dest)


def _fetch_releases() -> list | None:
    request = urllib.request.Request(
        API,
        headers={"User-Agent": "GrokAssistant", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, list):
        return None
    return payload


def _download(url: str, dest: Path) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": "GrokAssistant"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as handle:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    except OSError:
        return False
    return dest.is_file() and dest.stat().st_size > 0


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _spawn_replacer(source: Path, dest: Path) -> bool:
    child = os.getpid()
    parent = os.getppid()
    script = "\n".join([
        "$ErrorActionPreference = 'Stop'",
        f"$child = {int(child)}",
        f"$parent = {int(parent)}",
        f"$source = {_ps_quote(str(source))}",
        f"$dest = {_ps_quote(str(dest))}",
        "Wait-Process -Id $child -Timeout 90 -ErrorAction SilentlyContinue",
        "if ($parent -gt 0) { Wait-Process -Id $parent -Timeout 30 -ErrorAction SilentlyContinue }",
        "$ok = $false",
        "for ($i = 0; $i -lt 40; $i++) {",
        "    try {",
        "        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Force }",
        "        Move-Item -LiteralPath $source -Destination $dest -Force",
        "        $ok = $true",
        "        break",
        "    } catch { Start-Sleep -Milliseconds 500 }",
        "}",
        "if ($ok) { Start-Process -FilePath $dest }",
        "",
    ])
    fd, name = tempfile.mkstemp(prefix="GrokAssistant-update-", suffix=".ps1")
    os.close(fd)
    Path(name).write_text(script, encoding="utf-8-sig")
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", name],
            creationflags=flags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return True
