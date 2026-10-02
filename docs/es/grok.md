[← README.ES.md](../../README.ES.md)

# Por qué Grok, y no otra ventana de chat

Un chat normal puede generar código, pero después alguien tiene que colocarlo donde corresponde, ejecutarlo, probarlo y convertirlo en un cambio que realmente funcione.

Grok Build ya está instalado y con la sesión iniciada en este ordenador, así que no hay ninguna clave de API que copiar y pegar. Al abrir esta carpeta puede revisar el asistente, modificarlo, ejecutar las pruebas y dejar aquí la versión actualizada. La idea se parece a la de [OpenClaw](https://github.com/openclaw/openclaw): las instrucciones viven en archivos sencillos, de modo que añadir un nuevo paso puede ser tan simple como describirlo en un archivo.

Una pregunta normal —por ejemplo, sobre el tiempo— nunca modifica el programa. Cambiar el código es un flujo separado y deliberado que hay que abrir expresamente.

## La misma respuesta, con otro motor

Este programa es un compañero de voz. El micrófono, el nombre para despertarlo, la huella y la voz que contesta viven en este equipo. El motor de razonamiento solo recibe texto, y solo cuando alguien se ha dirigido al asistente.

Hoy el motor conectado es Grok, porque Grok Build ya está instalado y con la sesión iniciada en este ordenador. Claude, ChatGPT y Codex también pueden contestar una pregunta dicha en voz alta. En esa parte del trabajo las diferencias son pequeñas. Esta versión es un experimento con Grok. Si se sostiene, el paso siguiente será el mismo asistente apuntando a otro motor de razonamiento. Ese paso no está en esta versión.

| | Grok Build | Claude Code | Codex | ChatGPT |
| --- | --- | --- | --- | --- |
| Lo llama este asistente | Sí | No | No | No |
| Sesión iniciada, sin clave dentro del programa | Sí, con `grok login` | Sí, en el navegador, o con una clave de API | Sí, con la cuenta de ChatGPT, o con una clave de API | Sí, en la aplicación de ChatGPT |
| Datos actuales de la web | Sí. La búsqueda y la lectura de páginas están activas en una pregunta hablada | Sí | Sí. La búsqueda está activa. Las páginas en vivo son un ajuste aparte | Sí, dentro de ChatGPT |
| Seguir la misma conversación | Sí | Sí | Sí | Sí, dentro de ChatGPT |
| Cambiar archivos de este equipo | Solo si un administrador lo permite. La shell sigue apagada | Sí. Para eso está la herramienta | Sí, dentro de un recinto | No. Quien edita archivos es Codex |
| Voz, nombre y huella | Los pone este asistente | Tendría que ponerlos este asistente | Tendría que ponerlos este asistente | La voz de ChatGPT es otro producto |
| Dónde va el audio | Se queda en este equipo. Sale el texto | Esa herramienta no oye la habitación | Esa herramienta no oye la habitación | El audio de su voz va a OpenAI |

Claude, en esta tabla, es Claude Code, el programa de terminal. El chat de claude.ai es otra ventana de conversación. ChatGPT es la aplicación de charla y de voz. Codex es el programa de terminal que entra con esa misma cuenta. Gemini CLI y GitHub Copilot CLI están en el mismo grupo que Claude Code y Codex: se abren a propósito para trabajar en código, y no son la voz de la casa.
