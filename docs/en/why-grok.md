[← README.md](../../README.md)

# Why Grok, and not another chat window

A normal chat can generate code, but someone still has to put that code in the right place, run it, test it, and turn it into a working change.

Grok Build is already installed and signed in on this computer, so there is no API key to copy around. Open this project folder and it can inspect the assistant, make changes, run the tests, and leave the updated program here. The approach is similar to [OpenClaw](https://github.com/openclaw/openclaw): instructions live in ordinary files, which makes adding a new step as simple as describing it in a file.

Normal questions — asking about the weather, for example — never modify the program. Code changes are a separate, deliberate workflow that you have to open explicitly.
