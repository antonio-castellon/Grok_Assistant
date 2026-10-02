[← README.md](../../README.md)

# Why Grok, and not another chat window

A normal chat can generate code, but someone still has to put that code in the right place, run it, test it, and turn it into a working change.

Grok Build is already installed and signed in on this computer, so there is no API key to copy around. Open this project folder and it can inspect the assistant, make changes, run the tests, and leave the updated program here. The approach is similar to [OpenClaw](https://github.com/openclaw/openclaw): instructions live in ordinary files, which makes adding a new step as simple as describing it in a file.

Normal questions — asking about the weather, for example — never modify the program. Code changes are a separate, deliberate workflow that you have to open explicitly.

## The same answer, from another engine

This program is a voice companion. The microphone, the wake name, the voice print, and the voice that answers all live on this computer. The reasoning engine receives only text, and only when someone has addressed the assistant.

Grok is the engine wired in today, because Grok Build is already installed and signed in here. Claude, ChatGPT, and Codex can answer a spoken question too. On that part of the job the differences are small. This release is an experiment with Grok. If it holds up, the next step is the same assistant pointed at another reasoning engine. That step is not in this version.

| | Grok Build | Claude Code | Codex | ChatGPT |
| --- | --- | --- | --- | --- |
| Called by this assistant | Yes | No | No | No |
| Signed in, no API key stored here | Yes, with `grok login` | Yes, in the browser, or with an API key | Yes, with a ChatGPT account, or with an API key | Yes, in the ChatGPT app |
| Current facts from the web | Yes. Search and page fetch are on for a spoken question | Yes | Yes. Search is on. Live pages are a separate switch | Yes, inside ChatGPT |
| Continue the same conversation | Yes | Yes | Yes | Yes, inside ChatGPT |
| Change files on this PC | Only after an administrator allows it. The shell stays off | Yes. That is what the tool is for | Yes, inside a sandbox | No. Codex is the tool that edits files |
| Voice, wake name, voice print | Provided by this assistant | This assistant would have to provide them | This assistant would have to provide them | ChatGPT Voice is a different product |
| Where the audio goes | It stays on this PC. Only the text leaves | That tool does not hear the room | That tool does not hear the room | Its voice stream goes to OpenAI |

Claude, in this table, is Claude Code, the terminal tool. The claude.ai chat is another conversation window. ChatGPT is the chat and voice app. Codex is the terminal tool that signs in with that same account. Gemini CLI and GitHub Copilot CLI sit with Claude Code and Codex: they are opened on purpose to work on code. They are not the voice in the room.
