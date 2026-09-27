[← README.DE.md](../../README.DE.md)

# Stimmabdrücke und Ohren

Ein Stimmabdruck misst das Mikrofonstück, nicht die Wörter. Jedes Ohr schneidet dieses Stück auf seine Weise. Jeder STT-Motor — Whisper klein, Whisper base, Canary und das Windows-Diktat — liefert nicht dasselbe Audio. Ein Abdruck, der mit einem Ohr aufgenommen wurde, erkennt die Person nicht, wenn ein anderes Ohr aktiv ist.

**Administrador → Huellas** listet jede Person. Unter dem Namen zeigt jedes Ohr, wie viele Aufnahmen gespeichert sind, oder *sin huella*, wenn keine da ist. Ein Ohr, das nicht installiert ist, ist markiert und kann noch nicht aufgenommen werden. Die Wahl eines Ohrs schaltet auf dieses Ohr und nimmt zwölf Aufnahmen nur dafür auf.

Die Datei ist `dist/data/speakers.json`, neben `GrokAssistant.exe`. Ein neuer Bau ersetzt das Programm und lässt diesen Ordner stehen. `dist/data/` steht in `.gitignore`, die Abdrücke gehen also nicht ins Repository. Die Tastatur hat keinen Abdruck: es gibt kein Mikrofonstück.
