[← README.ES.md](../../README.ES.md)

# Ejecutarlo desde el código

```powershell
cd C:\DEV.Personal\Grok_Assistant
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m grok_assistant
```

`--console` permite escribir el texto que normalmente llegaría desde el micrófono. Es útil para probar el sistema de voz y también para esos momentos en los que no apetece hablarle al escritorio.

```powershell
.venv\Scripts\python -m grok_assistant --console
```

Las huellas y el sonido en crudo viven en `dist/data/`, junto al ejecutable. Una persona tiene una huella. Cada motor se valora con ese mismo sonido. El resto de los datos, las sesiones, el hash de la contraseña y el registro del oído viven en `%APPDATA%\GrokAssistant` en Windows y en `~/.config/grok-assistant` en Linux. Los agentes creados aquí van a `~/.grok/agents`. El menú también enseña los que publica la cuenta iniciada. Ninguno de los dos vive en esta copia de git. El asistente usa su propia carpeta de datos. No trabaja dentro de un árbol de código lleno de proyectos.

La música necesita `yt-dlp` y `mpv`. Si faltan, la primera canción los descarga. Si eso falla, el asistente lo dice en una frase.
