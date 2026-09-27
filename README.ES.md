[Read in English](README.md) · [Lire en français](README.FR.md) · [Auf Deutsch lesen](README.DE.md)

![Marca de Grok, con Assistance debajo](docs/img/banner.jpg)

# Grok Assistant

Llevaba años esperando que el Amazon Echo aprendiera a escuchar de verdad. Al final seguía siendo, sobre todo, un altavoz con un anillo de luz, así que decidí construir mi propio asistente para una persona mayor que ya tiene un pequeño portátil cerca.

En mi caso, esa persona es mi padre. Tiene la vista limitada y pasa muchas horas solo. Quería que pudiera hablar con una voz capaz de responder, conversar y explicar cosas sin tener que buscar una pantalla ni leer letra pequeña. Ahora ya es posible. Grok, en este equipo, es también la base sobre la que iré añadiendo nuevas funciones e integraciones. Para quien tenga un poco más de experiencia técnica y prefiera no dejar un portátil abierto, estoy preparando el mismo asistente para una Raspberry Pi 4 de 4 GB. Publicaré también ese código para que cualquiera pueda montarse un dispositivo dedicado.

Mientras el programa está abierto, puede seguir escuchando. El audio se queda en el ordenador y se convierte en texto de forma local. Grok solo recibe texto cuando realmente se está hablando con el asistente: después de un saludo, al hacer una pregunta, al dar una orden que empieza por `comando` o al pedir una canción. La conversación cotidiana permanece en la sesión local. Si una orden se entiende mal, Grok puede ayudar a interpretarla, pero el asistente seguirá pidiendo un `sí` antes de ejecutarla.

Esa es la idea básica. Debajo se puede ver la ventana mientras escucha y el menú de la bandeja con **Idioma** abierto.

![La ventana de información, escuchando, con la depuración en vivo debajo](docs/img/app-window.png)

![El menú de la bandeja, con la lista de idiomas abierta](docs/img/tray-menu.png)

El diagrama de abajo muestra qué ocurre con una frase desde que se pronuncia.

![El motor STT pasa la voz a texto. Sin conversación, el modelo local mira si es un comando completo. En una conversación, el texto va directo a Grok.](docs/img/flow.svg)

## Seguir leyendo

- [Guía de uso](docs/es/guia.md)
- [Español primero, porque inicialmente se desarrolló y se probó en español](docs/es/escucha.md)
- [Huellas y oídos](docs/es/huellas.md)
- [Sesiones y agentes](docs/es/sesiones.md)
- [Por qué Grok, y no otra ventana de chat](docs/es/grok.md)
- [Qué está funcionando de verdad](docs/es/piezas.md)
- [Qué se puede decir](docs/es/decir.md)
- [Ejecutar el programa](docs/es/ejecutar.md)
- [Ejecutarlo desde el código](docs/es/codigo.md)
- [Qué es esto](docs/es/que-es.md)
