[← README.DE.md](../../README.DE.md)

# Tipps

## Der Abdruck hält Personen auseinander

Der Stimmabdruck ist da, damit zwei Personen im selben Raum nicht in ein Gespräch geraten. Sobald er bereit ist, folgt das Mikrofon einer gespeicherten Stimme. Eine andere Stimme bleibt draußen, vor dem lokalen Modell und vor einem Auftrag. **Hören → Test einschalten** zeigt die Wörter und tut nichts damit. Dieselbe Zeile wird **Test ausschalten**. `salir` geht auch hinaus. Die Ecke zeigt TEST.

## Das Mikrofon gehört zum Abdruck

Ein leises oder dumpfes Mikrofon macht Wörter und Abdruck unsicherer. Der Abdruck ist die Stimme, wie dieses Mikrofon sie gehört hat. Dieselbe Person an einem anderen Mikrofon kann unter der Schwelle bleiben, auch wenn der Text auf dem Bildschirm stimmt. Den Abdruck nimmt man besser neu auf, an dem Mikrofon, das man benutzen wird.

**Einstellungen → Mikrofon** wechselt das Mikrofon. Hat dieses schon einen Abdruck, wird der benutzt. Ein Mikrofon ohne eigenen Abdruck behält den früheren, bis man ihn dort aufnimmt. **Standard** ist das Windows-Mikrofon.

## Wie ein Satz endet

Ein Satz schließt 1,2 Sekunden nach dem letzten neuen Wort, sobald mindestens 0,4 Sekunden Stimme da waren. Ein kürzeres Geräusch zählt nicht. Bei **Zuerst der Gruß** wartet ein bloßer Gruß 2 Sekunden, solange das Gespräch noch zu ist, damit die Frage folgen kann. Die Minuten auf Einfach schließen das Gespräch. Sie schließen nicht den Satz. Am schnellsten sind Name und Frage in einem Atemzug: «Hallo grok, wie spät ist es?».

## Während es antwortet

Das Mikrofon bleibt offen, während der Assistent spricht. Der Abdruck lässt die eigene Stimme des Assistenten fallen. **Hören pausieren** und eine Abdruckaufnahme schließen das Mikrofon. Während ein Lied läuft, wird nur eine gespeicherte Stimme verfolgt. Hält ein anderes Programm das Mikrofon schon, kann dieses es nicht öffnen. Ein anderes Mikrofon wählen, oder das Programm schließen, das es hält.

## Was die Debug-Zeilen bedeuten

`LLM: comando o accion no detectada` heißt: das kleine lokale Modell hat keinen Auftrag gesehen. Der Hörmotor hat den Satz gehört. Bei geschlossenem Gespräch bleibt der Satz auf dem Rechner. Zuerst das Gespräch öffnen, oder die Frage im selben Atemzug wie den Namen sagen. **Protokoll leeren** leert das Debug-Fenster. Spätere Sätze erscheinen wieder. **Spur speichern** packt eine Zip dieser Ausführung. Der Ton aus dem Haus bleibt auf dem Rechner. Grok bekommt den Text einer Frage oder eines Auftrags.
