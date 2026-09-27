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

Die erste Sprache ist Spanisch. Das ist die Sprache, die wir zu Hause wirklich sprechen, also ist sie der ehrliche Ort, um das Experiment anzufangen. Ein stiller Schreibtisch und ein Headset würden jeden Assistenten klug aussehen lassen. Die Küche nicht. Die Leute reden durcheinander, der Fernseher bleibt an, jemand verlangt ein Lied, während ein anderer mitten im Satz ist. Ich will dieses Geräusch. Die Probe ist, ob ein Anruf und ein kurzer Auftrag in einem echten Zimmer noch ankommen, und ob alles andere auf der Maschine bleibt, wenn das Zimmer unordentlich ist.

Die Antworten bleiben absichtlich kurz. Eine Stimme in einem lauten Haus, die einen Absatz vorliest, hat schon verloren.

Das Menü Sprache schaltet zwischen Español, Français, Deutsch und English. Befehle, Hilfe und die Persönlichkeiten leben in `lang/*.json`, und dasselbe Menü kann die Befehle und die Hilfe der Sprache bearbeiten, die gerade an ist. Eine weitere Sprache ist eine weitere json-Datei in diesem Ordner. Das Ohr muss mitgehen: Kroko hört Spanisch, und Whisper base liest die anderen. Wählt man eine andere Sprache als Spanisch, geht das Ohr auf Whisper base, wenn das Modell schon auf der Platte liegt. Die Grüße, die Wartesätze und die Befehlswörter reisen mit der Sprache. Die Regel darunter nicht. Ein Satz geht nur hinaus, wenn er an den Assistenten gerichtet war.

Auf diesem PC ist der Mund die spanische Stimme, die Windows schon hat, oder eine Piper-Stimme aus Voice market, oder espeak unter Linux. Der Pi hat sein eigenes Piper-Set. Das Mikrofon-Ohr für Spanisch ist Kroko: ein lokales Streaming-Modell. Audio verlässt die Maschine nicht. Voice market lädt es, wenn man darum bittet; liegt der Ordner auf der Platte und das gespeicherte Ohr war noch die Tastatur, startet der Assistent Kroko von allein. Die Tastatur im Debug-Fenster bleibt da. Die spanische Windows-Diktierfunktion ist der Desktop-Erkenner. Fehlt sie, installieren Hören und Voice market sie über Windows selbst. Whisper, base und Canary sind die anderen Ohren, jedes wartet auf sein Modell. Ein Erkenner in der Wolke ist kein Ersatz. Den Raum hochzuladen, um einen lauten Raum zu prüfen, würde das Experiment wegwerfen.

## Der Angestellte, der deine Hardware nicht braucht

Eine lokale Sitzung ist ein Heft. Sie lebt im Datenordner dieser Maschine. Die geteilte wird nach 24 Stunden weggeworfen und neu angefangen. Eine mit Namen bleibt, bis man sie löscht. Nichts von diesem Heft ist das Grok-Konto.

Ein Agent ist das andere Wesen. Man öffnet ihn absichtlich (`befehl öffne den agenten …`, auf Spanisch `comando abrir agente …`). Ihn anzulegen verlangt das Administrator-Passwort, denn „jemanden anwerfen, der sich Dinge merkt und ins Internet schauen kann“ ist kein Kunststück für jeden, der am Mikrofon vorbeigeht. Der Agent ist ein Grok-Agent auf deinem Konto, keine umbenannte Sitzung. Er kann Daten, Orte und Listen behalten, und er kann suchen. Dieses Gedächtnis bleibt beim Konto, also kann eine andere Maschine, auf der du schon angemeldet bist, denselben Agenten öffnen.

Das ist der Teil, den der Echo nie angeboten hat und den das Telefon nicht beherbergen wird. Der Agent braucht den Lüfter des Pi nicht, nicht dieses Symbol in der Leiste, und nicht ein Mikrofon, das ein Betriebssystem freizugeben bereit war. Der Computer im Wohnzimmer ist eine Klingel. Der Angestellte lebt beim Konto. Du ziehst die Klingel ab, und der Angestellte steht weiter auf der Liste: du erreichst ihn von jedem anderen angemeldeten Grok, wann du arbeiten willst, auch zu einer Stunde, in der jedes Gerät im Haus seine beste Imitation eines Ziegelsteins gibt. Die Klingel muss nicht wach bleiben, damit das Büro existiert. Das Büro, wenig höflich, hört den Raum nicht. Man muss es absichtlich ansprechen. Immer an sollte nie immer teilen heißen. Der Zylinder hatte eine Idee dazu. Es war die falsche, und sie kam mit einem Lichtring.

`befehl schließe den agenten` kehrt zum normalen Assistenten zurück. Es löscht den Agenten nicht und beendet das Gespräch nicht. Das Gespräch zu schließen (`danke`, `in ordnung`, `tschüss`) schließt die Sitzung nicht. Die Sitzung zu schließen kehrt zum geteilten Heft zurück und hört auf, wenn man gerade gesprochen hat. Der Bildschirm, oder die Leiste, wartet wieder. Das gewöhnliche Leben geht weiter, ohne hochgeladen worden zu sein.

## Warum Grok, das eine Werkstatt ist und kein weiteres Chatfenster

ChatGPT schreibt ein Programm. Claude schreibt ein sorgfältiges. Beide tun das in einem Fenster, das woanders lebt, und geben das Ergebnis dann als Text zurück. Jemand muss immer noch wissen, was ein Ordner ist, welche Datei die echte ist, und welcher Befehl einen höflichen Vorschlag in Software verwandelt, die wirklich läuft. Dieser Jemand war ich, und ich war schon müde.

Was ich wollte, ist die Form von [OpenClaw](https://github.com/openclaw/openclaw): ein Agent, der auf dem Computer bleibt, wächst, indem er seine eigenen Anweisungen schreibt, und die Softwarearbeit hier erledigt. OpenClaws Skills sind einfache Dateien, deshalb kann der Agent einen neuen Trick lernen, indem er ihn aufschreibt. Grok Build ist diese Idee mit den Krallen schon auf dieser Maschine. Der Befehl `grok` ist hier installiert. Er ist angemeldet. Zeigst du auf diesen Ordner, kann er den Assistenten lesen, ändern, die Tests laufen lassen und die nächste Fassung an dieselbe Stelle legen. Das Sprachprogramm ist die Klingel. Grok Build ist die Werkstatt hinter dem Haus.

Deshalb lässt sich mehr davon anbauen, ohne von vorn anzufangen. Es gibt keinen API-Schlüssel, den man suchen muss, und kein Formular, das fragt, welches Modell das Internet diese Woche begeistert. Der Assistent findet `grok` auf dem Pfad, fragt diesen Befehl, welche Modelle er wirklich fahren kann, und benutzt die Stimme, die der Computer schon hat. Die Konfiguration ist die Tatsache, dass Grok installiert ist. Danach kann ich diesen Ordner mit Grok öffnen und in gewöhnlicher Sprache sagen, was dem Haus noch fehlt. Ein lauterer Gruß. Ein neuer Auftrag. Ein Erkenner. Eine weitere Anbindung. Grok schreibt die Änderung hier und erzeugt das neue Programm hier.

Eine Frage zum Wetter darf den Computer immer noch nicht umschreiben. Das wäre die schlechte Idee des Zylinders, mit besserer Grammatik. Die Werkstatt hat ihre eigene Tür, und man öffnet sie absichtlich, so wie man einen Agenten öffnet.

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

Die gesprochenen Sätze, die Befehlswörter, die Hilfe und die Persönlichkeiten reisen im Sprachpaket unter `src/grok_assistant/lang/`. `hellos-es.txt` und `waits-es.txt` sind weiter die spanischen Listen, die die Stimme durchgeht. `brain.py` und `hub.py` bleiben. Dieselbe Türpolitik. Ein neues Ohr, ein neuer Mund und neue Stimmen, wenn die Sprache sie braucht.

Beim Start spricht er die nächste Zeile aus der Grußliste und hört dann auf zu reden. Eine Wolkenwarte spricht die nächste Zeile aus der anderen Liste. Die beiden Listen sind lang, damit derselbe Witz nicht jeden Morgen wiederkommt.

## Was man sagen kann

Man ruft mit `hallo grok` auf Deutsch, oder mit `hola grok` und `¿estás ahí?` auf Spanisch, der Ausgangssprache. Außerhalb eines Gesprächs beginnen die anderen Aufträge mit `befehl` (oder `comando`). Ein fertiger Satz mit mehr als sechs Wörtern wird ignoriert, außer es ist ein echter Anruf oder ein Lied plus Titel (bis zu sechzehn Wörter). Im Gespräch gibt es keine Sechs-Wörter-Grenze. Ein Lied kann man ohne das Wort `befehl` verlangen. Der Abschied ist lokal und sofort. Während eine Antwort geholt wird, hört man eine kurze Zeile aus einer langen Liste, die rotiert, das Mikrofon macht Pause, und dann hört man die Antwort. Beim Start spricht er die nächste Zeile aus einer anderen Liste, den Grüßen, und dann ist er still. Keine Führung. Keine Befehlsliste heruntergebetet. Das Informationsfenster hat die Liste, für Leute, die lieber lesen, als sich von einem Lautsprecher belehren zu lassen.

Die Taskleiste ist die Anwendung. Linksklick öffnet das Informationsfenster. Rechtsklick öffnet das Menü: Pause, Erkenner, Stimme, Modell, Sitzungen, Persönlichkeit, Sprache, Beenden. Ein Fenster zu schließen beendet nicht. Beenden ist ein Menüpunkt, weil manche von uns jahrelang schlecht trainiert wurden von „willst du das Fenster wirklich verstecken und so tun, als wäre das ein Ausgang“.

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

Daten, Sitzungen, der Passwort-Hash und das lokale Ohr-Protokoll liegen unter `%APPDATA%\GrokAssistant` unter Windows und unter `~/.config/grok-assistant` unter Linux. Agenten-Definitionen werden nach `~/.grok/agents` geschrieben, das ist der Ordner des Grok-Kontos, nicht diese Git-Kopie. Zeig das Arbeitsverzeichnis des Assistenten nicht auf einen Quellbaum voller Projekte. Er weigert sich schon und benutzt seinen eigenen Datenordner, denn eine Stimme in der Küche soll nicht plötzlich Lust aufs Refactoring entdecken.

Musik will `yt-dlp` und `mpv` auf dem PATH. Ohne sie sagt der Assistent es, in einem Satz, und tut nicht so, als würde er summen.

## Was das ist

Eine Stimme für die Stunden, in denen Lesen schwer ist und das Haus still. Die Laptop-Fassung ist für einen älteren Menschen, der schon einen kleinen Computer in der Nähe hat. Der Raspberry Pi 4 mit 4 GB ist derselbe Assistent, wenn der Laptop zu bleiben sollte. Das Mikrofon darf wach bleiben. Nur ein Satz, der für den Assistenten bestimmt war, geht hinaus, und er geht als Text.
