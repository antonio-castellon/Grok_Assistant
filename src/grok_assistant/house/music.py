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


def match_audio_device(listing: str, wanted: str) -> str:
    """The mpv device id whose description is exactly the saved speaker name."""
    name = " ".join(str(wanted or "").split())
    if not name:
        return ""
    for line in (listing or "").splitlines():
        text = line.strip()
        if not text.startswith("'"):
            continue
        end = text.find("'", 1)
        if end < 0:
            continue
        ident = text[1:end]
        rest = text[end + 1 :].strip()
        if rest.startswith("(") and rest.endswith(")"):
            rest = rest[1:-1].strip()
        if rest == name:
            return ident
    return ""


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
        self.output = ""
        self._devices = None

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

    def play(self, title: str, volume: int, on_status=None, output: str = "") -> str | None:
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
        self.output = " ".join(str(output or "").split())
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
        command = [str(self._tool("mpv")), "--no-video", "--really-quiet", f"--input-ipc-server={_PIPE}"]
        if volume is not None:
            command.append(f"--volume={max(0, min(100, int(volume)))}")
        device = self._output_device(self.output)
        if device:
            command.append(f"--audio-device={device}")
        command.append(url)
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

    def _output_device(self, wanted: str) -> str:
        name = " ".join(str(wanted or "").split())
        if not name:
            return ""
        if self._devices is None:
            self._devices = self._device_listing()
        found = match_audio_device(self._devices, name)
        if found:
            return found
        self._devices = self._device_listing()
        return match_audio_device(self._devices, name)

    def _device_listing(self) -> str:
        binary = self._tool("mpv")
        if binary is None:
            return ""
        try:
            done = subprocess.run(
                [str(binary), "--audio-device=help"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
                **no_window(),
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return (done.stdout or "") + (done.stderr or "")

    def _ipc(self, line: str) -> bool:
        try:
            with open(_PIPE, "w", encoding="utf-8") as pipe:
                pipe.write(line + "\n")
            return True
        except OSError:
            return False
