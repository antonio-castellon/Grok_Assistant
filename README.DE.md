[Read in English](README.md) · [Leer en español](README.ES.md) · [Lire en français](README.FR.md)

![Grok-Zeichen, darunter Assistance](docs/img/banner.jpg)

# Grok Assistant

Jahrelang habe ich darauf gewartet, dass der Amazon Echo wirklich besser zuhören lernt. Am Ende blieb er vor allem ein Lautsprecher mit einem Lichtring. Also habe ich beschlossen, meinen eigenen Assistenten zu bauen – für einen älteren Menschen, der bereits einen kleinen Laptop in der Nähe hat.

In meinem Fall ist dieser Mensch mein Vater. Seine Sehkraft ist eingeschränkt, und er verbringt viele Stunden allein. Ich wollte, dass er einfach mit einer Stimme sprechen kann, die antwortet, ein Gespräch führt und Dinge erklärt – ohne erst einen Bildschirm suchen oder kleine Schrift lesen zu müssen. Das ist inzwischen möglich. Grok auf diesem Rechner bildet außerdem die Grundlage für weitere Funktionen und Integrationen, die noch dazukommen sollen. Für Familien, die technisch etwas versierter sind und keinen Laptop offen stehen lassen möchten, baue ich denselben Assistenten auch für einen Raspberry Pi 4 mit 4 GB RAM. Diesen Code möchte ich ebenfalls veröffentlichen, damit sich bei Bedarf ein eigenes, dediziertes Gerät bauen lässt.

Solange das Programm läuft, kann der Assistent weiter zuhören. Das Audio bleibt auf dem Computer und wird dort lokal in Text umgewandelt. Grok erhält nur dann Text, wenn der Assistent tatsächlich angesprochen wurde: nach einer Begrüßung, bei einer Frage, bei einem Befehl, der mit `befehl` beginnt, oder wenn ein Lied gewünscht wird. Alltägliche Gespräche bleiben in der lokalen Sitzung. Wird ein Befehl falsch verstanden, kann Grok bei der Interpretation helfen – ausgeführt wird er trotzdem erst nach einer ausdrücklichen Bestätigung.

Das ist die Grundidee. Unten sieht man das Fenster während des Zuhörens sowie das Tray-Menü mit geöffnetem Bereich **Sprache**.

![Das Informationsfenster, beim Zuhören, mit dem laufenden Protokoll darunter](docs/img/app-window.png)

![Das Menü der Taskleiste, mit der Sprachenliste offen](docs/img/tray-menu.png)

Die folgende Grafik zeigt, was mit einem gesprochenen Satz passiert.

![Wie ein Satz läuft: das Ohr bleibt lokal, und nur eine Frage oder ein reparierter Auftrag schickt Text an Grok](docs/img/flow.svg)

## Weiterlesen

- [Kurze Anleitung](docs/de/anleitung.md)
- [Spanisch zuerst, weil es zuerst auf Spanisch entwickelt und geprüft wurde](docs/de/hoeren.md)
- [Stimmabdrücke und Ohren](docs/de/abdruecke.md)
- [Sitzungen und Agenten](docs/de/sitzungen.md)
- [Warum Grok, und nicht ein weiteres Chatfenster](docs/de/grok.md)
- [Was wirklich läuft](docs/de/teile.md)
- [Was man sagen kann](docs/de/sagen.md)
- [Die Programmdatei starten](docs/de/start.md)
- [Aus dem Quellbaum starten](docs/de/quelle.md)
- [Was das ist](docs/de/was.md)
