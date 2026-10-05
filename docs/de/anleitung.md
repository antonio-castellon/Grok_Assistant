[← README.DE.md](../../README.DE.md)

# Kurze Anleitung

Kurze Schritte, um das Programm zu öffnen, einzurichten und damit zu sprechen. Jedes lange Kapitel bleibt auf seiner eigenen Seite.

## Öffnen

1. Doppelklick auf `GrokAssistant.exe`. Es gibt kein Installationsprogramm, und Python ist nicht nötig.
2. Erscheint ein Fenster für Grok Build, klicke **Instalar Grok Build**, dann **Iniciar sesión** im Browser und **Comprobar**. **Continuar** öffnet den Assistenten auch ohne Wolke. Lokale Aufträge gehen weiter. Es gibt keinen Schlüssel zum Einfügen.
3. Das Fenster öffnet sich. Oben rechts steht **WARTEN**. Das Grok-Zeichen bleibt in der Leiste.
4. Linksklick auf das Zeichen zeigt das Fenster. Rechtsklick öffnet das Menü.
5. Das Fenster schließen versteckt es. **Beenden** schließt das Programm.

## Einrichten

Einmal, in dieser Reihenfolge.

1. **Sprache.** Wähle Español, Français, Deutsch oder English. Menüs und Antworten wechseln in diese Sprache.
2. **Hörmotor (STT).** Das ist das Programm, das Sprache in Text verwandelt. Wähle einen im Menü. Fehlt er, öffne **Voice market**, Reiter **Hörmotor (STT)**, und lade ihn. Wählbar wird er bei 100 %.
3. **Stimme.** Wähle eine Stimme derselben Sprache. **Voice market**, Reiter **Stimmen**, hat mehr. Es erscheinen nur Stimmen der aktiven Sprache.
4. **Abdruck.** **Personen → Stimmabdrücke → Neuer Abdruck…**. Sprich die sechzehn Sätze einmal, mit dem Mikrofon, das du benutzen wirst. Ein anderes Mikrofon braucht seine eigene Aufnahme. Das Programm speichert den Ton, macht daraus einen Abdruck für alle Motoren und notiert, was jeder trifft, etwa `(92%)`. Die Liste ist nur Auskunft. Beim Start zählt es alle Abdrücke zusammen, behält den höchsten Motor und schreibt das ins Debug-Fenster. Den Motor wechselst du unter **Hören**.
5. **Passwort.** Nur zum Anlegen von Agenten. **Einstellungen → Passwort…**. Schreib es zweimal. Das Programm speichert eine Prüfsumme, nicht das Passwort im Klartext.
6. **Mit Windows starten** bleibt aus, bis du es unter **Einstellungen** einschaltest.

## Sprechen

1. Sag den Wecknamen. Am Anfang ist es `hola grok`. Oben rechts wechselt es zu **IM GESPRÄCH**.
2. Sprich. Eine Frage geht an Grok. Ein Auftrag kann mit `befehl` beginnen.
3. `danke` oder `tschüss` kehrt zu **WARTEN** zurück. Die Sitzung wird nicht gelöscht.
4. Für ein Lied sag den Titel. Beim ersten Mal lädt der Spieler.
5. Das Protokoll im Fenster zeigt, was gehört wurde. Darunter zeigt `LLM:`, was das lokale Modell verstanden hat, bei geschlossenem oder offenem Gespräch (`Text`, `Befehl`, `Gruß` oder `Schluss`). `Grok:` ist die Antwort.

Mehr dazu: [Stimmabdrücke und Ohren](abdruecke.md) · [Was man sagen kann](sagen.md) · [Die Programmdatei starten](start.md)
