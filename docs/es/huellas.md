[← README.ES.md](../../README.ES.md)

# Huellas y oídos

Una huella mide el trozo de audio del micrófono, no las palabras. Cada oído corta ese trozo a su manera. Cada motor de STT —Whisper pequeño, Whisper base, Canary y el dictado de Windows— no entrega el mismo audio, así que una huella grabada con un oído no identifica a la persona cuando está activo otro oído.

**Administrador → Huellas** lista a cada persona. Debajo del nombre, cada oído muestra cuántas tomas tiene guardadas, o *sin huella* si no tiene ninguna. Un oído que no está instalado aparece marcado y todavía no se puede grabar. Al elegir un oído, el programa cambia a ese oído y graba doce tomas solo para él.

El archivo es `dist/data/speakers.json`, junto a `GrokAssistant.exe`. Reconstruir el programa sustituye el ejecutable y deja esa carpeta. `dist/data/` está en `.gitignore`, así que las huellas no se suben al repositorio. El teclado no tiene huella: no hay un trozo de micrófono.
