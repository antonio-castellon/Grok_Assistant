[← README.md](../../README.md)

# Run it from the source tree

```powershell
cd C:\DEV.Personal\Grok_Assistant
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m grok_assistant
```

`--console` lets you type the text that would normally come from the microphone. It is handy while testing speech support — or simply when you would rather not talk to your desk.

```powershell
.venv\Scripts\python -m grok_assistant --console
```

Voice prints and the raw sound live in `dist/data/`, next to the executable. One person has one print. Each engine is scored from that same sound. Data, sessions, the password hash, and the ear log live under `%APPDATA%\GrokAssistant` on Windows and `~/.config/grok-assistant` on Linux. Agents created here go to `~/.grok/agents`. The menu also shows the ones the signed-in account publishes. Neither lives in this git checkout. The assistant uses its own data folder. It does not work inside a source tree full of projects.

Music needs `yt-dlp` and `mpv`. If they are missing, the first song downloads them. If that fails, the assistant says so in one sentence.
