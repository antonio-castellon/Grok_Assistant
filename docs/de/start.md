[← README.DE.md](../../README.DE.md)

# Die Programmdatei starten

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
