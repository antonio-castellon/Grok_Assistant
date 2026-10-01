[← README.DE.md](../../README.DE.md)

# Was wirklich läuft

Die Grafik oben fasst das gesamte Produkt zusammen. Diese Komponenten setzen es technisch um.

| Teil | Wo es lebt | Was es darf |
| --- | --- | --- |
| STT-Motor | `listening/listen.py`, `listening/kroko_ear.py`, `listeners/dictation.ps1` | Ton auf diesem PC in Text verwandeln. Der STT-Motor im Streaming spricht Spanisch lokal. Windows-Diktat auf Spanisch, wenn der Motor da ist. Die Tastatur ist immer da. |
| Regeln | `rules/brain.py`, `rules/match.py`, `textutil.py` | Entscheiden: ignorieren, lokaler Auftrag, oder Wolke. Ein falscher Buchstabe trifft einen lokalen Auftrag noch. Zwei nicht. |
| Heft | `notebook/store.py`, `%APPDATA%\GrokAssistant` | Sitzungen, Namen und das Debug-Protokoll halten. Die geteilte Sitzung behält die im Tab Einfach gewählten Tage und lässt den ältesten Tag fallen. |
| Passwort | `notebook/auth.py` | Einen gesalzenen Hash speichern. Das Passwort selbst wird nie geschrieben. |
| Mund | `speaking/speech.py`, `scripts/speak.ps1` | Mit einer lokalen Stimme sprechen. Spanische Stimmen kommen zuerst. |
| Musik | `house/music.py` | Audio über `yt-dlp` und `mpv` spielen, wenn beide da sind. Während ein Lied läuft, bleibt das Mikrofon offen und folgt nur einem gespeicherten Abdruck. |
| Wolkentür | `rules/hub.py`, `cloud/grok_cli.py` | Den lokalen Befehl `grok` mit einer fertigen Textzeile rufen. Es gibt kein Audio-Argument. |
| Agenten | `~/.grok/agents` und das Konto | Die auf diesem PC und die, die das angemeldete Konto veröffentlicht. Einen zu öffnen ist eine Wahl. Ihr Gedächtnis ist nicht das lokale Heft. |
| Hülle | `ui/app.py` | Symbol in der Leiste, Informationsfenster, Debug-Protokoll. Ein Fenster zu schließen lässt das Programm laufen. |

Ein Satz endet, wenn die Person aufgehört hat. Der STT-Motor und das Windows-Ohr schließen ihn in unter zwei Sekunden. Ein Gruß allein bleibt zwei Sekunden offen, falls die Frage im selben Atem folgt. Während der Assistent spricht, ist dieses Ohr pausiert, damit die Antwort nicht als neuer Auftrag gilt. Während ein Lied läuft, bleibt das Mikrofon offen und folgt nur einem gespeicherten Abdruck. Siehe [Stimmabdrücke und Ohren](abdruecke.md). In einem Gespräch geht das Gehörte geradewegs an Grok, bis zum Abschied.

Außerhalb eines Gesprächs sind die Regeln eng. Mehr als sechs Wörter fällt weg, außer die Zeile ist ein echter Anruf oder `spiel das lied` plus ein Titel, bis zu sechzehn Wörter. Im Gespräch ist das Sechs-Wörter-Tor weg. Sechzig Sekunden ohne Neues beenden das Reden. Die Zeit, die man auf die Wolke wartet, zählt nicht. Der Administrator-Modus dauert fünf Minuten.

Grok wird auf zwei unterschiedliche Arten aufgerufen, jeweils für einen klar abgegrenzten Zweck.

- Ein verdrehter Auftrag ist eine Einordnung. Eine Runde, keine Websuche, keine Werkzeuge, ein einziges JSON-Objekt (`accion`, `orden`, `texto`). Ist die reparierte Zeile ein bekannter Auftrag, fragt der Assistent ja oder nein und führt ihn erst dann aus.
- Eine echte Frage ist ein Gespräch. Das Modell darf im Web suchen. Standardmäßig beschränken sich die Werkzeuge auf diese Suche. Ein Administrator kann auch Lesen und Ändern von Dateien erlauben. Die Shell bleibt aus. Das Arbeitsverzeichnis ist der Datenordner des Assistenten, also bleibt ein relativer Pfad dort und eine Stimme in der Küche steht nicht in einem Quellbaum. Die erste Runde legt eine Sitzungskennung an. Spätere Runden setzen sie fort. Ignorierte Zeilen sind nie in dieser Sitzung, weil sie nie gesendet wurden.

Ist ein Agent offen, benutzt die Frage die Datei dieses Agenten und die Sitzung dieses Agenten. Den Agenten schließen kehrt zum normalen Assistenten zurück. Das lokale Heft bleibt, wo es war.

Gesprochene Sätze, Befehlswörter, Hilfe und Persönlichkeiten liegen in `src/grok_assistant/lang/`. `hellos-es.txt` und `waits-es.txt` sind die spanischen Sätze, die die Stimme durchgeht. Die Farben sind JSON-Dateien in `ui/themes/`. Der Weg vom Mikrofon bleibt ein direkter Aufruf; die Ordner gruppieren nur den Code.

Beim Start wählt der Assistent die nächste Begrüßung aus der Liste und beginnt anschließend zuzuhören. Während er auf eine Antwort aus der Cloud wartet, verwendet er den nächsten kurzen Wartesatz. Beide Listen sind bewusst lang, damit nicht jeden Morgen dieselbe Formulierung zu hören ist.
