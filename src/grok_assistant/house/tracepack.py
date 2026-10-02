"""A zip of this run, written only when the person asks for it."""

from __future__ import annotations

import json
import tempfile
import time
import zipfile
from pathlib import Path

from grok_assistant.listening.enroll_audio import write_wav
from grok_assistant.mind.local_llm import SYSTEM


def save_trace(brain, sent, folder: Path) -> Path:
    """Heard audio, the local model's raw text, and what the assistant decided."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = Path(folder) / "traces" / f"traza-{stamp}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grok-traza-") as tmp:
        root = Path(tmp)
        _write_tree(root, brain, sent, folder)
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())
    return dest


def _write_tree(root: Path, brain, sent, folder: Path) -> None:
    (root / "leeme.txt").write_text(_ABOUT, encoding="utf-8")
    (root / "registro.txt").write_text("\n".join(brain.logs), encoding="utf-8")
    (root / "llm-instruccion.txt").write_text(SYSTEM, encoding="utf-8")
    _json(root / "llm.json", list(getattr(brain, "model_notes", [])))
    _json(root / "decisiones.json", _decisions(brain))
    _json(root / "nube.json", [[kind, text] for kind, text in list(sent or [])])
    _json(root / "ajustes.json", _settings(brain))
    _audio(root / "audio", list(getattr(brain, "heard_clips", [])))
    _live(root / "en-vivo", Path(folder) / "live")
    for name in ("ear.log", "crash.log"):
        _tail(folder / name, root / name)


def _decisions(brain) -> list:
    try:
        lines = list(brain.sessions.current().lines)
    except Exception:
        return []
    kept = []
    for item in lines[-200:]:
        if not isinstance(item, dict):
            continue
        kept.append({
            "ts": item.get("ts"),
            "heard": item.get("heard") or "",
            "decision": item.get("decision") or "",
            "sent": bool(item.get("sent")),
            "detail": item.get("detail") or "",
        })
    return kept


def _settings(brain) -> dict:
    from dataclasses import asdict

    return asdict(brain.settings)


def _live(folder: Path, source: Path) -> None:
    if not source.is_dir():
        return
    files = sorted(source.glob("frase-*.wav"), key=lambda item: item.stat().st_mtime)[-30:]
    if not files:
        return
    folder.mkdir(parents=True, exist_ok=True)
    for path in files:
        try:
            (folder / path.name).write_bytes(path.read_bytes())
        except OSError:
            continue


def _audio(folder: Path, clips: list) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    index = []
    for number, clip in enumerate(clips, start=1):
        name = f"{number:02d}.wav"
        audio = clip.get("audio")
        if audio is not None:
            try:
                write_wav(folder / name, audio)
            except Exception:
                name = ""
        index.append({
            "file": name,
            "ts": clip.get("ts"),
            "heard": clip.get("heard") or "",
            "primary": clip.get("primary") or "",
            "second": clip.get("second") or "",
            "heard_by": clip.get("heard_by") or "",
            "who": clip.get("who") or "",
        })
    _json(folder / "index.json", index)


def _tail(source: Path, dest: Path) -> None:
    if not source.is_file():
        return
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    dest.write_text(text[-200_000:], encoding="utf-8")


def _json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


_ABOUT = """\
Traza de esta ejecución. No sale del equipo hasta que tú la copies.

registro.txt — lo que muestra la pestaña Depuración.
decisiones.json — qué hizo el asistente con cada frase.
llm.json — la frase que vio el modelo local y el texto que devolvió.
llm-instruccion.txt — las instrucciones de ese modelo.
nube.json — el texto que salió hacia Grok.
ajustes.json — las opciones guardadas, sin la contraseña.
audio/ — el wav de cada frase que el micrófono cerró, y al lado lo que se transcribió.
en-vivo/ — el wav temporal que se iba escribiendo mientras se hablaba.
ear.log y crash.log — si existen, el final de esos registros.
"""
