[← README.DE.md](../../README.DE.md)

# Warum Grok, und nicht ein weiteres Chatfenster

Ein normaler Chat kann Code erzeugen. Danach muss ihn aber immer noch jemand an die richtige Stelle legen, ausführen, testen und daraus eine tatsächlich funktionierende Änderung machen.

Grok Build ist auf diesem Computer bereits installiert und angemeldet. Ein API-Schlüssel muss also nicht kopiert oder eingefügt werden. Öffnet man diesen Projektordner, kann Grok Build den Assistenten prüfen, Änderungen vornehmen, die Tests ausführen und die aktualisierte Version direkt hier ablegen. Der Ansatz ähnelt [OpenClaw](https://github.com/openclaw/openclaw): Anweisungen liegen in einfachen Dateien, sodass sich ein neuer Schritt direkt in einer Datei beschreiben lässt.

Eine normale Frage – etwa nach dem Wetter – verändert das Programm niemals. Codeänderungen laufen über einen eigenen, bewusst gestarteten Ablauf.

## Dieselbe Antwort, mit einer anderen Engine

Dieses Programm ist ein Sprachbegleiter. Mikrofon, Weckname, Stimmabdruck und die Stimme, die antwortet, bleiben auf diesem Computer. Die Reasoning-Engine bekommt nur Text, und nur dann, wenn jemand den Assistenten angesprochen hat.

Heute ist Grok angeschlossen, weil Grok Build auf diesem Rechner bereits installiert und angemeldet ist. Claude, ChatGPT und Codex können eine gesprochene Frage ebenfalls beantworten. In diesem Teil der Arbeit sind die Unterschiede klein. Diese Version ist ein Versuch mit Grok. Wenn er sich bewährt, ist der nächste Schritt derselbe Assistent, gerichtet auf eine andere Reasoning-Engine. Dieser Schritt ist in dieser Version nicht enthalten.

| | Grok Build | Claude Code | Codex | ChatGPT |
| --- | --- | --- | --- | --- |
| Wird von diesem Assistenten aufgerufen | Ja | Nein | Nein | Nein |
| Angemeldet, kein Schlüssel im Programm | Ja, mit `grok login` | Ja, im Browser, oder mit einem API-Schlüssel | Ja, mit dem ChatGPT-Konto, oder mit einem API-Schlüssel | Ja, in der ChatGPT-App |
| Aktuelle Fakten aus dem Web | Ja. Suche und Seitenabruf sind bei einer gesprochenen Frage an | Ja | Ja. Die Suche ist an. Live-Seiten sind ein eigener Schalter | Ja, in ChatGPT |
| Dasselbe Gespräch fortsetzen | Ja | Ja | Ja | Ja, in ChatGPT |
| Dateien auf diesem PC ändern | Nur wenn ein Administrator es erlaubt. Die Shell bleibt aus | Ja. Dafür ist das Werkzeug da | Ja, in einer Sandbox | Nein. Dateien ändert Codex |
| Stimme, Name und Abdruck | Stellt dieser Assistent | Müsste dieser Assistent stellen | Müsste dieser Assistent stellen | ChatGPT Voice ist ein anderes Produkt |
| Wohin die Audio geht | Sie bleibt auf diesem PC. Nur der Text geht hinaus | Dieses Werkzeug hört den Raum nicht | Dieses Werkzeug hört den Raum nicht | Sein Sprachstrom geht zu OpenAI |

Claude ist in dieser Tabelle Claude Code, das Terminalwerkzeug. Der Chat auf claude.ai ist ein anderes Gesprächsfenster. ChatGPT ist die Chat- und Sprach-App. Codex ist das Terminalwerkzeug, das sich mit demselben Konto anmeldet. Gemini CLI und GitHub Copilot CLI gehören zu Claude Code und Codex: man öffnet sie absichtlich, um am Code zu arbeiten. Sie sind nicht die Stimme im Haus.
