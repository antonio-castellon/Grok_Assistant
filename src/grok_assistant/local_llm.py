"""A small model on this PC. It sorts the phrase before any cloud call."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from grok_assistant.marketplace import _llama_exe
from grok_assistant.paths import default_data_dir
from grok_assistant.quiet import no_window

PORT = 8099
SYSTEM = (
    "Eres un clasificador local. No buscas en internet. Respondes solo un JSON con las claves "
    "accion, orden y texto. accion es ignorar, comando o pregunta. "
    "Si es una orden conocida, orden es la línea estricta y texto es vacío. "
    "Si es una pregunta para el asistente, orden es vacío y texto es la pregunta limpia, corta. "
    "Si es ruido o charla de la sala, accion es ignorar. "
    "Órdenes: subir volumen, bajar volumen, otra voz, voz N, pon cancion TITULO, "
    "pausa musica, seguir musica, para la musica, otro reconocedor, "
    "listar sesiones, abrir sesion NOMBRE, cerrar sesion, "
    "listar agentes, abrir agente NOMBRE, cerrar agente, ayuda, prueba."
)


def parse_intent(raw: str) -> dict | None:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "accion" not in data:
        return None
    accion = str(data.get("accion") or "").strip().lower()
    if accion not in {"ignorar", "comando", "pregunta"}:
        return None
    return {
        "accion": accion,
        "orden": str(data.get("orden") or "").strip(),
        "texto": str(data.get("texto") or "").strip(),
    }


class LocalMind:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or default_data_dir()
        self._server: subprocess.Popen | None = None

    def available(self) -> bool:
        folder = self.data_dir / "llm"
        return any(folder.glob("*.gguf")) and _llama_exe(folder) is not None

    def interpret(self, phrase: str, in_conversation: bool) -> dict | None:
        if not self.available():
            return None
        if not self._ensure_server():
            return None
        user = phrase if in_conversation else f"Fuera de conversación. Frase: {phrase}"
        body = json.dumps({
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": 120,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{PORT}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.load(response)
        except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return None
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None
        return parse_intent(str(content))

    def _ensure_server(self) -> bool:
        if self._healthy():
            return True
        folder = self.data_dir / "llm"
        exe = _llama_exe(folder)
        model = next(folder.glob("*.gguf"), None)
        if exe is None or model is None or exe.name != "llama-server.exe":
            server = next(folder.rglob("llama-server.exe"), None)
            exe = server or exe
        if exe is None or model is None or "server" not in exe.name:
            return False
        self._server = subprocess.Popen(
            [str(exe), "-m", str(model), "--host", "127.0.0.1", "--port", str(PORT), "-c", "2048"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **no_window(),
        )
        for _ in range(40):
            if self._healthy():
                return True
            if self._server.poll() is not None:
                return False
            import time
            time.sleep(0.25)
        return False

    def _healthy(self) -> bool:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=0.4) as response:
                return response.status == 200
        except (OSError, urllib.error.URLError):
            return False
