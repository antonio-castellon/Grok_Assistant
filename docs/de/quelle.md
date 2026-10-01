[← README.DE.md](../../README.DE.md)

# Aus dem Quellbaum starten

```powershell
cd C:\DEV.Personal\Grok_Assistant
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m grok_assistant
```

Mit `--console` lässt sich der Text eintippen, der normalerweise vom Mikrofon kommen würde. Das ist praktisch zum Testen der Spracherkennung – oder einfach dann, wenn man gerade nicht mit dem Schreibtisch sprechen möchte.

```powershell
.venv\Scripts\python -m grok_assistant --console
```

Stimmabdrücke und der Roh-Ton liegen in `dist/data/`, neben der Programmdatei. Eine Person hat einen Abdruck. Jeder Motor wird mit demselben Ton bewertet. Daten, Sitzungen, der Passwort-Hash und das Ohr-Protokoll liegen unter `%APPDATA%\GrokAssistant` unter Windows und unter `~/.config/grok-assistant` unter Linux. Hier angelegte Agenten gehen nach `~/.grok/agents`. Das Menü zeigt außerdem die, die das angemeldete Konto veröffentlicht. Beides liegt nicht in dieser Git-Kopie. Der Assistent benutzt seinen eigenen Datenordner. Er arbeitet nicht in einem Quellbaum voller Projekte.

Musik braucht `yt-dlp` und `mpv`. Fehlen sie, lädt das erste Lied sie herunter. Schlägt das fehl, sagt der Assistent es in einem Satz.
