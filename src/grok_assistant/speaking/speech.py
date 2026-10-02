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
    "es_ES-mls_9972-low": "MLS 9972 · España",
    "es_ES-mls_10246-low": "MLS 10246 · España",
    "fr_FR-siwis-medium": "Siwis · France",
    "fr_FR-upmc-medium": "UPMC · France",
    "fr_FR-tom-medium": "Tom · France",
    "de_DE-thorsten-medium": "Thorsten · Deutschland",
    "de_DE-eva_k-x_low": "Eva · Deutschland",
    "de_DE-kerstin-low": "Kerstin · Deutschland",
    "en_US-lessac-medium": "Lessac · US",
    "en_US-ryan-medium": "Ryan · US",
    "en_GB-alba-medium": "Alba · UK",
    "en_GB-alan-medium": "Alan · UK",
}


def voice_lang(name: str) -> str:
    """es, fr, de, or en from a Piper file name or a Windows culture."""
    token = (name or "").strip().replace("_", "-").lower()
    head = token.split("-", 1)[0]
    if head in {"es", "fr", "de", "en"}:
        return head
    return ""


class Speaker:
    def list_voices(self, lang: str | None = None) -> list[str]:
        from grok_assistant.i18n import code

        wanted = voice_lang(lang or code() or "es") or "es"
        found = [label for label, tongue in _piper_voices() if tongue == wanted]
        if os.name == "nt":
            found.extend(name for name, tongue in _windows_voices() if tongue == wanted)
        else:
            found.extend(name for name, tongue in _linux_voices() if tongue == wanted)
        return found or ["Predeterminada"]

    def say(self, text: str, voice: str | None, volume: int, output: str = "") -> bool:
        text = (text or "").strip()
        if not text:
            return True
        volume = max(0, min(100, int(volume)))
        model = _piper_by_label().get(voice or "")
        if model and _piper_say(text, model, output):
            return True
        if os.name == "nt":
            return _windows_say(text, voice, volume, output)
        return _linux_say(text, voice, volume, output)


def _windows_voices() -> list[tuple[str, str]]:
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
    found = []
    for line in (done.stdout or "").splitlines():
        if "|" not in line:
            continue
        name, culture = line.split("|", 1)
        name = name.strip()
        tongue = voice_lang(culture)
        if name and tongue:
            found.append((name, tongue))
    return found


def _windows_say(text: str, voice: str | None, volume: int, output: str = "") -> bool:
    script = bundle_root() / "scripts" / "speak.ps1"
    if not script.exists():
        return False
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False)
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav.close()
    try:
        handle.write(text)
        handle.close()
        done = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(script), handle.name, str(volume), voice or "", wav.name],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **no_window(),
        )
        if done.returncode != 0 or not Path(wav.name).exists() or Path(wav.name).stat().st_size < 45:
            return False
        return _play_file(wav.name, output)
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        try:
            os.remove(handle.name)
        except OSError:
            pass
        try:
            os.remove(wav.name)
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


def _piper_voices() -> list[tuple[str, str]]:
    rows = []
    for label, model in _piper_by_label().items():
        tongue = voice_lang(model.stem)
        if tongue:
            rows.append((label, tongue))
    return rows


def _play_file(path: str, output: str) -> bool:
    from grok_assistant.listening.devices import play_wav

    if play_wav(path, output):
        return True
    if os.name == "nt":
        try:
            import winsound

            winsound.PlaySound(path, winsound.SND_FILENAME)
            return True
        except (RuntimeError, OSError):
            return False
    player = shutil.which("aplay") or shutil.which("afplay")
    if not player:
        return False
    played = subprocess.run([player, path], check=False, **no_window())
    return played.returncode == 0


def _piper_say(text: str, model: Path, output: str = "") -> bool:
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
        return _play_file(wav.name, output)
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        try:
            os.remove(wav.name)
        except OSError:
            pass


def _linux_voices() -> list[tuple[str, str]]:
    if shutil.which("espeak-ng"):
        names = ["es", "es-la", "fr", "de", "en"]
    elif shutil.which("espeak"):
        names = ["es", "es-la", "fr", "de", "en"]
    else:
        return []
    return [(name, voice_lang(name)) for name in names if voice_lang(name)]


def _linux_say(text: str, voice: str | None, volume: int, output: str = "") -> bool:
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        return False
    amplitude = str(max(0, min(200, volume * 2)))
    wav = None
    command = [binary, "-v", voice or "es", "-a", amplitude]
    if output:
        wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav.close()
        command.extend(["-w", wav.name])
    command.append(text)
    try:
        done = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **no_window(),
        )
        if done.returncode != 0:
            return False
        if wav is None:
            return True
        return _play_file(wav.name, output)
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        if wav is not None:
            try:
                os.remove(wav.name)
            except OSError:
                pass
