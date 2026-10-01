[← README.DE.md](../../README.DE.md)

# Sitzungen und Agenten

Meistens muss man sich über Sitzungen überhaupt keine Gedanken machen. Sobald ein Gespräch mit dem Assistenten beginnt, verwendet es automatisch eine **gemeinsame Sitzung**. Im Tab Einfach legt man fest, wie viele Tage sie zurückbehält. Der neue Tag kommt dazu und der älteste fällt weg. Voreingestellt ist ein Tag.

Für Gespräche, die länger erhalten bleiben sollen, gibt es benannte Sitzungen. Anders als die gemeinsame Sitzung laufen sie nicht von allein ab: Ihr Kontext bleibt so lange erhalten, bis die Sitzung ausdrücklich gelöscht wird. Die gemeinsame Sitzung eignet sich damit für alltägliche Gespräche, während benannte Sitzungen Themen getrennt halten können, die über Tage, Wochen oder länger weitergeführt werden sollen.

Man muss also nicht vor jedem Gespräch entscheiden, wo es gespeichert werden soll. Normale Unterhaltungen landen automatisch in der gemeinsamen Sitzung und räumen sich später selbst auf. Eine eigene Sitzung wird erst dann wichtig, wenn ein Thema bewusst erhalten bleiben soll.

Diese Sitzungen gehören zum lokalen Assistenten und bleiben auf diesem Computer. Sie sind nicht dasselbe wie das Gedächtnis des Grok-Kontos.

Ein **Agent** ist etwas anderes. Er gehört zum Grok-Konto und wird bewusst mit `befehl öffne den agenten …` geöffnet (auf Spanisch `comando abrir agente …`). Das Menü Agent zeigt die Dateien auf diesem PC (`~/.grok/agents`) und die Agenten, die das angemeldete Konto bereits veröffentlicht. Er kann eigene Informationen – etwa Daten, Orte oder Listen – behalten und später wiederverwenden. Da diese Informationen zum Konto gehören, kann derselbe Agent auch auf einem anderen Computer verfügbar sein, auf dem du angemeldet bist. Einen anzulegen speichert eine Datei auf diesem PC und verlangt das Administrator-Passwort.

Ein Abschied (`danke`, `tschüss`) beendet lediglich das aktuelle Gespräch; der Kontext wird dadurch nicht gelöscht. Das Schließen einer Sitzung führt zurück zur gemeinsamen Sitzung. `befehl schließe den agenten` verlässt den aktiven Agenten und kehrt zum normalen Assistenten zurück, ohne den Agenten oder seine Informationen zu löschen.
