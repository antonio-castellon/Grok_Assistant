"""Catalog of voices, speech models, and the small local model. Nothing downloads until you ask."""

from __future__ import annotations

import json
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from grok_assistant.paths import default_data_dir

PIPER = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
SHERPA = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
QWEN_05 = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
QWEN_15 = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
SMOL_360 = "https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF/resolve/main/smollm2-360m-instruct-q8_0.gguf"
LLAMA_1B = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"


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
    lang: str = ""

    def ready(self, root: Path | None = None) -> bool:
        if self.local == "windows-speech":
            from grok_assistant.listen import windows_spanish_available

            return windows_spanish_available()
        base = root or default_data_dir()
        if self.kind == "llm":
            folder = base / "llm"
            return all((base / rel).stat().st_size > 1_000_000 for _url, rel in self.files if (base / rel).exists()) and all(
                (base / rel).exists() for _url, rel in self.files
            ) and _llama_exe(folder) is not None
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
        ("siwis", "Siwis · France", "fr/fr_FR/siwis/medium/fr_FR-siwis-medium", "60 MB"),
        ("upmc", "UPMC · France", "fr/fr_FR/upmc/medium/fr_FR-upmc-medium", "73 MB"),
        ("tom", "Tom · France", "fr/fr_FR/tom/medium/fr_FR-tom-medium", "61 MB"),
        ("thorsten", "Thorsten · Deutschland", "de/de_DE/thorsten/medium/de_DE-thorsten-medium", "60 MB"),
        ("eva", "Eva · Deutschland", "de/de_DE/eva_k/x_low/de_DE-eva_k-x_low", "20 MB"),
        ("kerstin", "Kerstin · Deutschland", "de/de_DE/kerstin/low/de_DE-kerstin-low", "60 MB"),
        ("lessac", "Lessac · US", "en/en_US/lessac/medium/en_US-lessac-medium", "60 MB"),
        ("ryan", "Ryan · US", "en/en_US/ryan/medium/en_US-ryan-medium", "60 MB"),
        ("alba", "Alba · UK", "en/en_GB/alba/medium/en_GB-alba-medium", "60 MB"),
        ("alan", "Alan · UK", "en/en_GB/alan/medium/en_GB-alan-medium", "60 MB"),
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
            id="zipfr",
            kind="stt",
            title="Zipformer francés",
            detail="Oído en streaming, solo francés. El audio no sale de este PC.",
            size="380 MB",
            engine_id="zipfr",
            files=((
                f"{SHERPA}/sherpa-onnx-streaming-zipformer-fr-2023-04-14.tar.bz2",
                "models/sherpa-onnx-streaming-zipformer-fr-2023-04-14.tar.bz2",
            ),),
        ),
        Offer(
            id="zipen",
            kind="stt",
            title="Zipformer inglés",
            detail="Oído en streaming, solo inglés, modelo pequeño. El audio no sale de este PC.",
            size="122 MB",
            engine_id="zipen",
            files=((
                f"{SHERPA}/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2",
                "models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2",
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
            id="small",
            kind="stt",
            title="Whisper small",
            detail="El mismo motor, modelo small. Más fino y más pesado que el pequeño.",
            size="610 MB",
            engine_id="small",
            files=((f"{SHERPA}/sherpa-onnx-whisper-small.tar.bz2", "models/sherpa-onnx-whisper-small.tar.bz2"),),
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
        Offer(
            id="cohere",
            kind="stt",
            title="Cohere",
            detail="Oído local para 14 idiomas, entre ellos español, francés, alemán e inglés. Usa el idioma elegido. El audio no sale de este PC.",
            size="1.6 GB",
            engine_id="cohere",
            files=((
                f"{SHERPA}/sherpa-onnx-cohere-transcribe-14-lang-int8-2026-04-01.tar.bz2",
                "models/sherpa-onnx-cohere-transcribe-14-lang-int8-2026-04-01.tar.bz2",
            ),),
        ),
    ]
    items.extend(
        Offer(
            id=key,
            kind="voice",
            title=title,
            detail="Voz Piper. Solo se ofrece y se puede elegir cuando el idioma coincide.",
            size=size,
            use_label=title,
            lang=path.split("/", 1)[0],
            files=(
                (f"{PIPER}/{path}.onnx", f"voices/{path.rsplit('/', 1)[-1]}.onnx"),
                (f"{PIPER}/{path}.onnx.json", f"voices/{path.rsplit('/', 1)[-1]}.onnx.json"),
            ),
        )
        for key, title, path, size in ears
    )
    items.extend(
        Offer(
            id=key,
            kind="llm",
            title=title,
            detail="Mira si la frase del oído es un comando de la lista o una variación. Si no lo es, el texto sigue tal cual hacia Grok.",
            size=size,
            files=((url, f"llm/{name}"),),
        )
        for key, title, size, url, name in (
            ("qwen-0.5b", "Qwen 0.5B", "491 MB + motor", QWEN_05, "qwen2.5-0.5b-instruct-q4_k_m.gguf"),
            ("smol-360m", "SmolLM2 360M", "386 MB + motor", SMOL_360, "smollm2-360m-instruct-q8_0.gguf"),
            ("llama-1b", "Llama 3.2 1B", "808 MB + motor", LLAMA_1B, "Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
            ("qwen-1.5b", "Qwen 1.5B", "1.1 GB + motor", QWEN_15, "qwen2.5-1.5b-instruct-q4_k_m.gguf"),
        )
    )
    return items


def offers_for(lang: str | None = None) -> list[Offer]:
    """Voice rows follow the selected language. Ears and local models stay listed."""
    from grok_assistant.i18n import code

    wanted = (lang or code() or "es").split("-")[0].lower()
    rows = []
    for item in offers():
        if item.kind == "voice" and item.lang and item.lang != wanted:
            continue
        rows.append(item)
    rows.extend(extra_piper_offers(wanted))
    return rows


PIPER_INDEX = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/voices.json"


def extra_piper_offers(lang: str, index: dict | None = None) -> list[Offer]:
    """More Piper voices from the public rhasspy catalog, for this language only."""
    data = piper_cached() if index is None else index
    if not data:
        return []
    known = set()
    for item in offers():
        if item.kind != "voice":
            continue
        for _url, rel in item.files:
            known.add(rel.rsplit("/", 1)[-1])
    rows = []
    for key, info in data.items():
        if not isinstance(info, dict):
            continue
        language = info.get("language") or {}
        if str(language.get("family") or "") != lang:
            continue
        try:
            speakers = int(info.get("num_speakers") or 1)
        except (TypeError, ValueError):
            speakers = 1
        if speakers > 8:
            continue
        files = info.get("files") or {}
        onnx = next((path for path in files if str(path).endswith(".onnx")), "")
        meta = next((path for path in files if str(path).endswith(".onnx.json")), "")
        if not onnx or not meta:
            continue
        file_name = str(onnx).rsplit("/", 1)[-1]
        if file_name in known:
            continue
        size = int((files.get(onnx) or {}).get("size_bytes") or 0)
        name = str(info.get("name") or key).replace("_", " ")
        country = str(language.get("country_english") or "")
        quality = str(info.get("quality") or "")
        title = f"{name} · {country} · {quality}".strip(" ·")
        label = Path(file_name).stem.replace("-", " ")
        rows.append(Offer(
            id=f"piper-{key}",
            kind="voice",
            title=title,
            detail="Piper · rhasspy/piper-voices",
            size=f"{max(1, size // 1_000_000)} MB" if size else "",
            use_label=label,
            lang=lang,
            files=(
                (f"{PIPER}/{onnx}", f"voices/{file_name}"),
                (f"{PIPER}/{meta}", f"voices/{str(meta).rsplit('/', 1)[-1]}"),
            ),
        ))
    rows.sort(key=lambda item: item.title.lower())
    return rows


def piper_cached() -> dict:
    """The rhasspy catalog already saved on this PC. Never touches the network."""
    cache = default_data_dir() / "voices" / "piper-voices.json"
    if not cache.exists() or cache.stat().st_size < 1000:
        return {}
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def fetch_piper_index() -> dict:
    """Download voices.json once, then keep the copy under the assistant data folder."""
    found = piper_cached()
    if found:
        return found
    try:
        import urllib.request

        folder = default_data_dir() / "voices"
        folder.mkdir(parents=True, exist_ok=True)
        cache = folder / "piper-voices.json"
        with urllib.request.urlopen(PIPER_INDEX, timeout=20) as response:
            raw = response.read()
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return {}
        cache.write_bytes(raw)
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def progress_percent(done: int, total: int) -> int:
    if done <= 0 or total <= 0:
        return 0
    value = int(done * 100 / total)
    if value == 0:
        return 1
    return min(100, value)


def cpu_windows_zip(assets: list) -> dict | None:
    """The Windows CPU build. Releases named 'latest' no longer carry it."""
    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name.endswith(".zip") and "win" in name and "cpu" in name and "x64" in name and "cuda" not in name:
            return asset
    return None


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
        whole = known or max(current, 1)
        caption = _bytes_caption(current, whole if known else total)
        _report(on_progress, min(99, progress_percent(current, whole)), caption)

    seen: dict[str, int] = {}
    for url, rel in offer.files:
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or dest.stat().st_size < 1000:
            on_status(f"bajo {offer.title}")
            _fetch(url, dest, lambda got, total, key=rel: account(got, total, key))
        else:
            on_status(f"{offer.title} ya está en el disco")
            _report(on_progress, 1, "el archivo ya está. Sigue el motor.")
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


def _report(on_progress, value: int, caption: str = "") -> None:
    if on_progress is not None:
        on_progress(value, caption)


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


def _bytes_caption(done: int, total: int) -> str:
    if total <= 0:
        return f"{done / (1024 * 1024):.1f} MB"
    return f"{done / (1024 * 1024):.1f} MB / {total / (1024 * 1024):.0f} MB"


def _ensure_llama(folder: Path, on_status, on_bytes=None) -> None:
    if _llama_exe(folder):
        return
    import json

    folder.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=20",
        headers={"User-Agent": "GrokAssistant", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        releases = json.load(response)
    url = ""
    for release in releases:
        asset = cpu_windows_zip(release.get("assets") or [])
        if asset:
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
