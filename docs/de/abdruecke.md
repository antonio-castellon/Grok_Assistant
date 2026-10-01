[← README.DE.md](../../README.DE.md)

# Stimmabdrücke und Ohren

Der Abdruck wird einmal aufgenommen. Das Programm speichert den Ton jeder Phrase roh bei der Person. Der Motor, der zuhört, entscheidet nicht, ob der Satz der erwartete war. Aus demselben Ton entsteht der Stimmabdruck, und danach läuft jeder Motor über die Sätze. Die Sätze sind bekannt, also schreibt es auf, wie viele jeder Motor trifft. Unter Hören wählt man den Motor, der an diesem Mikrofon gut hört.

Es sind sechzehn verschiedene Sätze, jeder einmal. Mehrere braucht es, damit Abdruck und Prozent fein werden. Eine Aufnahme, die nicht zu den anderen passt, bleibt aus dem Stimmabdruck draußen. Der Ton der sechzehn Sätze wird trotzdem gespeichert. Bleibt keine klare Stimme übrig, wird der Abdruck der Person nicht ersetzt.

**Personen → Stimmabdrücke** listet jede Person. Unter dem Namen steht die Zahl der Aufnahmen. Neben jedem installierten Motor steht die Trefferquote dieser Person, zum Beispiel `Whisper pequeño (92%)`. Das ist nur Auskunft: es wählt den Motor nicht. Eine Aufnahme bewertet alle Motoren. Beim Start zählt das Programm die Treffer aller Abdrücke zusammen und behält den höchsten Motor. Das steht im Debug-Fenster. Der Motor wird unter **Hören → Hörmotor (STT)** gewechselt. Ein Motor, der noch fehlt, wird beim Installieren bewertet, ohne noch einmal zu sprechen. **Neu aufnehmen** wiederholt die sechzehn Sätze.

Ton und Abdruck liegen in `dist/data/`, neben `GrokAssistant.exe`. Ein neuer Bau ersetzt das Programm und lässt diesen Ordner stehen. `dist/data/` steht in `.gitignore`. Die Tastatur hat keinen Abdruck: es gibt kein Mikrofon.
