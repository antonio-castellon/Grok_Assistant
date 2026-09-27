[Leer en español](README.ES.md) · [Lire en français](README.FR.md) · [Auf Deutsch lesen](README.DE.md)

![Grok mark, with Assistance underneath](docs/img/banner.jpg)

# Grok Assistant

I spent years waiting for the Amazon Echo to become a better listener. It never really became more than a speaker with a light ring, so I decided to build my own assistant for an older person who already keeps a small laptop nearby.

In my case, that person is my father. His eyesight is limited, and he spends many hours on his own. I wanted him to have a voice he could simply talk to — one that could answer questions and explain things without making him find a screen or read small text. That is now possible. Grok on this machine is also the foundation for the features and integrations I plan to add next. For families that are a little more technical and would rather not keep a laptop open, I am building the same assistant for a Raspberry Pi 4 with 4 GB of RAM. I plan to publish that code soon as well, so anyone who prefers a dedicated device can build one.

While the program is running, it can keep listening. Audio stays on the computer and is converted to text locally. Grok only receives text when the assistant has actually been addressed: after a greeting, for a question, for a command beginning with `comando`, or when someone asks for a song. Ordinary conversation stays in the local session. If a command is unclear or misheard, Grok can help interpret it, but the assistant still asks for a `sí` before doing anything.

That is the basic idea. Below you can see the listening window and the tray menu with **Idioma** open.

![The information window, listening, with the live debug underneath](docs/img/app-window.png)

![The tray menu, with the language list open](docs/img/tray-menu.png)

The diagram below shows what happens to a spoken phrase from the moment it is heard.

![How a phrase moves: the ear stays local, and only a question or a repaired order sends text to Grok](docs/img/flow.svg)

## Read on

- [Spanish first, because the house is loud](docs/en/listening.md)
- [Voice prints and listeners](docs/en/prints.md)
- [Sessions and agents](docs/en/sessions.md)
- [Why Grok, and not another chat window](docs/en/why-grok.md)
- [What is actually running](docs/en/pieces.md)
- [What you can say](docs/en/saying.md)
- [Run the executable](docs/en/run.md)
- [Run it from the source tree](docs/en/source.md)
- [What this is](docs/en/what.md)
