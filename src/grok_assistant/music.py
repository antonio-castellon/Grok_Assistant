"""Songs stay on this machine's speakers. YouTube audio, no account, same idea as the Pi."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from grok_assistant.paths import default_data_dir
from grok_assistant.quiet import no_window

def _fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "GrokAssistant"})
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)


def _mpv_url() -> str:
    request = urllib.request.Request(
        "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest",
        headers={"User-Agent": "GrokAssistant", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    for asset in payload.get("assets") or []:
        name = str(asset.get("name", ""))
        if name.startswith("mpv-x86_64-") and name.endswith(".7z") and "-dev-" not in name and "-v3-" not in name:
            return asset["browser_download_url"]
    raise RuntimeError("no encuentro mpv para Windows")


_PIPE = r"\\.\pipe\grok-assistant-mpv" if os.name == "nt" else "/tmp/grok-assistant-mpv"
_YTDLP = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
_SEVEN = "https://www.7-zip.org/a/7zr.exe"


class Music:
    def __init__(self, folder: Path | None = None):
        self.folder = folder or default_data_dir() / "player"
        self.proc: subprocess.Popen | None = None
        self.loaded = False
        self.user_paused = False
        self._held = False
        self.url = ""

    def available(self) -> bool:
        return self._tool("yt-dlp") is not None and self._tool("mpv") is not None

    def ensure(self, on_status=None) -> bool:
        if self.available():
            return True
        if os.name != "nt":
            return False
        self.folder.mkdir(parents=True, exist_ok=True)
        if on_status:
            on_status("Bajo el reproductor. Es YouTube, sin cuenta.")
        try:
            ytdlp = self.folder / "yt-dlp.exe"
            if not ytdlp.exists():
                _fetch(_YTDLP, ytdlp)
            if self._tool("mpv") is None:
                archive = self.folder / "mpv.7z"
                seven = self.folder / "7zr.exe"
                if not seven.exists():
                    _fetch(_SEVEN, seven)
                if not archive.exists() or archive.stat().st_size < 1000:
                    _fetch(_mpv_url(), archive)
                subprocess.run(
                    [str(seven), "x", str(archive), f"-o{self.folder}", "-y"],
                    check=False,
                    timeout=120,
                    **no_window(),
                )
        except (OSError, subprocess.TimeoutExpired, RuntimeError):
            return False
        return self.available()

    def play(self, title: str, volume: int, on_status=None) -> str | None:
        if not self.available() and not self.ensure(on_status):
            return "No pude bajar el reproductor de YouTube."
        try:
            done = subprocess.run(
                [str(self._tool("yt-dlp")), "-f", "bestaudio", "-g", "--no-playlist", f"ytsearch1:{title}"],
                capture_output=True,
                text=True,
                timeout=40,
                check=False,
                **no_window(),
            )
        except (OSError, subprocess.TimeoutExpired):
            return "No encuentro esa canción."
        lines = [line.strip() for line in (done.stdout or "").splitlines() if line.strip()]
        if done.returncode != 0 or not lines:
            return "No encuentro esa canción."
        self._start(lines[0], volume)
        return None

    def pause(self) -> None:
        self.user_paused = True
        if not self._ipc("{ \"command\": [\"set_property\", \"pause\", true] }"):
            self._ipc("set pause yes")

    def resume(self) -> None:
        self.user_paused = False
        if self.proc is None or self.proc.poll() is not None:
            if self.url:
                self._start(self.url, None)
            return
        if not self._ipc("{ \"command\": [\"set_property\", \"pause\", false] }"):
            self._ipc("set pause no")

    def stop(self) -> None:
        self.loaded = False
        self.user_paused = False
        self.url = ""
        self._held = False
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
        self.proc = None

    def hold_for_speech(self) -> None:
        if self.loaded and not self.user_paused and self.proc is not None and self.proc.poll() is None:
            self._held = True
            if not self._ipc("{ \"command\": [\"set_property\", \"pause\", true] }"):
                self._ipc("set pause yes")

    def release_after_speech(self) -> None:
        if self._held and not self.user_paused:
            self.resume()
        self._held = False

    def _start(self, url: str, volume: int | None) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
        command = [str(self._tool("mpv")), "--no-video", "--really-quiet", f"--input-ipc-server={_PIPE}", url]
        if volume is not None:
            command.insert(-1, f"--volume={max(0, min(100, int(volume)))}")
        self.proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **no_window())
        self.url = url
        self.loaded = True
        self.user_paused = False

    def _tool(self, name: str) -> Path | None:
        found = shutil.which(name) or shutil.which(f"{name}.exe")
        if found:
            return Path(found)
        if not self.folder.exists():
            return None
        match = next(self.folder.rglob(f"{name}.exe"), None)
        return match

    def _ipc(self, line: str) -> bool:
        try:
            with open(_PIPE, "w", encoding="utf-8") as pipe:
                pipe.write(line + "\n")
            return True
        except OSError:
            return False
