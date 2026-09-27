![Project banner](docs/img/banner.jpg)

# Grok Assistant

I waited years for the Echo to improve.

It did not. The light ring changed color a few times, the shopping suggestions got more confident, and the thing on the shelf remained a cylinder with the conversational range of a polite toaster. Meanwhile the phone, which already lives in my pocket and hears everything it is allowed to hear, still treats a microphone like a controlled substance. An app may listen for a moment, if it asks nicely, if the operating system is in the mood, and if nobody in Cupertino or Mountain View has decided that “always” is a dirty word.

So this is another experiment. The first one sits on a Raspberry Pi, because apparently the way to get a microphone that stays awake is to give a tiny computer a fan and a grudge. This repository is the same assistant standing up on a normal PC. No framebuffer. No touchscreen the size of a sandwich. No GPIO pins. A tray icon, an information window, and a debug transcript. The pins are imaginary. The attitude is not.

## The scandal, which is also the point

It listens all the time.

That is the whole feature the phones will not sell you. The microphone stays open while the program is running. Audio does not go anywhere. There is no stream to Grok, no stream to a speech corporation, no “short clip uploaded for quality.” A phrase ends here, on the machine, and then a very suspicious little set of rules decides whether **the text** may leave.

Most of the time the answer is no.

You can argue about football, the dying plant, the neighbor, or whether the Echo still deserves the shelf. That stays in the local session, a notebook on this computer. It does not get a boarding pass. Grok in the cloud hears a phrase only when you actually talked to the assistant: you woke it (`hola grok`, or the close mishearings, or “¿estás ahí?”), and the next thing you said was a question, or you gave an order that starts with `comando`, or you asked for a song. The wake itself is not uploaded. Words spoken in the same breath as the wake are not uploaded either. The assistant says “Hola.” and waits, like someone who was taught manners by a person who was tired of chatbots.

A garbled order can be shown to Grok for a repair, and even then it does not run until you say sí. The cloud is allowed to be clever. It is not allowed to be spontaneous with the power button.

```
sala  ->  oído local  ->  ¿me lo dijiste a mí?
                | no                 | sí
                v                    v
         cuaderno de casa     texto, y solo el texto
         (no viaja)           a tu cuenta de Grok
```

## Two bodies, one unreasonable request

The Pi is the other body of the same idea: a box in the room that does not have to ask an operating system for permission to exist. This repository does not contain that box. It does not contain the little screen, the fan that cannot be slowed down, the Wi-Fi boot opera, or the Pi's administrator key. Shutdown here, after you say sí, is the normal shutdown of the computer you are sitting at. The password is one you type in the tray. The file on disk is a salted hash. There is no password in the source, and there will not be a clever default. Clever defaults are how cylinders get into your shopping list.

Spoken language is Spanish. Answers are short, because this is a voice in a room and not a blog. The PC edition speaks with whatever Spanish voice the machine already has (Windows speech, or espeak on Linux). The Pi has a particular set of Piper voices. If you install local recognizers later, the names match: Kroko, Whisper, base, Canary. Until then the ear you can always use is the keyboard in the debug window, and Windows Spanish dictation if that language pack is actually installed. A cloud recognizer is not a fallback. That would make the whole privacy story a joke, and not the funny kind.

## The employee who does not need your hardware

A local session is a notebook. It lives in this machine's data folder. The shared one is thrown away and started again after 24 hours. A named one stays until you delete it. None of that notebook is the Grok account.

An agent is the other creature. You open it on purpose (`comando abrir agente …`). Creating one asks for the administrator password, because “spin up someone who remembers things and can look at the internet” is not a party trick for whoever walks past the microphone. The agent is a Grok agent on your account, not a renamed session. It can keep dates, places, and lists, and it can search. That memory stays with the account, so another machine where you are already signed in can open the same agent.

This is the part the Echo never offered and the phone will not host. The agent does not need the Pi's fan, this tray icon, or a microphone that an operating system has agreed to unlock. The living-room computer is a doorbell. The employee lives with the account. Unplug the doorbell and the employee is still on the payroll: you reach them from any other signed-in Grok, whenever you feel like working, including at an hour when every device in the house is doing its finest impression of a brick. The doorbell does not have to stay awake for the office to exist. The office, rudely, does not hear the room. You still have to talk to it on purpose. Always-on was never supposed to mean always-sharing. The cylinder had one idea about that. It was the wrong idea, and it came with a light ring.

`comando cerrar agente` comes back to the normal assistant. It does not delete the agent, and it does not end the conversation. Closing the conversation (`gracias`, `vale`, `adiós`, `cierra conversación`) does not close the session. Closing the session comes back to the shared notebook and, if you were talking, stops. The screen, or the tray, goes back to waiting. Ordinary life resumes, un-uploaded.

## What you can say

Wake with `hola grok` or `¿estás ahí?`. Outside a conversation, every other order starts with `comando`, and a finished phrase longer than six words is ignored unless it is a real wake or `pon la canción` plus a title (up to sixteen words). Inside a conversation there is no six-word limit. A song can be asked for without the word `comando`. Goodbye is local and immediate. While an answer is being fetched, you hear one short line from a long rotating list, the microphone takes a break, and then you hear the answer. Startup speaks the next line from a different list, the hellos, and then it shuts up. No tour. No command dump. The information window has the list, for people who prefer reading to being lectured by a speaker.

The tray is the application. Left click opens the information window. Right click opens the menu: pause, information, debug, recognizer, voice, model, sessions, administrator password, quit. Closing a window does not quit. Quit is a menu item, because some of us have been trained badly by years of “are you sure you want to hide the window and pretend that is an exit.”

## Run it

You need Python 3.11 or newer, and the `grok` command already logged in as you. This project does not want an API key in a `.env`. If `grok` is missing, local orders still work and the cloud gets a one-line apology.

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
