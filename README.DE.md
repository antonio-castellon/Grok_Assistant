[Read in English](README.md) · [Leer en español](README.ES.md) · [Lire en français](README.FR.md)

![Grok-Zeichen, darunter Assistance](docs/img/banner.jpg)

# Grok Assistant

Ich habe Jahre darauf gewartet, dass der Amazon Echo besser zuhört. Er blieb ein Lautsprecher mit einem Lichtring, also habe ich meinen eigenen gebaut, für einen älteren Menschen, der schon einen kleinen Laptop in der Nähe hat.

In meinem Fall ist dieser Mensch mein Vater. Sein Sehen ist eingeschränkt, und er verbringt viele Stunden allein. Ich wollte eine Stimme, die ein Gespräch führen und Dinge erklären kann, ohne einen Bildschirm, den man suchen muss, und ohne kleine Schrift, die man lesen muss. Das geht jetzt. Grok auf diesem Rechner ist der Weg, auf dem weitere Funktionen und Anbindungen ankommen. Wenn jemand in der Familie ein wenig mehr weiß und lieber keinen Laptop offen stehen lassen will, ist derselbe Assistent der, den ich auf einem Raspberry Pi 4 mit 4 GB baue, und ich werde den Code bald auch veröffentlichen, damit man ihn klonen kann, wenn man lieber ein eigenes Gerät hat.

Er kann weiter hören, solange das Programm offen ist. Der Ton bleibt auf dem Computer. Ein Satz wird hier zu Text, und Grok bekommt diesen Text nur, wenn er für den Assistenten bestimmt war: ein Hallo, dann eine Frage, ein Auftrag, der mit `befehl` beginnt, oder ein Lied, das man verlangt hat. Das alltägliche Reden landet in einer lokalen Sitzung und bleibt dort. Ein missverstandener Auftrag kann mit Grok geprüft werden, und er wartet trotzdem auf ein Ja, bevor er ihn ausführt.

Das ist die ganze Idee. Das ist das Fenster, während es hört, und das Menü der Leiste mit Sprache offen.

![Das Informationsfenster, beim Zuhören, mit dem laufenden Protokoll darunter](docs/img/app-window.png)

![Das Menü der Taskleiste, mit der Sprachenliste offen](docs/img/tray-menu.png)

Die Zeichnung darunter ist der Weg eines Satzes.

![Wie ein Satz läuft: das Ohr bleibt lokal, und nur eine Frage oder ein reparierter Auftrag schickt Text an Grok](docs/img/flow.svg)

## Zuerst Spanisch, weil das Haus laut ist

Spanisch ist die Sprache zu Hause, also fängt der Assistent dort an. Die Antworten bleiben kurz. Eine lange Rede ist schwer zu folgen, wenn es laut ist.

Der schwierige Teil ist STT, Sprache zu Text. Das ist der Schritt, der eine Stimme in Wörter verwandelt, auf diesem Computer. Das Audio geht nicht hinaus. Die lokalen Modelle, die das tun, Kroko und Whisper, hören ein Wort leicht falsch. „Hola“ kann als „ola“ ankommen. Ein englischer Name kann auf Spanisch ankommen. Der Rest der Anwendung hängt an diesem Text. Sind die Wörter falsch, ist der Auftrag falsch, und die Frage erreicht Grok nicht.

Kroko ist das spanische Ohr. Whisper base behält englische Namen, und es liest Französisch, Deutsch und Englisch. Das Menü Sprache schaltet die Sprache schon um. Voice market lädt ein Ohr, wenn man darum bittet.

## Sitzungen und Agenten

Eine Sitzung ist das Heft des Gesprächs. Sie bleibt auf diesem Computer. Das geteilte Heft fängt nach 24 Stunden neu an. Ein Heft mit Namen bleibt, bis man es löscht. Dieses Heft ist nicht das Grok-Konto.

Ein Agent ist ein Grok auf deinem Konto. Man öffnet ihn absichtlich mit `befehl öffne den agenten …` (auf Spanisch `comando abrir agente …`). Er kann Daten, Orte und Listen behalten, und er kann nachschlagen. Dieses Gedächtnis bleibt im Konto, also öffnet sich derselbe Agent auf einem anderen Computer, auf dem du angemeldet bist. Ihn anzulegen verlangt das Administrator-Passwort.

Auf Wiedersehen sagen (`danke`, `tschüss`) beendet das Gespräch. Es schließt die Sitzung nicht. Die Sitzung schließen geht zurück zum geteilten Heft. `befehl schließe den agenten` geht zurück zum normalen Assistenten. Es löscht den Agenten nicht. Der Agent braucht diesen Laptop nicht eingeschaltet. Man spricht ihn trotzdem absichtlich an.

## Warum Grok, und nicht ein weiteres Chatfenster

Ein normaler Chat kann ein Programm schreiben und es als Text zurückgeben. Jemand muss diesen Text noch in den richtigen Ordner legen und zum Laufen bringen.

Grok Build ist schon auf diesem Computer, und er ist angemeldet. Es gibt keinen API-Schlüssel zum Einfügen. Du öffnest diesen Ordner, und er kann den Assistenten lesen, ändern, die Tests laufen lassen und das neue Programm hier lassen. Die Idee ist dieselbe wie bei [OpenClaw](https://github.com/openclaw/openclaw): die Anweisungen sind einfache Dateien, also lässt sich ein neuer Schritt als Datei aufschreiben.

Eine Frage zum Wetter ändert das Programm nicht. Das Programm zu ändern ist ein eigener Schritt, und man öffnet ihn absichtlich.

## Was wirklich läuft

Die Zeichnung weiter oben ist das ganze Produkt. Das sind die Teile, die es umsetzen.

| Teil | Wo es lebt | Was es darf |
| --- | --- | --- |
| Ohr | `listen.py`, `kroko_ear.py`, `listeners/dictation.ps1` | Ton auf diesem PC in Text verwandeln. Kroko streamt Spanisch lokal. Windows-Diktat auf Spanisch, wenn der Erkenner da ist. Die Tastatur ist immer da. |
| Regeln | `brain.py`, `match.py`, `textutil.py` | Entscheiden: ignorieren, lokaler Auftrag, oder Wolke. Ein falscher Buchstabe trifft einen lokalen Auftrag noch. Zwei nicht. |
| Heft | `store.py`, `%APPDATA%\GrokAssistant` | Sitzungen, Namen und das Debug-Protokoll halten. Die geteilte Sitzung wird nach 24 Stunden ersetzt. |
| Passwort | `auth.py` | Einen gesalzenen Hash speichern. Das Passwort selbst wird nie geschrieben. |
| Mund | `speech.py`, `scripts/speak.ps1` | Mit einer lokalen Stimme sprechen. Spanische Stimmen kommen zuerst. |
| Musik | `music.py` | Audio über `yt-dlp` und `mpv` spielen, wenn beide da sind. Das Ohr macht zu, während ein Lied läuft. |
| Wolkentür | `hub.py`, `grok_cli.py` | Den lokalen Befehl `grok` mit einer fertigen Textzeile rufen. Es gibt kein Audio-Argument. |
| Agenten | `~/.grok/agents` | Definitionen auf diesem Konto. Einen zu öffnen ist eine Wahl. Ihr Gedächtnis ist nicht das lokale Heft. |
| Hülle | `tray.py` | Symbol in der Leiste, Informationsfenster, Debug-Protokoll. Ein Fenster zu schließen lässt das Programm laufen. |

Ein Satz endet, wenn die Person aufgehört hat. Kroko und das Windows-Ohr schließen ihn in unter zwei Sekunden. Ein Gruß allein bleibt zwei Sekunden offen, falls die Frage im selben Atem folgt. Während der Assistent spricht, ist dieses Ohr pausiert, damit die Antwort nicht als neuer Auftrag gilt. Dieselbe Pause gilt für Musik. In einem Gespräch geht das Gehörte geradewegs an Grok, bis zum Abschied.

Außerhalb eines Gesprächs sind die Regeln eng. Mehr als sechs Wörter fällt weg, außer die Zeile ist ein echter Anruf oder `spiel das lied` plus ein Titel, bis zu sechzehn Wörter. Im Gespräch ist das Sechs-Wörter-Tor weg. Sechzig Sekunden ohne Neues beenden das Reden. Die Zeit, die man auf die Wolke wartet, zählt nicht. Der Administrator-Modus dauert fünf Minuten.

Zwei verschiedene Rufe gibt es, und sie sind nicht austauschbar.

- Ein verdrehter Auftrag ist eine Einordnung. Eine Runde, keine Websuche, keine Werkzeuge, ein einziges JSON-Objekt (`accion`, `orden`, `texto`). Ist die reparierte Zeile ein bekannter Auftrag, fragt der Assistent ja oder nein und führt ihn erst dann aus.
- Eine echte Frage ist ein Gespräch. Das Modell darf im Web suchen. Die Werkzeuge beschränken sich auf diese Suche. Das Arbeitsverzeichnis ist der Datenordner des Assistenten, also steht eine Stimme in der Küche nicht in einem Quellbaum. Die erste Runde legt eine Sitzungskennung an. Spätere Runden setzen sie fort. Ignorierte Zeilen sind nie in dieser Sitzung, weil sie nie gesendet wurden.

Ist ein Agent offen, benutzt die Frage die Datei dieses Agenten und die Sitzung dieses Agenten. Den Agenten schließen kehrt zum normalen Assistenten zurück. Das lokale Heft bleibt, wo es war.

Gesprochene Sätze, Befehlswörter, Hilfe und Persönlichkeiten liegen in `src/grok_assistant/lang/`. `hellos-es.txt` und `waits-es.txt` sind die spanischen Sätze, die die Stimme durchgeht. `brain.py` und `hub.py` bleiben gleich.

Beim Start sagt er den nächsten Gruß und hört dann auf. Während er auf die Wolke wartet, sagt er den nächsten kurzen Satz aus der anderen Liste. Die Listen sind lang, damit derselbe Satz nicht jeden Morgen wiederkommt.

## Was man sagen kann

Man fängt mit `hallo grok` auf Deutsch an, oder mit `hola grok` und `¿estás ahí?` auf Spanisch, der Ausgangssprache. Außerhalb eines Gesprächs beginnen die anderen Aufträge mit `befehl` (oder `comando`). Ein Satz mit mehr als sechs Wörtern wird ignoriert, außer es ist ein echter Gruß oder ein Lied plus Titel (bis zu sechzehn Wörter). Im Gespräch gibt es keine Grenze von sechs Wörtern. Ein Lied braucht das Wort `befehl` nicht. Der Abschied bleibt auf diesem Computer und ist sofort. Während eine Antwort kommt, hört man einen kurzen Satz, das Mikrofon pausiert, und dann hört man die Antwort. Das Informationsfenster hat die Befehlsliste.

Das Symbol in der Leiste ist das Programm. Linksklick öffnet das Fenster. Rechtsklick öffnet das Menü. Das Fenster zu schließen versteckt es. Beenden ist der Knopf, im Fenster oder im Menü.

## Die Programmdatei starten

Es gibt kein Installationsprogramm. `dist/GrokAssistant.exe` ist das ganze Programm. Man kopiert sie irgendwohin und öffnet sie mit einem Doppelklick. Für diese Datei muss Python nicht installiert sein. Ein Fenster öffnet sich mit dem laufenden Protokoll — was gehört wurde, und was danach passiert — und das Grok-Zeichen bleibt in der Leiste. Das Fenster zu schließen versteckt es. Beenden ist der Knopf, oder Salir im Menü der Leiste.

Fehlt Grok Build, oder hat man sich nie angemeldet, hält das Programm an einem Fenster an, bevor die Leiste kommt. **Instalar Grok Build** führt das offizielle Installationsprogramm aus:

```powershell
irm https://x.ai/cli/install.ps1 | iex
```

**Iniciar sesión** öffnet `grok login`, das den Browser benutzt. **Comprobar** fragt `grok models`, ob das Konto bereit ist. **Continuar** startet den Assistenten trotzdem, damit lokale Aufträge weiter gehen, während die Wolke fehlt. Es gibt keinen API-Schlüssel zum Einfügen.

Um diese Programmdatei aus diesem Ordner neu zu bauen:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## Aus dem Quellbaum starten

```powershell
cd C:\DEV.Personal\Grok_Assistant
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m grok_assistant
```

`--console` tippt, was das Mikrofon gehört hätte. Nützlich, bevor es eine Sprachmaschine gibt, und nützlich, wenn man nicht mit dem Schreibtisch reden will.

```powershell
.venv\Scripts\python -m grok_assistant --console
```

Daten, Sitzungen, der Passwort-Hash und das Ohr-Protokoll liegen unter `%APPDATA%\GrokAssistant` unter Windows und unter `~/.config/grok-assistant` unter Linux. Agenten-Dateien gehen nach `~/.grok/agents`, den Ordner des Grok-Kontos, nicht diese Git-Kopie. Der Assistent benutzt seinen eigenen Datenordner. Er arbeitet nicht in einem Quellbaum voller Projekte.

Musik braucht `yt-dlp` und `mpv`. Fehlen sie, lädt das erste Lied sie herunter. Schlägt das fehl, sagt der Assistent es in einem Satz.

## Was das ist

Eine Stimme für die Stunden, in denen Lesen schwer ist und das Haus still. Die Laptop-Fassung ist für einen älteren Menschen, der schon einen kleinen Computer in der Nähe hat. Der Raspberry Pi 4 mit 4 GB ist derselbe Assistent, wenn der Laptop zu bleiben sollte. Das Mikrofon darf wach bleiben. Nur ein Satz, der für den Assistenten bestimmt war, geht hinaus, und er geht als Text.
