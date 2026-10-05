[← README.md](../../README.md)

# Voice prints and listeners

Each microphone has its own print. Choosing that microphone uses the print recorded with it. A microphone without one still uses the earlier print, and a new recording on the microphone you will use matches better. A window shows the phrase and what the engine hears. Retry records this phrase again. Next moves on. Leave throws away the audio from this recording. The program saves the raw sound of each phrase with the person. The engine that is listening does not decide whether the phrase was the expected one. From that same sound it builds the voice print, then runs every listening engine over the phrases. The phrases are known, so it writes down how many each engine gets right. The user picks, under Listen, the engine that hears well on that microphone.

There are sixteen different phrases, once each. Several are needed so the print and the percentage come out fine. A take that does not sit with the others is left out of the voice print. The raw sound of all sixteen phrases is saved anyway. If one clear voice does not remain, the person's voice print is not replaced.

**People → Prints** lists every person. Under the name is the number of takes. Beside each installed engine is that person's hit rate, for example `Whisper pequeño (92%)`. It is information: it does not choose the engine. Recording a profile scores every engine. At startup the program adds the hits from every print and keeps the highest engine. It writes that choice on the Debug tab. The engine is changed under **Listen → Listening engine (STT)**. An engine that is not here yet is scored when it is installed, without speaking again. **Record again** repeats the sixteen phrases.

The sound and the print live in `dist/data/`, next to `GrokAssistant.exe`. A rebuild replaces the program and leaves that folder. `dist/data/` is listed in `.gitignore`. The keyboard has no print: there is no microphone.
