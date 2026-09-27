"""Local mouths. Spanish when the machine has a Spanish voice, and never a cloud voice."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from grok_assistant.paths import bundle_root, default_data_dir
from grok_assistant.quiet import no_window

PIPER_LABELS = {
    "es_ES-davefx-medium": "Dave · España",
    "es_ES-sharvard-medium": "Sharvard · España",
    "es_MX-ald-medium": "Ald · México",
    "es_ES-carlfm-x_low": "Carlfm · España",
    "es_AR-daniela-high": "Daniela · Argentina",
    "es_MX-claude-high": "Claude · México",
}


class Speaker:
    def list_voices(self) -> list[str]:
        found = _piper_voices()
        if os.name == "nt":
            found.extend(_windows_voices())
        else:
            found.extend(_linux_voices())
        return found or ["Predeterminada"]

    def say(self, text: str, voice: str | None, volume: int) -> bool:
        text = (text or "").strip()
        if not text:
            return True
        volume = max(0, min(100, int(volume)))
        model = _piper_by_label().get(voice or "")
        if model and _piper_say(text, model):
            return True
        if os.name == "nt":
            return _windows_say(text, voice, volume)
        return _linux_say(text, voice, volume)


def _windows_voices() -> list[str]:
    script = bundle_root() / "scripts" / "voices.ps1"
    if not script.exists():
        return []
    try:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            **no_window(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    spanish = []
    others = []
    for line in (done.stdout or "").splitlines():
        if "|" not in line:
            continue
        name, culture = line.split("|", 1)
        name = name.strip()
        if not name:
            continue
        if culture.lower().startswith("es"):
            spanish.append(name)
        else:
            others.append(name)
    return spanish + others


def _windows_say(text: str, voice: str | None, volume: int) -> bool:
    script = bundle_root() / "scripts" / "speak.ps1"
    if not script.exists():
        return False
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False)
    try:
        handle.write(text)
        handle.close()
        done = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(script), handle.name, str(volume), voice or ""],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **no_window(),
        )
        return done.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        try:
            os.remove(handle.name)
        except OSError:
            pass


def _voice_dirs() -> list[Path]:
    return [default_data_dir() / "voices", bundle_root() / "voices"]


def _piper_executable() -> Path | None:
    name = "piper.exe" if os.name == "nt" else "piper"
    for folder in _voice_dirs():
        direct = folder / name
        if direct.exists():
            return direct
        nested = folder / "piper" / name
        if nested.exists():
            return nested
    found = shutil.which(name)
    return Path(found) if found else None


def _piper_by_label() -> dict[str, Path]:
    catalog: dict[str, Path] = {}
    for folder in _voice_dirs():
        if not folder.exists():
            continue
        for model in sorted(folder.glob("*.onnx")):
            label = PIPER_LABELS.get(model.stem, model.stem.replace("-", " "))
            catalog.setdefault(label, model)
    return catalog


def _piper_voices() -> list[str]:
    return list(_piper_by_label())


def _piper_say(text: str, model: Path) -> bool:
    binary = _piper_executable()
    if binary is None or not model.exists():
        return False
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav.close()
    try:
        done = subprocess.run(
            [str(binary), "--model", str(model), "--output_file", wav.name],
            input=text,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
            **no_window(),
        )
        if done.returncode != 0 or not Path(wav.name).exists():
            return False
        if os.name == "nt":
            import winsound
            winsound.PlaySound(wav.name, winsound.SND_FILENAME)
            return True
        player = shutil.which("aplay") or shutil.which("afplay")
        if not player:
            return False
        played = subprocess.run([player, wav.name], check=False, **no_window())
        return played.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        try:
            os.remove(wav.name)
        except OSError:
            pass


def _linux_voices() -> list[str]:
    if shutil.which("espeak-ng"):
        return ["es", "es-la", "es+m3", "es+f3", "es+m1"]
    if shutil.which("espeak"):
        return ["es", "es-la"]
    return []


def _linux_say(text: str, voice: str | None, volume: int) -> bool:
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        return False
    amplitude = str(max(0, min(200, volume * 2)))
    try:
        done = subprocess.run(
            [binary, "-v", voice or "es", "-a", amplitude, text],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **no_window(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0
