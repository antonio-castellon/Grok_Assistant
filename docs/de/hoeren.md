[← README.DE.md](../../README.DE.md)

# Spanisch zuerst, weil es zuerst auf Spanisch entwickelt und geprüft wurde

Zu Hause sprechen wir Spanisch. Das war ein natürlicher Ausgangspunkt, aber die Entscheidung hatte auch einen ganz praktischen Grund: Während der Entwicklung musste ich Erkennungsfehler schnell bemerken, unterscheiden können, ob das Problem in der Transkription oder in der nachfolgenden Logik lag, und denselben Satz auf verschiedene Arten wiederholen, bis sich die Ursache eindeutig finden ließ.

Ein echtes Zuhause ist außerdem deutlich anspruchsvoller als eine kontrollierte Testumgebung. Im Hintergrund wird gesprochen, der Fernseher läuft, aus der Küche kommen Geräusche, der Abstand zum Mikrofon ändert sich, und Menschen sprechen ganz normal, ohne für eine Maschine besonders deutlich zu artikulieren. Gerade unter solchen Bedingungen zu entwickeln hilft dabei, Probleme zu entdecken, die in einer sauberen Testumgebung leicht verborgen bleiben.

Der empfindlichste Teil ist STT – also *Speech-to-Text* –, denn alles Weitere hängt von dem erzeugten Text ab. Das Audio wird lokal verarbeitet und verlässt den Computer nicht. Der STT-Motor übernimmt die Transkription, doch schon ein falsch erkanntes Wort kann den weiteren Ablauf verändern: Aus `hola` kann `ola` werden, ein englischer Name kann wie ein spanisches Wort interpretiert werden oder ein für einen Menschen völlig klarer Befehl kommt so verändert an, dass das Programm ihn nicht mehr erkennt.

Das Ziel ist deshalb nicht eine perfekte Transkription – das wäre in einer normalen Wohnumgebung unrealistisch –, sondern ein Assistent, der sich auch dann vorhersehbar verhält, wenn die Transkription nicht perfekt ist.

Der STT-Motor im Streaming übernimmt zu Hause die spanische Spracherkennung. Whisper base, ein weiterer STT-Motor, hilft bei englischen Namen und Begriffen und erweitert die Erkennung auf Französisch, Deutsch und Englisch. Die Sprache lässt sich über das Menü **Idioma** wechseln; Voice Market kann bei Bedarf das passende Sprachmodell herunterladen.

Die Antworten sind standardmäßig bewusst kurz. Bei einer Sprachschnittstelle ist es meist angenehmer, zunächst eine klare und direkte Antwort zu hören, als jedes Mal eine lange Erklärung abwarten zu müssen. Das begrenzt das Gespräch aber nicht: Mit „erklär das genauer“, „warum?“ oder „gib mir mehr Details“ lässt sich dasselbe Thema direkt vertiefen. Die Idee ist, knapp zu beginnen und die Antwort bei Bedarf ganz natürlich auszubauen.
