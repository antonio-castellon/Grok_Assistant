[← README.DE.md](../../README.DE.md)

# Stimmabdrücke und Ohren

Der Abdruck wird einmal aufgenommen. Das Programm speichert den Ton jeder Phrase roh bei der Person. Aus demselben Ton entsteht der Stimmabdruck, und danach läuft jeder Motor über die Sätze. Die Sätze sind bekannt, also schreibt es auf, wie viele jeder Motor trifft.

Es sind sechzehn verschiedene Sätze, jeder einmal. Mehrere braucht es, damit Abdruck und Prozent fein werden. Eine Aufnahme, die nicht zu den anderen passt, bleibt draußen. Bleibt keine klare Stimme übrig, wird keine zweite Person gespeichert.

**Administrador → Huellas** listet jede Person. Unter dem Namen steht die Zahl der Aufnahmen. Neben jedem installierten Motor steht die Trefferquote, zum Beispiel `Whisper pequeño (92%)`. Der Motor in Gebrauch ist der mit dem höchsten Prozentwert. Ein Motor, der noch fehlt, wird beim Installieren bewertet, ohne noch einmal zu sprechen. **Neu aufnehmen** wiederholt die sechzehn Sätze. Einen Motor zu wählen startet keine neue Aufnahme.

Ton und Abdruck liegen in `dist/data/`, neben `GrokAssistant.exe`. Ein neuer Bau ersetzt das Programm und lässt diesen Ordner stehen. `dist/data/` steht in `.gitignore`. Die Tastatur hat keinen Abdruck: es gibt kein Mikrofon.
