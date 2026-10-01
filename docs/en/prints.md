[← README.md](../../README.md)

# Voice prints and listeners

The print is recorded once. The program saves the raw sound of each phrase with the person. From that same sound it builds the voice print, then runs every listening engine over the phrases. The phrases are known, so it writes down how many each engine gets right.

There are sixteen different phrases, once each. Several are needed so the print and the percentage come out fine. A take that does not sit with the others is left out. If one clear voice does not remain, the program does not save a second person.

**Administrador → Huellas** lists every person. Under the name is the number of takes. Beside each installed engine is the hit rate, for example `Whisper pequeño (92%)`. The engine in use is the one with the highest percent. An engine that is not here yet is scored when it is installed, without speaking again. **Record again** repeats the sixteen phrases. Choosing an engine does not start another recording.

The sound and the print live in `dist/data/`, next to `GrokAssistant.exe`. A rebuild replaces the program and leaves that folder. `dist/data/` is listed in `.gitignore`. The keyboard has no print: there is no microphone.
