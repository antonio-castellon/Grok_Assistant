[← README.md](../../README.md)

# Voice prints and listeners

A voice print is a measurement of the microphone clip, not of the words. Each listener cuts that clip in its own way. Each STT engine — Whisper tiny, Whisper base, Canary, and Windows speech — does not hand the same audio to the print, so a print recorded with one listener does not identify the person when another listener is active.

**Administrador → Huellas** lists every person. Under the name, every listener shows how many takes are saved, or *sin huella* when that listener has none. A listener that is not installed is marked and cannot be recorded yet. Choosing a listener switches the ear and records twelve takes for that ear only.

The file is `dist/data/speakers.json`, next to `GrokAssistant.exe`. A rebuild replaces the program and leaves that folder. `dist/data/` is listed in `.gitignore`, so the prints are not pushed to the repository. The keyboard has no print: there is no microphone clip.
