"""Type what the microphone would have heard. Useful before a speech engine is installed."""

from __future__ import annotations

import sys

from grok_assistant.hub import build
from grok_assistant.tray import shutdown_machine


def run() -> None:
    hub = build()
    print(hub.startup())
    print("Escribe lo que dirías. Ctrl+Z y Enter cierra.")
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        result = hub.run(text)
        for said in result.spoken:
            print(said)
        if any(item[0] == "ask_password" for item in result.effects):
            password = input("contraseña: ").strip()
            follow = hub.submit_password(password) if password and password.lower() != "no" else hub.cancel_password()
            for said in follow.spoken:
                print(said)
            result.effects.extend(follow.effects)
        if any(item[0] == "shutdown" for item in result.effects):
            shutdown_machine()
            return
