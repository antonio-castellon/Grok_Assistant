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
    "Eres un proceso local. No buscas en internet. No conversas. No reescribes la frase.\n"
    "Miras el texto tal como lo entregó el reconocedor de voz. Decides solo esto: "
    "si es un comando de la lista, o una variación mal oída de uno de ellos.\n"
    "Respondes un único JSON con las claves accion y orden. Sin explicar. Sin repetir la frase.\n"
    "El mensaje dice el nombre del asistente y si la conversación está abierta o cerrada.\n"
    "Si la conversación está cerrada y la frase le saluda, aunque el oído deforme el nombre, "
    "accion es \"saludo\" y orden es \"\".\n"
    "Si es un comando o una variación, accion es \"comando\" y orden es la línea estricta, sin cambiar el sentido.\n"
    "Si cierra la conversación (gracias, nada gracias, ok, vale, adiós, cierra, hasta luego, o una variación), "
    "accion es \"cierre\" y orden es \"gracias\", \"adios\" o \"vale\".\n"
    "Si no es un comando ni un cierre, accion es \"texto\" y orden es \"\". El texto original se queda como está.\n"
    "No inventes órdenes.\n"
    "Lista:\n"
    "subir volumen, bajar volumen, otra voz, voz N, pon cancion TITULO,\n"
    "pausa musica, seguir musica, para la musica, otro reconocedor,\n"
    "reconocedor teclado, reconocedor windows, reconocedor kroko, reconocedor whisper, reconocedor base, reconocedor canary,\n"
    "listar sesiones, crear sesion NOMBRE, abrir sesion NOMBRE, cerrar sesion, borrar sesion NOMBRE,\n"
    "listar agentes, abrir agente NOMBRE, crear agente NOMBRE, cerrar agente,\n"
    "ayuda, prueba, identifica mi voz, lista las personas, borra NOMBRE, modo administrador."
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
    if accion not in {"ignorar", "comando", "pregunta", "texto", "cierre", "saludo"}:
        return None
    return {
        "accion": accion,
        "orden": str(data.get("orden") or "").strip(),
        "texto": str(data.get("texto") or "").strip(),
    }


class LocalMind:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or default_data_dir()
        self.selected = ""
        self.wake_name = ""
        self._server: subprocess.Popen | None = None

    def available(self) -> bool:
        folder = self.data_dir / "llm"
        return any(folder.glob("*.gguf")) and _llama_exe(folder) is not None

    def interpret(self, phrase: str, in_conversation: bool) -> dict | None:
        if not self.available():
            return None
        if not self._ensure_server():
            return None
        name = " ".join((self.wake_name or "grok").split()) or "grok"
        state = "abierta" if in_conversation else "cerrada"
        user = f"Nombre: {name}. Conversación: {state}.\nFrase:\n{phrase}"
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
        parsed = parse_intent(str(content))
        if parsed:
            return parsed
        return {"accion": "ilegible", "orden": "", "texto": ""}

    def _ensure_server(self) -> bool:
        if self._healthy():
            return True
        folder = self.data_dir / "llm"
        exe = _llama_exe(folder)
        model = self._model_file(folder)
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

    def select(self, filename: str) -> None:
        if filename == self.selected:
            return
        self.selected = filename
        if self._server is not None and self._server.poll() is None:
            self._server.kill()
        self._server = None

    def _model_file(self, folder: Path) -> Path | None:
        if self.selected:
            chosen = folder / self.selected
            if chosen.exists():
                return chosen
        return next(folder.glob("*.gguf"), None)

    def _healthy(self) -> bool:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=0.4) as response:
                return response.status == 200
        except (OSError, urllib.error.URLError):
            return False
