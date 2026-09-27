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
WHISPER_CPP = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
QWEN = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"


@dataclass(frozen=True)
class Offer:
    id: str
    kind: str
    title: str
    detail: str
    size: str
    files: tuple[tuple[str, str], ...]
    use_label: str = ""
    engine_id: str = ""

    def ready(self, root: Path | None = None) -> bool:
        base = root or default_data_dir()
        if self.kind == "llm":
            folder = base / "llm"
            return any(folder.rglob("*.gguf")) and _llama_exe(folder) is not None
        return all((base / rel).exists() for _url, rel in self.files)


def offers() -> list[Offer]:
    voices = [
        ("davefx", "Dave · España", "es/es_ES/davefx/medium/es_ES-davefx-medium", "63 MB"),
        ("sharvard", "Sharvard · España", "es/es_ES/sharvard/medium/es_ES-sharvard-medium", "77 MB"),
        ("carlfm", "Carlfm · España", "es/es_ES/carlfm/x_low/es_ES-carlfm-x_low", "28 MB"),
        ("ald", "Ald · México", "es/es_MX/ald/medium/es_MX-ald-medium", "63 MB"),
        ("mls9972", "MLS 9972 · España", "es/es_ES/mls_9972/low/es_ES-mls_9972-low", "63 MB"),
        ("mls10246", "MLS 10246 · España", "es/es_ES/mls_10246/low/es_ES-mls_10246-low", "63 MB"),
    ]
    items = [
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
        for key, title, path, size in voices
    ]
    items.extend([
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
            id="ggml-tiny",
            kind="stt",
            title="Whisper.cpp tiny",
            detail="Modelo ggml para whisper.cpp. Ligero, para una frase corta.",
            size="75 MB",
            engine_id="whisper",
            files=((f"{WHISPER_CPP}/ggml-tiny.bin", "models/whisper-cpp/ggml-tiny.bin"),),
        ),
        Offer(
            id="ggml-base",
            kind="stt",
            title="Whisper.cpp base",
            detail="Modelo ggml más capaz para whisper.cpp.",
            size="150 MB",
            engine_id="base",
            files=((f"{WHISPER_CPP}/ggml-base.bin", "models/whisper-cpp/ggml-base.bin"),),
        ),
        Offer(
            id="local-llm",
            kind="llm",
            title="Qwen 0.5B",
            detail="Modelo pequeño en este PC. Lee la frase y decide si es orden, pregunta o ruido antes de llamar a la nube.",
            size="~400 MB + llama.cpp",
            files=((QWEN, "llm/qwen2.5-0.5b-instruct-q4_k_m.gguf"),),
        ),
    ])
    return items


def download(offer: Offer, on_status, root: Path | None = None) -> None:
    base = root or default_data_dir()
    base.mkdir(parents=True, exist_ok=True)
    for url, rel in offer.files:
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or dest.stat().st_size < 1000:
            on_status(f"bajo {offer.title}")
            _fetch(url, dest)
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
        _ensure_llama(base / "llm", on_status)


def _fetch(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "GrokAssistant"})
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)


def _ensure_llama(folder: Path, on_status) -> None:
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
    _fetch(url, archive)
    with zipfile.ZipFile(archive) as packed:
        packed.extractall(folder)


def _llama_exe(folder: Path) -> Path | None:
    for name in ("llama-server.exe", "llama-cli.exe"):
        found = next(folder.rglob(name), None)
        if found:
            return found
    return None
