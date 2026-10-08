[Read in English](README.md) · [Leer en español](README.ES.md) · [Lire en français](README.FR.md)

![Grok-Zeichen und ein Mikrofon, darunter Assistant](docs/img/banner.jpg)

# Grok Assistant

Release-Kandidat 1.0.5.

Jahrelang habe ich darauf gewartet, dass der Amazon Echo wirklich besser zuhören lernt. Am Ende blieb er vor allem ein Lautsprecher mit einem Lichtring. Also habe ich beschlossen, meinen eigenen Assistenten zu bauen – für einen älteren Menschen, der bereits einen kleinen Laptop in der Nähe hat.

In meinem Fall ist dieser Mensch mein Vater. Seine Sehkraft ist eingeschränkt, und er verbringt viele Stunden allein. Ich wollte, dass er einfach mit einer Stimme sprechen kann, die antwortet, ein Gespräch führt und Dinge erklärt – ohne erst einen Bildschirm suchen oder kleine Schrift lesen zu müssen. Das ist inzwischen möglich. Grok auf diesem Rechner bildet außerdem die Grundlage für weitere Funktionen und Integrationen, die noch dazukommen sollen. Für Familien, die technisch etwas versierter sind und keinen Laptop offen stehen lassen möchten, liegt derselbe Assistent für einen Raspberry Pi 4 mit 4 GB RAM im Parallelprojekt [Grok Pi Assistance](https://github.com/antonio-castellon/Grok_Pi_Assistance), damit sich bei Bedarf ein eigenes Gerät bauen lässt.

Damit der Assistent wirklich zuhört, braucht es einen Stimmabdruck, aufgenommen mit dem Mikrofon, das benutzt werden soll: **Personen → Stimmabdrücke**. Ohne diesen Abdruck hört das Programm den Raum und lässt den Satz fallen, vor dem lokalen Modell und vor einem Auftrag. Der Abdruck sorgt dafür, dass sich am selben Ort nicht zwei Personen, der Fernseher und die Stimme des Assistenten vermischen. Das Mikrofon bleibt offen, während der Assistent spricht. Ein anderes Mikrofon braucht eine eigene Aufnahme. Der Rest steht in [Stimmabdrücke und Ohren](docs/de/abdruecke.md).

Solange das Programm läuft, kann der Assistent weiter zuhören. Das Audio bleibt auf dem Computer und wird dort lokal in Text umgewandelt. Grok erhält nur dann Text, wenn der Assistent tatsächlich angesprochen wurde: nach einer Begrüßung, bei einer Frage, bei einem Befehl, der mit `befehl` beginnt, oder wenn ein Lied gewünscht wird. Alltägliche Gespräche bleiben in der lokalen Sitzung. Wird ein Befehl falsch verstanden, kann Grok bei der Interpretation helfen – ausgeführt wird er trotzdem erst nach einer ausdrücklichen Bestätigung.

Das ist die Grundidee. Unten das Fenster beim Zuhören und das Symbolmenü mit geöffnetem Escucha. Die Bilder sind in jeder Sprache dieselben.

![Das Fenster im Warten, auf dem Tab Einfach](docs/img/app-window.png)

![Das Symbolmenü mit geöffnetem Escucha](docs/img/tray-menu.png)

Die folgende Grafik zeigt, was mit einem gesprochenen Satz passiert.

![Der STT-Motor macht aus Sprache Text. Ohne Gespräch prüft das lokale Modell, ob es ein voller Auftrag ist. Im Gespräch notiert es den Satz, und der Text geht an Grok.](docs/img/flow.svg)

In den Einstellungen sucht Grok nur im Internet. Ein Administrator kann erlauben, dass Grok Dateien auf diesem Rechner ändert. Die Shell bleibt aus, und ein relativer Pfad landet im Datenordner des Assistenten.

## Weiterlesen

- [Kurze Anleitung](docs/de/anleitung.md)
- [Aussehen](docs/de/aussehen.md)
- [Stimmabdrücke und Ohren](docs/de/abdruecke.md)
- [Tipps](docs/de/tipps.md)
- [Sitzungen und Agenten](docs/de/sitzungen.md)
- [Warum Grok, und nicht ein weiteres Chatfenster](docs/de/grok.md)
- [Was wirklich läuft](docs/de/teile.md)
- [Was man sagen kann](docs/de/sagen.md)
- [Die Programmdatei starten](docs/de/start.md)
- [Aus dem Quellbaum starten](docs/de/quelle.md)
- [Was das ist](docs/de/was.md)
