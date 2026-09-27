[Leer en español](README.ES.md) · [Lire en français](README.FR.md) · [Auf Deutsch lesen](README.DE.md)

![Grok mark, with Assistance underneath](docs/img/banner.jpg)

# Grok Assistant

I waited years for the Amazon Echo to listen better. It stayed a speaker with a light ring, so I made my own for an older person who already has a small laptop nearby.

In my case that person is my father. His vision is limited, and he spends many hours alone. I wanted a voice that can hold a conversation and explain things, without a screen to hunt for and without small text to read. That is possible now. Grok on this machine is how more features and integrations will arrive. If someone in the family knows a little more and would rather not leave a laptop open, the same assistant is the one I am building on a Raspberry Pi 4 with 4 GB, and I will publish that code soon as well, so it can be cloned by someone who would rather have a device of their own.

It can stay listening while the program is open. The sound remains on the computer. A phrase is turned into text here, and Grok receives that text only when you meant it for the assistant: a hello, then a question, an order that starts with `comando`, or a song you asked for. Everyday talk is written in a local session and stays there. A muddled order can be checked with Grok, and it still waits for a sí before it runs.

That is the whole idea. This is the window while it is listening, and the tray menu with Idioma open.

![The information window, listening, with the live debug underneath](docs/img/app-window.png)

![The tray menu, with the language list open](docs/img/tray-menu.png)

The picture below is the path of one phrase.

![How a phrase moves: the ear stays local, and only a question or a repaired order sends text to Grok](docs/img/flow.svg)

## Spanish first, because the house is loud

Spanish is the language we speak at home, so the assistant starts there. Answers stay short. A long speech is hard to follow when the room is noisy.

The hard part is STT, speech to text. That is the step that turns a voice into words, on this computer. The audio never leaves. The local models that do it, Kroko and Whisper, often hear a word wrong. "Hola" can arrive as "ola". An English name can arrive in Spanish. The rest of the app depends on that text. If the words are wrong, the order is wrong, and the question never reaches Grok.

Kroko is the Spanish ear. Whisper base keeps English names, and it reads French, German, and English. The Idioma menu already switches language. Voice market downloads an ear when you ask.

## Sessions and agents

A session is the notebook of the talk. It stays on this computer. The shared notebook starts again after 24 hours. A notebook with a name stays until you delete it. That notebook is not your Grok account.

An agent is a Grok on your account. You open it on purpose with `comando abrir agente …`. It can remember dates, places, and lists, and it can look things up. That memory stays in the account, so the same agent opens on another computer where you are signed in. Creating one asks for the administrator password.

Saying goodbye (`gracias`, `vale`, `adiós`) ends the talk. It does not close the session. Closing the session goes back to the shared notebook. `comando cerrar agente` goes back to the normal assistant. It does not delete the agent. The agent does not need this laptop to stay on. You still speak to it on purpose.

## Why Grok, and not another chat window

A normal chat can write a program and give it back as text. Someone still has to put that text in the right folder and make it run.

Grok Build is already on this computer, and it is signed in. There is no API key to paste. Open this folder and it can read the assistant, change it, run the tests, and leave the new program here. The idea is the same as [OpenClaw](https://github.com/openclaw/openclaw): the instructions are plain files, so a new step can be written down as a file.

A question about the weather does not change the program. Changing the program is a separate step, and you open it on purpose.

## What is actually running

The diagram further up is the whole product. These are the pieces that implement it.

| Piece | Where it lives | What it is allowed to do |
| --- | --- | --- |
| Ear | `listen.py`, `kroko_ear.py`, `listeners/dictation.ps1` | Turn sound into text on this PC. Kroko streams Spanish locally. Windows Spanish dictation when that recognizer is present. The keyboard is always there. |
| Rules | `brain.py`, `match.py`, `textutil.py` | Decide ignore, local order, or cloud. One wrong character still matches a local order. Two do not. |
| Notebook | `store.py`, `%APPDATA%\GrokAssistant` | Keep sessions, speaker names, and the debug history. The shared session is replaced after 24 hours. |
| Password | `auth.py` | Store a salted hash. The password itself is never written. |
| Mouth | `speech.py`, `scripts/speak.ps1` | Speak with a local voice. Spanish voices are offered first. |
| Music | `music.py` | Play audio through `yt-dlp` and `mpv` when both exist. The ear closes while a song is playing. |
| Cloud door | `hub.py`, `grok_cli.py` | Call the local `grok` command with a finished line of text. There is no audio argument. |
| Agents | `~/.grok/agents` | Definitions on this account. Opening one is a choice. Their memory is not the local notebook. |
| Shell | `tray.py` | Tray icon, information window, debug transcript. Closing a window leaves the program running. |

A phrase ends when the person has stopped. Kroko and the Windows ear close it in under two seconds. While the assistant is speaking, that ear is paused, so the reply is not heard as a new order. The same pause holds for music. Inside a conversation, what was heard goes straight to Grok until goodbye.

Outside a conversation the rules are narrow. More than six words is dropped, unless the line is a real wake or `pon la canción` plus a title, up to sixteen words. Inside a conversation the six-word gate is gone. Sixty seconds with nothing new ends the talk. Time spent waiting for the cloud does not count. Administrator mode lasts five minutes.

Two different calls exist, and they are not interchangeable.

- A garbled order is a classification. One turn, no web search, no tools, a single JSON object (`accion`, `orden`, `texto`). If the repaired line is a known order, the assistant asks sí or no and only then runs it.
- A real question is a conversation. The model may search the web. Tools are limited to that search. The working directory is the assistant's own data folder, so a voice in the kitchen is not standing inside a source tree. The first turn creates a session id. Later turns resume it. Ignored lines are never in that session, because they were never sent.

If an agent is open, the question uses that agent's file and that agent's session. `cerrar agente` returns to the normal assistant. The local notebook stays where it was.

Spoken lines, command words, help, and personalities are in `src/grok_assistant/lang/`. `hellos-es.txt` and `waits-es.txt` are the Spanish lines the voice rotates through. `brain.py` and `hub.py` stay the same.

At startup it says the next hello, then it stops. While it waits for the cloud it says the next short line from the other list. The lists are long so the same line does not come back every morning.

## What you can say

Say `hola grok` or `¿estás ahí?` to start. Outside a conversation, other orders start with `comando`. A phrase longer than six words is ignored, unless it is a real hello or `pon la canción` plus a title (up to sixteen words). Inside a conversation there is no six-word limit. A song does not need the word `comando`. Goodbye stays on this computer and happens at once. While an answer is on the way, you hear one short line, the microphone pauses, and then you hear the answer. The information window has the command list.

The tray icon is the program. Left click opens the window. Right click opens the menu. Closing the window hides it. Quit is Salir, in the window or in the menu.

## Run the executable

There is no installer. `dist/GrokAssistant.exe` is the whole program. Copy it anywhere and double-click it. Python does not have to be installed for that file. A window opens with the live debug — what was heard, and what happens next — and the Grok icon stays in the tray. Closing the window hides it. Quit is the button, or Salir on the tray menu.

If Grok Build is missing, or if you have never signed in, the program stops on a window before the tray. **Instalar Grok Build** runs the official installer:

```powershell
irm https://x.ai/cli/install.ps1 | iex
```

**Iniciar sesión** opens `grok login`, which uses the browser. **Comprobar** asks `grok models` whether the account is ready. **Continuar** starts the assistant anyway, so local orders still work while the cloud is absent. There is no API key to paste in.

To build that executable again from this folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## Run it from the source tree

```powershell
cd C:\DEV.Personal\Grok_Assistant
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m grok_assistant
```

`--console` types what the microphone would have heard, which is useful before a speech engine exists and also useful when you do not want to talk to your desk.

```powershell
.venv\Scripts\python -m grok_assistant --console
```

Data, sessions, the password hash, and the ear log live under `%APPDATA%\GrokAssistant` on Windows and `~/.config/grok-assistant` on Linux. Agent files go to `~/.grok/agents`, the Grok account folder, not this git checkout. The assistant uses its own data folder. It does not work inside a source tree full of projects.

Music needs `yt-dlp` and `mpv`. If they are missing, the first song downloads them. If that fails, the assistant says so in one sentence.

## What this is

A voice for the hours when reading is hard and the house is quiet. The laptop version is for an older person who already has a small computer nearby. The Raspberry Pi 4, with 4 GB, is the same assistant when a laptop should stay closed. The microphone can stay awake. Only a phrase that was meant for the assistant leaves as text.
