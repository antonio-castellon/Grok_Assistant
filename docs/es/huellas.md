[← README.ES.md](../../README.ES.md)

# Huellas y oídos

La huella se graba una vez. El programa guarda el sonido de cada frase, en crudo, junto a la persona. Con ese mismo sonido hace la huella de la voz, y después pasa cada motor por las frases. Como las frases se conocen, anota cuántas acierta cada motor.

Son dieciséis frases distintas, una vez cada una. Hacen falta varias para que la huella y el porcentaje salgan finos. Una toma que no encaja con las demás se deja fuera. Si no queda una sola voz clara, no se guarda a otra persona.

**Administrador → Huellas** lista a cada persona. Debajo del nombre está el número de tomas. Al lado de cada motor instalado sale el acierto, por ejemplo `Whisper pequeño (92%)`. El motor en uso es el de mayor porcentaje. Un motor que aún no está se valora cuando se instala, sin volver a hablar. **Volver a grabar** repite las dieciséis frases. Elegir un motor no abre otra grabación.

El sonido y la huella están en `dist/data/`, junto a `GrokAssistant.exe`. Reconstruir el programa sustituye el ejecutable y deja esa carpeta. `dist/data/` está en `.gitignore`. El teclado no tiene huella: no hay micrófono.
