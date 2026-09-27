"""Songs stay on this machine's speakers. The microphone takes a break while they play."""

from __future__ import annotations

import os
import shutil
import subprocess

from grok_assistant.quiet import no_window

_PIPE = r"\\.\pipe\grok-assistant-mpv" if os.name == "nt" else "/tmp/grok-assistant-mpv"


class Music:
    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.loaded = False
        self.user_paused = False
        self._held = False
        self.url = ""

    def available(self) -> bool:
        return bool(shutil.which("yt-dlp") and shutil.which("mpv"))

    def play(self, title: str, volume: int) -> str | None:
        if not self.available():
            return "No puedo poner música en este equipo."
        try:
            done = subprocess.run(
                ["yt-dlp", "-f", "bestaudio", "-g", "--no-playlist", f"ytsearch1:{title}"],
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
        command = ["mpv", "--no-video", "--really-quiet", f"--input-ipc-server={_PIPE}", url]
        if volume is not None:
            command.insert(-1, f"--volume={max(0, min(100, int(volume)))}")
        self.proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **no_window())
        self.url = url
        self.loaded = True
        self.user_paused = False

    def _ipc(self, line: str) -> bool:
        try:
            with open(_PIPE, "w", encoding="utf-8") as pipe:
                pipe.write(line + "\n")
            return True
        except OSError:
            return False
