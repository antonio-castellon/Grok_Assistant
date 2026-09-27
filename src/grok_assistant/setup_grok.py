"""If Grok Build is missing or signed out, explain the fix before the tray starts."""

from __future__ import annotations

import os
import subprocess
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from grok_assistant.grok_cli import GrokCLI, interpret_models

INSTALL_COMMAND = "irm https://x.ai/cli/install.ps1 | iex"


@dataclass(frozen=True)
class GrokStatus:
    state: str
    binary: str | None
    detail: str


def probe() -> GrokStatus:
    binary = GrokCLI.find()
    if not binary:
        return GrokStatus("missing", None, "Grok Build no está instalado.")
    try:
        done = subprocess.run(
            [binary, "models"],
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GrokStatus("broken", binary, str(exc))
    state = interpret_models(done.stdout or "", done.stderr or "", done.returncode)
    detail = (done.stdout or done.stderr or "").strip().splitlines()
    line = detail[0] if detail else state
    return GrokStatus(state, binary, line[:180])


def remember_grok_bin() -> None:
    folder = str(Path.home() / ".grok" / "bin")
    current = os.environ.get("PATH", "")
    if folder.lower() not in current.lower():
        os.environ["PATH"] = folder + os.pathsep + current


def ensure_grok() -> None:
    """Show the setup window only when Grok is missing or not signed in."""
    remember_grok_bin()
    status = probe()
    if status.state == "ready":
        return
    _window(status)


def _window(status: GrokStatus) -> None:
    root = tk.Tk()
    root.title("Grok Assistant")
    root.geometry("640x460")
    root.minsize(520, 380)

    title = ttk.Label(root, text="Hace falta Grok Build", font=("Segoe UI", 16))
    title.pack(anchor="w", padx=16, pady=(16, 4))
    body = ttk.Label(
        root,
        wraplength=600,
        justify="left",
        text=(
            "El asistente se ejecuta solo. Grok Build es el programa que habla con tu cuenta. "
            "Si no está instalado, o si todavía no has iniciado sesión, las preguntas no pueden salir de casa. "
            "Las órdenes locales siguen funcionando."
        ),
    )
    body.pack(anchor="w", padx=16, pady=(0, 8))

    state = tk.StringVar(value=_label(status))
    ttk.Label(root, textvariable=state, font=("Segoe UI", 11)).pack(anchor="w", padx=16)

    command = ttk.Label(root, text=INSTALL_COMMAND, font=("Consolas", 10))
    command.pack(anchor="w", padx=16, pady=(8, 4))

    log = ScrolledText(root, height=10, wrap="word")
    log.pack(fill="both", expand=True, padx=16, pady=8)
    log.insert("end", status.detail + "\n")
    log.configure(state="disabled")

    buttons = ttk.Frame(root)
    buttons.pack(fill="x", padx=16, pady=(0, 16))

    busy = {"on": False}

    def write(line: str) -> None:
        log.configure(state="normal")
        log.insert("end", line.rstrip() + "\n")
        log.see("end")
        log.configure(state="disabled")

    def refresh() -> None:
        remember_grok_bin()
        current = probe()
        state.set(_label(current))
        write(current.detail)
        if current.state == "ready":
            write("Listo. Puedes continuar.")

    def install() -> None:
        if busy["on"]:
            return
        busy["on"] = True
        write("Instalando Grok Build…")

        def work() -> None:
            try:
                done = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", INSTALL_COMMAND],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=False,
                )
                text = ((done.stdout or "") + "\n" + (done.stderr or "")).strip()
                root.after(0, lambda: write(text or f"El instalador terminó con código {done.returncode}."))
            except (OSError, subprocess.TimeoutExpired) as exc:
                root.after(0, lambda: write(str(exc)))
            finally:
                busy["on"] = False
                root.after(0, refresh)

        threading.Thread(target=work, daemon=True).start()

    def sign_in() -> None:
        remember_grok_bin()
        binary = GrokCLI.find()
        if not binary:
            write("Primero instala Grok Build.")
            return
        write("Se abre el inicio de sesión. Termínalo en el navegador y luego pulsa Comprobar.")
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen([binary, "login"], creationflags=flags)

    def go_on() -> None:
        root.destroy()

    ttk.Button(buttons, text="Instalar Grok Build", command=install).pack(side="left")
    ttk.Button(buttons, text="Iniciar sesión", command=sign_in).pack(side="left", padx=8)
    ttk.Button(buttons, text="Comprobar", command=refresh).pack(side="left")
    ttk.Button(buttons, text="Continuar", command=go_on).pack(side="right")
    root.mainloop()


def _label(status: GrokStatus) -> str:
    if status.state == "ready":
        return f"Grok Build está listo. {status.binary}"
    if status.state == "signed_out":
        return f"Grok Build está instalado y falta iniciar sesión. {status.binary}"
    if status.state == "broken":
        return f"Grok Build no responde. {status.binary or ''}"
    return "Grok Build no está instalado."
