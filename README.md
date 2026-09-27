![Grok mark, with Assistance underneath](docs/img/banner.jpg)

# Grok Assistant

A small voice assistant for the house.

I waited a long time for the living-room speaker to become a better listener. It stayed the same, so I made my own. The first one runs on a Raspberry Pi. This repository is the PC version: a window, a tray icon, and a log of what was heard.

It can stay listening while the program is open. The sound remains on the computer. A phrase is turned into text here, and Grok receives that text only when you meant it for the assistant: a hello, then a question, an order that starts with `comando`, or a song you asked for. Everyday talk is written in a local session and stays there. A muddled order can be checked with Grok, and it still waits for a sí before it runs.

That is the whole idea. The picture below is the path of one phrase.

![How a phrase moves: the ear stays local, and only a question or a repaired order sends text to Grok](docs/img/flow.svg)

## Spanish first, because the house is loud

The first language is Spanish. That is the language we actually speak at home, so it is the honest place to start an experiment. A quiet desk and a headset would make any assistant look clever. The kitchen does not. People talk across each other, the television stays on, someone asks for a song while someone else is already in the middle of a sentence. I want that noise. The test is whether a wake and a short order still survive a real room, and whether everything else stays on the machine when the room is messy.

Answers stay short on purpose. A voice in a noisy house that recites a paragraph has already lost.

French, German, and English come later, as their own versions. Each one means adapting the ear, the mouth, and the voices: the speech-to-text engine, the text-to-speech engine, and the list of voices that `otra voz` walks through. The hellos, the waiting lines, and the command words travel with the language. The rule underneath does not. A phrase still leaves only when it was said to the assistant.

On this PC the mouth is whatever Spanish voice Windows already has, or a Piper voice you pick in Mercado, or espeak on Linux. The Pi has its own Piper set. The microphone ear for Spanish is Kroko: a local streaming model. Audio never leaves the machine. Mercado downloads it when you ask; once the folder is on disk and the saved ear was still the keyboard, the assistant starts Kroko on its own. The keyboard in the debug window stays available. Windows Spanish dictation is the desktop recognizer. When that language is missing, Escucha and Mercado install it through Windows itself. Whisper, base, and Canary are the other ears, each one waiting for its own model. A cloud recognizer is not the stand-in. Uploading the room in order to test a noisy room would throw away the experiment.

## The employee who does not need your hardware

A local session is a notebook. It lives in this machine's data folder. The shared one is thrown away and started again after 24 hours. A named one stays until you delete it. None of that notebook is the Grok account.

An agent is the other creature. You open it on purpose (`comando abrir agente …`). Creating one asks for the administrator password, because “spin up someone who remembers things and can look at the internet” is not a party trick for whoever walks past the microphone. The agent is a Grok agent on your account, not a renamed session. It can keep dates, places, and lists, and it can search. That memory stays with the account, so another machine where you are already signed in can open the same agent.

This is the part the Echo never offered and the phone will not host. The agent does not need the Pi's fan, this tray icon, or a microphone that an operating system has agreed to unlock. The living-room computer is a doorbell. The employee lives with the account. Unplug the doorbell and the employee is still on the payroll: you reach them from any other signed-in Grok, whenever you feel like working, including at an hour when every device in the house is doing its finest impression of a brick. The doorbell does not have to stay awake for the office to exist. The office, rudely, does not hear the room. You still have to talk to it on purpose. Always-on was never supposed to mean always-sharing. The cylinder had one idea about that. It was the wrong idea, and it came with a light ring.

`comando cerrar agente` comes back to the normal assistant. It does not delete the agent, and it does not end the conversation. Closing the conversation (`gracias`, `vale`, `adiós`, `cierra conversación`) does not close the session. Closing the session comes back to the shared notebook and, if you were talking, stops. The screen, or the tray, goes back to waiting. Ordinary life resumes, un-uploaded.

## Why Grok, which is a workshop and not another chat window

ChatGPT will write a program. Claude will write a careful one. Both of them do that in a window that lives somewhere else, and then hand the result back as text. Someone still has to know what a folder is, which file is the real one, and which command turns a polite suggestion into software that actually runs. That someone was always going to be me, and I was already tired.

What I wanted is the shape of [OpenClaw](https://github.com/openclaw/openclaw): a free agent that stays on the computer, grows by writing its own instructions, and does the software work so the person who owns the house does not have to become a developer. OpenClaw's skills are plain files, which is why the agent can learn a new trick by writing one down. Grok Build is that idea with the claws already on this machine. The `grok` command is installed here. It is logged in. Point it at this folder and it can read the assistant, change it, run the tests, and leave the next version in the same place. The voice program is the doorbell. Grok Build is the workshop behind the house.

That is also why the thing can configure itself once the install is done. There is no API key to go hunting for, and no form that asks which model the internet is excited about this week. The assistant finds `grok` on the path, asks that command which models it can really run, and uses the Spanish voice the computer already has. The configuration is the fact that Grok is installed. After that, anyone who can follow the steps further down can open this folder with Grok and say, in ordinary language, what the house still needs. A louder greeting. A new order. A recognizer. Grok writes the change locally and produces the new program here. The source is public so they can have it. The local agent is what makes "anyone" include people who have never opened a programming book. They install it. They talk. The claws do the development.

A question about the weather still does not get to rewrite the computer. That would be the cylinder's bad idea with better grammar. The workshop has its own door, and you open it on purpose, the same way you open an agent. One install, then the assistant can grow without a software career in the room. That is the whole bet.

## What is actually running

The diagram further up is the whole product. These are the pieces that implement it.

| Piece | Where it lives | What it is allowed to do |
| --- | --- | --- |
| Ear | `listen.py`, `listeners/dictation.ps1` | Turn sound into text on this PC. Windows Spanish dictation, if the language pack is there, or the keyboard. |
| Rules | `brain.py`, `match.py`, `textutil.py` | Decide ignore, local order, or cloud. One wrong character still matches a local order. Two do not. |
| Notebook | `store.py`, `%APPDATA%\GrokAssistant` | Keep sessions, speaker names, and the debug history. The shared session is replaced after 24 hours. |
| Password | `auth.py` | Store a salted hash. The password itself is never written. |
| Mouth | `speech.py`, `scripts/speak.ps1` | Speak with a local voice. Spanish voices are offered first. |
| Music | `music.py` | Play audio through `yt-dlp` and `mpv` when both exist. The ear closes while a song is playing. |
| Cloud door | `hub.py`, `grok_cli.py` | Call the local `grok` command with a finished line of text. There is no audio argument. |
| Agents | `~/.grok/agents` | Definitions on this account. Opening one is a choice. Their memory is not the local notebook. |
| Shell | `tray.py` | Tray icon, information window, debug transcript. Closing a window leaves the program running. |

A phrase ends when the recognizer decides the person has stopped. Kroko and the Windows ear use about 3.5 seconds of trailing silence. While the assistant is speaking, that ear is paused, so the reply is not heard as a new order. The same pause holds for music.

Outside a conversation the rules are narrow. More than six words is dropped, unless the line is a real wake or `pon la canción` plus a title, up to sixteen words. Inside a conversation the six-word gate is gone. Sixty seconds with nothing new ends the talk. Time spent waiting for the cloud does not count. Administrator mode lasts five minutes.

Two different calls exist, and they are not interchangeable.

- A garbled order is a classification. One turn, no web search, no tools, a single JSON object (`accion`, `orden`, `texto`). If the repaired line is a known order, the assistant asks sí or no and only then runs it.
- A real question is a conversation. The model may search the web. Tools are limited to that search. The working directory is the assistant's own data folder, so a voice in the kitchen is not standing inside a source tree. The first turn creates a session id. Later turns resume it. Ignored lines are never in that session, because they were never sent.

If an agent is open, the question uses that agent's file and that agent's session. `cerrar agente` returns to the normal assistant. The local notebook stays where it was.

The spoken Spanish lives in a few places, which is what a later language has to replace: `hellos-es.txt`, `waits-es.txt`, the command words in `match.py`, the help lines, and the prompts in `prompts.py`. The recognizer culture and the voice list change with them. `brain.py` and `hub.py` stay. That is the whole plan for French, German, and English. Same door policy. A new ear, a new mouth, and new voices.

Startup speaks the next line from the hello list and then stops talking. A cloud wait speaks the next line from the other list. The two lists are long so the same joke does not return every morning.

## What you can say

Wake with `hola grok` or `¿estás ahí?`. Outside a conversation, every other order starts with `comando`, and a finished phrase longer than six words is ignored unless it is a real wake or `pon la canción` plus a title (up to sixteen words). Inside a conversation there is no six-word limit. A song can be asked for without the word `comando`. Goodbye is local and immediate. While an answer is being fetched, you hear one short line from a long rotating list, the microphone takes a break, and then you hear the answer. Startup speaks the next line from a different list, the hellos, and then it shuts up. No tour. No command dump. The information window has the list, for people who prefer reading to being lectured by a speaker.

The tray is the application. Left click opens the information window. Right click opens the menu: pause, information, debug, recognizer, voice, model, sessions, administrator password, quit. Closing a window does not quit. Quit is a menu item, because some of us have been trained badly by years of “are you sure you want to hide the window and pretend that is an exit.”

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

Data, sessions, the password hash, and the local ear log live under `%APPDATA%\GrokAssistant` on Windows and `~/.config/grok-assistant` on Linux. Agent definitions are written to `~/.grok/agents`, which is the Grok account folder, not this git checkout. Do not point the assistant's working directory at a source tree full of projects. It already refuses, and uses its own data folder, because a voice in the kitchen should not discover a sudden interest in refactoring.

Music wants `yt-dlp` and `mpv` on the PATH. Without them, the assistant admits it, in one sentence, and does not pretend to hum.

## What this is

An experiment, filed next to the others. The Pi proved the microphone could stay awake without a product manager. This one asks whether the same rules can live in a tray icon without becoming a cloud microphone that happens to have a desktop shortcut.

If it works, the house gets a voice that knows when to shut up. If it does not, the Echo remains on the shelf, collecting the dust it spent a decade earning, and I will have learned something slightly more useful than the changelog of a light ring.
