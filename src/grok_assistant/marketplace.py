"""Catalog of voices, speech models, and the small local model. Nothing downloads until you ask."""

from __future__ import annotations

import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from grok_assistant.paths import default_data_dir

PIPER = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
SHERPA = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
QWEN = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"


@dataclass(frozen=True)
class Offer:
    id: str
    kind: str
    title: str
    detail: str
    size: str
    files: tuple[tuple[str, str], ...] = ()
    use_label: str = ""
    engine_id: str = ""
    local: str = ""

    def ready(self, root: Path | None = None) -> bool:
        if self.local == "windows-speech":
            from grok_assistant.listen import windows_spanish_available

            return windows_spanish_available()
        base = root or default_data_dir()
        if self.kind == "llm":
            folder = base / "llm"
            return any(folder.rglob("*.gguf")) and _llama_exe(folder) is not None
        return all((base / rel).exists() for _url, rel in self.files)


def offers() -> list[Offer]:
    """Speech models first. Those are the ears the menu shows as not installed."""
    ears = [
        ("davefx", "Dave · España", "es/es_ES/davefx/medium/es_ES-davefx-medium", "63 MB"),
        ("sharvard", "Sharvard · España", "es/es_ES/sharvard/medium/es_ES-sharvard-medium", "77 MB"),
        ("carlfm", "Carlfm · España", "es/es_ES/carlfm/x_low/es_ES-carlfm-x_low", "28 MB"),
        ("ald", "Ald · México", "es/es_MX/ald/medium/es_MX-ald-medium", "63 MB"),
        ("mls9972", "MLS 9972 · España", "es/es_ES/mls_9972/low/es_ES-mls_9972-low", "63 MB"),
        ("mls10246", "MLS 10246 · España", "es/es_ES/mls_10246/low/es_ES-mls_10246-low", "63 MB"),
    ]
    items = [
        Offer(
            id="windows-es",
            kind="stt",
            title="Windows español",
            detail="Dictado de escritorio de Windows. El audio se queda en este PC. Si falta, el botón lo instala y Windows pide permiso.",
            size="idioma de Windows",
            engine_id="windows",
            local="windows-speech",
        ),
        Offer(
            id="kroko",
            kind="stt",
            title="Kroko · español",
            detail="Oído en streaming. Es el que escucha frases en español mientras hablas, sin subir el audio.",
            size="119 MB",
            engine_id="kroko",
            files=((
                f"{SHERPA}/sherpa-onnx-streaming-zipformer-es-kroko-2025-08-06.tar.bz2",
                "models/sherpa-onnx-streaming-zipformer-es-kroko-2025-08-06.tar.bz2",
            ),),
        ),
        Offer(
            id="whisper",
            kind="stt",
            title="Whisper pequeño",
            detail="Reconocimiento local, modelo tiny de sherpa. Más rápido, menos fino.",
            size="~100 MB",
            engine_id="whisper",
            files=((f"{SHERPA}/sherpa-onnx-whisper-tiny.tar.bz2", "models/sherpa-onnx-whisper-tiny.tar.bz2"),),
        ),
        Offer(
            id="base",
            kind="stt",
            title="Whisper base",
            detail="El mismo motor, modelo base. Más lento y suele oír mejor.",
            size="~200 MB",
            engine_id="base",
            files=((f"{SHERPA}/sherpa-onnx-whisper-base.tar.bz2", "models/sherpa-onnx-whisper-base.tar.bz2"),),
        ),
        Offer(
            id="canary",
            kind="stt",
            title="Canary",
            detail="Oído local en español, inglés, francés y alemán. Una frase se cierra tras el silencio. El audio no sale de este PC.",
            size="~200 MB",
            engine_id="canary",
            files=((
                f"{SHERPA}/sherpa-onnx-nemo-canary-180m-flash-en-es-de-fr-int8.tar.bz2",
                "models/sherpa-onnx-nemo-canary-180m-flash-en-es-de-fr-int8.tar.bz2",
            ),),
        ),
    ]
    items.extend(
        Offer(
            id=key,
            kind="voice",
            title=title,
            detail="Voz Piper en español. Se usa en el menú Voz.",
            size=size,
            use_label=title,
            files=(
                (f"{PIPER}/{path}.onnx", f"voices/{path.rsplit('/', 1)[-1]}.onnx"),
                (f"{PIPER}/{path}.onnx.json", f"voices/{path.rsplit('/', 1)[-1]}.onnx.json"),
            ),
        )
        for key, title, path, size in ears
    )
    items.append(
        Offer(
            id="local-llm",
            kind="llm",
            title="Qwen 0.5B",
            detail="Modelo pequeño en este PC. Lee la frase y decide si es orden, pregunta o ruido antes de llamar a la nube.",
            size="~400 MB + llama.cpp",
            files=((QWEN, "llm/qwen2.5-0.5b-instruct-q4_k_m.gguf"),),
        )
    )
    return items


def progress_percent(done: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, int(done * 100 / total)))


def download(offer: Offer, on_status, on_progress=None, root: Path | None = None) -> None:
    if offer.local == "windows-speech":
        from grok_assistant.listen import install_windows_speech

        on_status("instalo el idioma de voz de Windows")
        _report(on_progress, 0)
        message = install_windows_speech()
        if message != "OK":
            raise RuntimeError(message.removeprefix("ERR:"))
        _report(on_progress, 100)
        return
    base = root or default_data_dir()
    base.mkdir(parents=True, exist_ok=True)
    done = 0
    known = 0

    def account(got: int, total: int, key: str) -> None:
        nonlocal known
        if total > 0 and key not in seen:
            seen[key] = total
            known = sum(seen.values())
        current = done + got
        whole = known or current or 1
        _report(on_progress, min(99, progress_percent(current, whole)))

    seen: dict[str, int] = {}
    for url, rel in offer.files:
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or dest.stat().st_size < 1000:
            on_status(f"bajo {offer.title}")
            _fetch(url, dest, lambda got, total, key=rel: account(got, total, key))
        size = dest.stat().st_size
        done += size
        if rel not in seen:
            seen[rel] = size
            known = sum(seen.values())
        if dest.name.endswith(".tar.bz2"):
            on_status(f"abro {dest.name}")
            with tarfile.open(dest, "r:bz2") as packed:
                packed.extractall(base / "models")
        elif dest.suffix == ".zip":
            on_status(f"abro {dest.name}")
            with zipfile.ZipFile(dest) as packed:
                packed.extractall(dest.parent)
    if offer.kind == "llm":
        on_status("bajo llama.cpp")
        _ensure_llama(base / "llm", on_status, lambda got, total: account(got, total, "llama.cpp"))
    _report(on_progress, 100)


def _report(on_progress, value: int) -> None:
    if on_progress is not None:
        on_progress(value)


def _fetch(url: str, dest: Path, on_bytes=None) -> None:
    """Write to a side file. The real name appears only when the file is complete."""
    request = urllib.request.Request(url, headers={"User-Agent": "GrokAssistant"})
    part = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(request, timeout=120) as response, part.open("wb") as handle:
            total = int(response.headers.get("Content-Length") or 0)
            got = 0
            if on_bytes is not None:
                on_bytes(0, total)
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                handle.write(chunk)
                got += len(chunk)
                if on_bytes is not None:
                    on_bytes(got, total)
    except Exception:
        part.unlink(missing_ok=True)
        raise
    part.replace(dest)


def _ensure_llama(folder: Path, on_status, on_bytes=None) -> None:
    if _llama_exe(folder):
        return
    import json

    folder.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest",
        headers={"User-Agent": "GrokAssistant", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    url = ""
    for asset in payload.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".zip") and "win" in name and "x64" in name and "cpu" in name:
            url = asset["browser_download_url"]
            break
    if not url:
        raise RuntimeError("no encuentro el zip de llama.cpp para Windows")
    archive = folder / "llama-cpp.zip"
    on_status("bajo el motor llama.cpp")
    _fetch(url, archive, on_bytes)
    with zipfile.ZipFile(archive) as packed:
        packed.extractall(folder)


def _llama_exe(folder: Path) -> Path | None:
    for name in ("llama-server.exe", "llama-cli.exe"):
        found = next(folder.rglob(name), None)
        if found:
            return found
    return None
