[← README.md](../../README.md)

# Spanish first, because it was developed and tested in Spanish first

Spanish is the language we speak at home, so that is where the assistant starts. Replies are deliberately short: when the room is noisy, a concise answer is much easier to follow than a long monologue.

The hardest part is STT — speech-to-text — because everything else depends on getting those first words right. Audio is transcribed locally and never leaves the computer. The STT engine does the transcription, but like any local speech model it can mishear things: `hola` may become `ola`, or an English name may be interpreted as Spanish. If the transcription is wrong, a command may no longer match and a question may never make it to Grok.

The streaming STT engine handles Spanish listening at home. Whisper base, another STT engine, is useful for English names and also supports French, German, and English. You can switch languages from the **Idioma** menu, and Voice Market can download the required speech model when needed.
