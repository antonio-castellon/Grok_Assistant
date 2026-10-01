[← README.ES.md](../../README.ES.md)

# Qué está funcionando de verdad

El diagrama anterior resume el producto completo. Estas son las piezas que hacen que funcione.

| Pieza | Dónde vive | Qué tiene permitido hacer |
| --- | --- | --- |
| Motor de STT | `listen.py`, `kroko_ear.py`, `listeners/dictation.ps1` | Convertir el sonido en texto en este PC. El motor de STT en streaming transmite el español en local. El dictado de Windows en español, cuando ese motor está. El teclado está siempre. |
| Reglas | `brain.py`, `match.py`, `textutil.py` | Decidir si se ignora, si es una orden local o si va a la nube. Un carácter mal puesto sigue coincidiendo con una orden local. Dos, no. |
| Cuaderno | `store.py`, `%APPDATA%\GrokAssistant` | Guardar sesiones, nombres de quien habla y el historial de depuración. La sesión compartida se sustituye a las 24 horas. |
| Contraseña | `auth.py` | Guardar un hash con sal. La contraseña en sí no se escribe nunca. |
| Boca | `speech.py`, `scripts/speak.ps1` | Hablar con una voz local. Las voces en español se ofrecen primero. |
| Música | `music.py` | Reproducir audio con `yt-dlp` y `mpv` cuando los dos existen. Mientras suena una canción, el micrófono sigue abierto y solo sigue una huella guardada. |
| Puerta a la nube | `hub.py`, `grok_cli.py` | Llamar al comando local `grok` con una línea de texto ya terminada. No hay argumento de audio. |
| Agentes | `~/.grok/agents` y la cuenta | Los de este PC y los que publica la cuenta iniciada. Abrir uno es una elección. Su memoria no es el cuaderno local. |
| Carcasa | `tray.py` | Icono de bandeja, ventana de información, transcripción de depuración. Cerrar una ventana deja el programa en marcha. |

Una frase se considera terminada cuando la persona deja de hablar. El motor de STT y el reconocimiento de Windows suelen cerrarla en menos de dos segundos. Mientras el asistente responde, el micrófono se pausa para no tomar su propia voz por una orden nueva. Mientras suena una canción sigue abierto y solo atiende una huella guardada. Véase [Huellas y oídos](huellas.md). Una vez iniciada una conversación, el texto reconocido pasa directamente a Grok hasta que se dice adiós.

Fuera de una conversación activa, el asistente es deliberadamente estricto. Las frases de más de seis palabras se ignoran, salvo que sean una activación válida o `pon la canción` seguido de un título, que puede llegar hasta dieciséis palabras. Durante una conversación desaparece el límite de seis palabras. Sesenta segundos de inactividad terminan la charla; el tiempo empleado esperando una respuesta de la nube no cuenta para ese límite. El modo administrador permanece activo durante cinco minutos.

Grok se utiliza de dos formas distintas, cada una con un propósito concreto.

- Una orden mal oída es una clasificación. Un turno, sin búsqueda web, sin herramientas, un solo objeto JSON (`accion`, `orden`, `texto`). Si la línea reparada es una orden conocida, el asistente pregunta sí o no y solo entonces la ejecuta.
- Una pregunta de verdad es una conversación. El modelo puede buscar en la web. Las herramientas se limitan a esa búsqueda. El directorio de trabajo es la carpeta de datos del asistente, así que una voz en la cocina no está metida en un árbol de código. El primer turno crea un id de sesión. Los siguientes lo reanudan. Las líneas ignoradas no entran en esa sesión, porque no se enviaron.

Si hay un agente abierto, la pregunta usa el archivo de ese agente y la sesión de ese agente. `cerrar agente` vuelve al asistente normal. El cuaderno local se queda donde estaba.

Las frases habladas, las palabras de las órdenes, la ayuda y las personalidades están en `src/grok_assistant/lang/`. `hellos-es.txt` y `waits-es.txt` son las frases en español que la voz va rotando. `brain.py` y `hub.py` siguen igual.

Al arrancar, el asistente elige el siguiente saludo de la lista y empieza a escuchar. Mientras espera una respuesta de la nube, utiliza la siguiente frase breve de espera. Ambas listas son largas a propósito, para que no repita la misma frase cada mañana.
