[Read in English](README.md) · [Leer en español](README.ES.md) · [Lire en français](README.FR.md)

![Grok-Zeichen, darunter Assistance](docs/img/banner.jpg)

# Grok Assistant

Version 0.1.0, noch ein Release-Kandidat.

Jahrelang habe ich darauf gewartet, dass der Amazon Echo wirklich besser zuhören lernt. Am Ende blieb er vor allem ein Lautsprecher mit einem Lichtring. Also habe ich beschlossen, meinen eigenen Assistenten zu bauen – für einen älteren Menschen, der bereits einen kleinen Laptop in der Nähe hat.

In meinem Fall ist dieser Mensch mein Vater. Seine Sehkraft ist eingeschränkt, und er verbringt viele Stunden allein. Ich wollte, dass er einfach mit einer Stimme sprechen kann, die antwortet, ein Gespräch führt und Dinge erklärt – ohne erst einen Bildschirm suchen oder kleine Schrift lesen zu müssen. Das ist inzwischen möglich. Grok auf diesem Rechner bildet außerdem die Grundlage für weitere Funktionen und Integrationen, die noch dazukommen sollen. Für Familien, die technisch etwas versierter sind und keinen Laptop offen stehen lassen möchten, baue ich denselben Assistenten auch für einen Raspberry Pi 4 mit 4 GB RAM. Diesen Code möchte ich ebenfalls veröffentlichen, damit sich bei Bedarf ein eigenes, dediziertes Gerät bauen lässt.

Solange das Programm läuft, kann der Assistent weiter zuhören. Das Audio bleibt auf dem Computer und wird dort lokal in Text umgewandelt. Grok erhält nur dann Text, wenn der Assistent tatsächlich angesprochen wurde: nach einer Begrüßung, bei einer Frage, bei einem Befehl, der mit `befehl` beginnt, oder wenn ein Lied gewünscht wird. Alltägliche Gespräche bleiben in der lokalen Sitzung. Wird ein Befehl falsch verstanden, kann Grok bei der Interpretation helfen – ausgeführt wird er trotzdem erst nach einer ausdrücklichen Bestätigung.

Das ist die Grundidee. Unten das Fenster beim Zuhören und das Symbolmenü mit geöffnetem Escucha. Die Bilder sind in jeder Sprache dieselben.

![Das Fenster im Warten, auf dem Tab Einfach](docs/img/app-window.png)

![Das Symbolmenü mit geöffnetem Escucha](docs/img/tray-menu.png)

Die folgende Grafik zeigt, was mit einem gesprochenen Satz passiert.

![Der STT-Motor macht aus Sprache Text. Ohne Gespräch prüft das lokale Modell, ob es ein voller Auftrag ist. Im Gespräch notiert es den Satz, und der Text geht an Grok.](docs/img/flow.svg)

## Aussehen

Einstellungen → Aussehen listet Noche, dann Aurora, Cobre, Día, Lino, Mar und Oliva. Noche ist das der Bilder. Aurora ist Indigo, Cobre ist Holz und Kupfer, Lino ist helles Leinen, und Oliva ist ein tiefes Grün.

Zum Wechseln eine Datei `themes/<id>.json` in denselben Ordner legen wie `GrokAssistant.exe`. Das Menü zeigt das Feld `name`. Eine Datei mit derselben id ersetzt das mitgelieferte Thema. Eine fehlende Farbe bleibt bei Noche. Ein Start aus dem Quellbaum liest `dist/themes/`.

```json
{
  "name": "Casa",
  "bg": "#14181e",
  "ink": "#e7eef2"
}
```

Die übrigen Schlüssel sind `panel`, `muted`, `amber`, `teal`, `green`, `field`, `button`, `button_active`, `pause`, `pause_active`, `quit`, `quit_active`, `time`, `mode_ink`, `danger`, `select`, `chip_ink`, `flow_on`, `flow_off`, `flow_dim`, `menu_bg`, `menu_hot`, `menu_ink`, `menu_muted` und `menu_line`. `font`, `font_bold` und `mono` sind optional, als Liste, zum Beispiel `["Segoe UI", 12]`.

In den Einstellungen beginnt Grok nur mit dem Web. Ein Administrator kann Dateiänderungen erlauben. Die Shell bleibt aus, und ein relativer Pfad landet im Datenordner des Assistenten.

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
