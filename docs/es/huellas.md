[← README.ES.md](../../README.ES.md)

# Huellas y oídos

La huella se graba una vez. Una ventana muestra la frase y lo que oye el motor. Reintentar repite esta frase. Seguir pasa a la siguiente. Salir tira los audios de esta grabación. El programa guarda el sonido de cada frase, en crudo, junto a la persona. El motor que está escuchando no decide si la frase era la esperada. Con ese mismo sonido hace la huella de la voz, y después pasa cada motor por las frases. Como las frases se conocen, anota cuántas acierta cada motor. El usuario elige en Escucha el motor que oye bien en ese micrófono.

Son dieciséis frases distintas, una vez cada una. Hacen falta varias para que la huella y el porcentaje salgan finos. Una toma que no encaja se deja fuera de la huella. El sonido en crudo de las dieciséis frases se guarda igual. Si no queda una sola voz clara, no se cambia la huella de la persona.

**Personas → Huellas** lista a cada persona. Debajo del nombre está el número de tomas. Al lado de cada motor instalado sale el acierto de esa persona, por ejemplo `Whisper pequeño (92%)`. Es información: no elige el motor. Grabar un perfil valora todos los motores. Al arrancar, el programa suma los aciertos de todas las huellas y deja el motor más alto. Lo escribe en Depuración. El motor se cambia en **Escucha → Motor escucha (STT)**. Un motor que aún no está se valora cuando se instala, sin volver a hablar. **Volver a grabar** repite las dieciséis frases.

El sonido y la huella están en `dist/data/`, junto a `GrokAssistant.exe`. Reconstruir el programa sustituye el ejecutable y deja esa carpeta. `dist/data/` está en `.gitignore`. El teclado no tiene huella: no hay micrófono.
