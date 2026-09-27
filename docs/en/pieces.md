[← README.md](../../README.md)

# What is actually running

The diagram above captures the whole product at a glance. Underneath it are the components that make the assistant work.

| Piece | Where it lives | What it is allowed to do |
| --- | --- | --- |
| Ear | `listen.py`, `kroko_ear.py`, `listeners/dictation.ps1` | Turn sound into text on this PC. Kroko streams Spanish locally. Windows Spanish dictation when that recognizer is present. The keyboard is always there. |
| Rules | `brain.py`, `match.py`, `textutil.py` | Decide ignore, local order, or cloud. One wrong character still matches a local order. Two do not. |
| Notebook | `store.py`, `%APPDATA%\GrokAssistant` | Keep sessions, speaker names, and the debug history. The shared session is replaced after 24 hours. |
| Password | `auth.py` | Store a salted hash. The password itself is never written. |
| Mouth | `speech.py`, `scripts/speak.ps1` | Speak with a local voice. Spanish voices are offered first. |
| Music | `music.py` | Play audio through `yt-dlp` and `mpv` when both exist. While a song plays, the microphone stays open and only follows a print recorded with the listener that is active. |
| Cloud door | `hub.py`, `grok_cli.py` | Call the local `grok` command with a finished line of text. There is no audio argument. |
| Agents | `~/.grok/agents` | Definitions on this account. Opening one is a choice. Their memory is not the local notebook. |
| Shell | `tray.py` | Tray icon, information window, debug transcript. Closing a window leaves the program running. |

A phrase is considered finished once the speaker stops. Kroko and Windows speech recognition usually close it in under two seconds. The microphone pauses while the assistant is speaking, so its own voice is not mistaken for a new command. While a song plays it stays open and only follows a print from the active listener. See [Voice prints and listeners](prints.md). Once a conversation has started, recognized speech goes directly to Grok until the user says goodbye.

Outside an active conversation, the assistant is intentionally conservative. Phrases longer than six words are ignored unless they are a valid wake phrase or `pon la canción` followed by a title, which may be up to sixteen words. Once a conversation is active, the six-word limit disappears. Sixty seconds of inactivity ends the conversation; time spent waiting for a cloud response does not count toward that timeout. Administrator mode remains active for five minutes.

There are two distinct ways Grok is called, and they serve different purposes.

- A garbled order is a classification. One turn, no web search, no tools, a single JSON object (`accion`, `orden`, `texto`). If the repaired line is a known order, the assistant asks sí or no and only then runs it.
- A real question is a conversation. The model may search the web. Tools are limited to that search. The working directory is the assistant's own data folder, so a voice in the kitchen is not standing inside a source tree. The first turn creates a session id. Later turns resume it. Ignored lines are never in that session, because they were never sent.

If an agent is open, the question uses that agent's file and that agent's session. `cerrar agente` returns to the normal assistant. The local notebook stays where it was.

Spoken lines, command words, help, and personalities are in `src/grok_assistant/lang/`. `hellos-es.txt` and `waits-es.txt` are the Spanish lines the voice rotates through. `brain.py` and `hub.py` stay the same.

At startup, the assistant picks the next greeting from the list and then starts listening. While it waits for a cloud response, it uses the next short waiting phrase. Both lists are deliberately long so the assistant does not greet you with the same sentence every morning.
