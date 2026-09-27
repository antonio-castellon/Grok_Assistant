[Read in English](README.md) · [Lire en français](README.FR.md) · [Auf Deutsch lesen](README.DE.md)

![Marca de Grok, con Assistance debajo](docs/img/banner.jpg)

# Grok Assistant

Llevaba años esperando a que el Amazon Echo escuchara mejor. Siguió siendo un altavoz con un anillo de luz, así que hice el mío para una persona mayor que ya tiene un portátil pequeño cerca.

En mi caso esa persona es mi padre. Tiene la vista limitada y pasa muchas horas solo. Quería una voz que pueda conversar y explicar las cosas, sin una pantalla que buscar y sin letra pequeña que leer. Ahora es posible. Grok, en este equipo, es por donde llegarán más funciones e integraciones. Si alguien de la familia sabe un poco más y prefiere no dejar un portátil abierto, el mismo asistente es el que estoy montando en una Raspberry Pi 4 de 4 GB, y publicaré en breve también su código para que se pueda clonar si se prefiere un dispositivo específico.

Puede seguir escuchando mientras el programa está abierto. El sonido se queda en el ordenador. Una frase se convierte en texto aquí, y Grok recibe ese texto solo cuando iba dirigido al asistente: un saludo, luego una pregunta, una orden que empieza por `comando`, o una canción que se ha pedido. La charla de todos los días se anota en una sesión local y ahí se queda. Una orden mal oída se puede consultar con Grok, y aun así espera un sí antes de ejecutarla.

Esa es la idea. Esta es la ventana mientras escucha, y el menú de la bandeja con Idioma abierto.

![La ventana de información, escuchando, con la depuración en vivo debajo](docs/img/app-window.png)

![El menú de la bandeja, con la lista de idiomas abierta](docs/img/tray-menu.png)

El dibujo de abajo es el camino de una frase.

![Cómo se mueve una frase: el oído se queda en local, y solo una pregunta o una orden reparada envía texto a Grok](docs/img/flow.svg)

## Español primero, porque la casa es ruidosa

El español es el idioma de casa, así que el asistente empieza ahí. Las respuestas son cortas. Un discurso largo se sigue mal cuando hay ruido.

La parte difícil es el STT, de voz a texto. Es el paso que convierte la voz en palabras, en este ordenador. El audio no sale. Los modelos locales que lo hacen, Kroko y Whisper, oyen mal una palabra con facilidad. «Hola» puede llegar como «ola». Un nombre en inglés puede llegar en español. El resto de la aplicación depende de ese texto. Si las palabras fallan, la orden falla, y la pregunta no llega a Grok.

Kroko es el oído en español. Whisper base guarda los nombres en inglés, y lee francés, alemán e inglés. El menú Idioma ya cambia el idioma. Voice market baja un oído cuando se lo pides.

## Sesiones y agentes

Una sesión es el cuaderno de la charla. Se queda en este ordenador. El cuaderno compartido vuelve a empezar a las 24 horas. Un cuaderno con nombre se queda hasta que lo borras. Ese cuaderno no es la cuenta de Grok.

Un agente es un Grok de tu cuenta. Se abre a propósito con `comando abrir agente …`. Puede recordar fechas, sitios y listas, y puede buscar. Esa memoria se queda en la cuenta, así que el mismo agente se abre en otro ordenador donde ya hayas iniciado sesión. Crearlo pide la contraseña de administrador.

Decir adiós (`gracias`, `vale`, `adiós`) cierra la charla. No cierra la sesión. Cerrar la sesión vuelve al cuaderno compartido. `comando cerrar agente` vuelve al asistente normal. No borra el agente. El agente no necesita que este portátil siga encendido. Hay que hablarle a propósito.

## Por qué Grok, y no otra ventana de chat

Un chat normal puede escribir un programa y devolverlo como texto. Alguien tiene que poner ese texto en la carpeta correcta y hacer que se ejecute.

Grok Build ya está en este ordenador, con la sesión iniciada. No hay una clave de API que pegar. Abres esta carpeta y puede leer el asistente, cambiarlo, pasar las pruebas y dejar aquí el programa nuevo. La idea es la de [OpenClaw](https://github.com/openclaw/openclaw): las instrucciones son archivos sencillos, así que un paso nuevo se puede escribir como un archivo.

Una pregunta sobre el tiempo no cambia el programa. Cambiar el programa es otro paso, y se abre a propósito.

## Qué está funcionando de verdad

El diagrama de más arriba es el producto entero. Estas son las piezas que lo implementan.

| Pieza | Dónde vive | Qué tiene permitido hacer |
| --- | --- | --- |
| Oído | `listen.py`, `kroko_ear.py`, `listeners/dictation.ps1` | Convertir el sonido en texto en este PC. Kroko transmite el español en local. El dictado de Windows en español, cuando ese reconocedor está. El teclado está siempre. |
| Reglas | `brain.py`, `match.py`, `textutil.py` | Decidir si se ignora, si es una orden local o si va a la nube. Un carácter mal puesto sigue coincidiendo con una orden local. Dos, no. |
| Cuaderno | `store.py`, `%APPDATA%\GrokAssistant` | Guardar sesiones, nombres de quien habla y el historial de depuración. La sesión compartida se sustituye a las 24 horas. |
| Contraseña | `auth.py` | Guardar un hash con sal. La contraseña en sí no se escribe nunca. |
| Boca | `speech.py`, `scripts/speak.ps1` | Hablar con una voz local. Las voces en español se ofrecen primero. |
| Música | `music.py` | Reproducir audio con `yt-dlp` y `mpv` cuando los dos existen. El oído se cierra mientras suena una canción. |
| Puerta a la nube | `hub.py`, `grok_cli.py` | Llamar al comando local `grok` con una línea de texto ya terminada. No hay argumento de audio. |
| Agentes | `~/.grok/agents` | Definiciones de esta cuenta. Abrir uno es una elección. Su memoria no es el cuaderno local. |
| Carcasa | `tray.py` | Icono de bandeja, ventana de información, transcripción de depuración. Cerrar una ventana deja el programa en marcha. |

Una frase termina cuando la persona ha parado. Kroko y el oído de Windows la cierran en menos de dos segundos. Mientras el asistente habla, ese oído está en pausa, para que la respuesta no se oiga como una orden nueva. La misma pausa vale para la música. Dentro de una conversación, lo oído pasa directo a Grok hasta el adiós.

Fuera de una conversación las reglas son estrechas. Más de seis palabras se descarta, salvo que la línea sea un aviso de verdad o `pon la canción` más un título, hasta dieciséis palabras. Dentro de una conversación el límite de seis palabras desaparece. Sesenta segundos sin nada nuevo terminan la charla. El tiempo esperando a la nube no cuenta. El modo administrador dura cinco minutos.

Hay dos llamadas distintas, y no se intercambian.

- Una orden mal oída es una clasificación. Un turno, sin búsqueda web, sin herramientas, un solo objeto JSON (`accion`, `orden`, `texto`). Si la línea reparada es una orden conocida, el asistente pregunta sí o no y solo entonces la ejecuta.
- Una pregunta de verdad es una conversación. El modelo puede buscar en la web. Las herramientas se limitan a esa búsqueda. El directorio de trabajo es la carpeta de datos del asistente, así que una voz en la cocina no está metida en un árbol de código. El primer turno crea un id de sesión. Los siguientes lo reanudan. Las líneas ignoradas no entran en esa sesión, porque no se enviaron.

Si hay un agente abierto, la pregunta usa el archivo de ese agente y la sesión de ese agente. `cerrar agente` vuelve al asistente normal. El cuaderno local se queda donde estaba.

Las frases habladas, las palabras de las órdenes, la ayuda y las personalidades están en `src/grok_assistant/lang/`. `hellos-es.txt` y `waits-es.txt` son las frases en español que la voz va rotando. `brain.py` y `hub.py` siguen igual.

Al arrancar dice el siguiente saludo y se calla. Mientras espera a la nube dice la siguiente frase corta de la otra lista. Las listas son largas para que la misma frase no vuelva cada mañana.

## Qué se puede decir

Se empieza con `hola grok` o `¿estás ahí?`. Fuera de una conversación, las demás órdenes empiezan por `comando`. Una frase de más de seis palabras se ignora, salvo que sea un saludo de verdad o `pon la canción` más un título (hasta dieciséis palabras). Dentro de una conversación no hay límite de seis palabras. Una canción no necesita la palabra `comando`. El adiós se queda en este ordenador y es inmediato. Mientras llega la respuesta se oye una frase corta, el micrófono descansa y luego se oye la respuesta. La ventana de información tiene la lista de órdenes.

El icono de la bandeja es el programa. El clic izquierdo abre la ventana. El clic derecho abre el menú. Cerrar la ventana la esconde. Salir es el botón, en la ventana o en el menú.

## Ejecutar el programa

No hay instalador. `dist/GrokAssistant.exe` es el programa entero. Se copia a cualquier sitio y se abre con doble clic. Para ese archivo no hace falta tener Python instalado. Se abre una ventana con la depuración en vivo — lo que se oyó y lo que pasa después — y el icono de Grok se queda en la bandeja. Cerrar la ventana la esconde. Salir es el botón, o Salir en el menú de la bandeja.

Si falta Grok Build, o si nunca se ha iniciado sesión, el programa se detiene en una ventana antes de la bandeja. **Instalar Grok Build** ejecuta el instalador oficial:

```powershell
irm https://x.ai/cli/install.ps1 | iex
```

**Iniciar sesión** abre `grok login`, que usa el navegador. **Comprobar** pregunta a `grok models` si la cuenta está lista. **Continuar** arranca el asistente de todos modos, para que las órdenes locales sigan funcionando mientras la nube no está. No hay una clave de API que pegar.

Para volver a construir ese ejecutable desde esta carpeta:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## Ejecutarlo desde el código

```powershell
cd C:\DEV.Personal\Grok_Assistant
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m grok_assistant
```

`--console` escribe lo que el micrófono habría oído. Sirve antes de que exista un motor de voz, y también cuando no quieres hablarle a la mesa.

```powershell
.venv\Scripts\python -m grok_assistant --console
```

Los datos, las sesiones, el hash de la contraseña y el registro del oído viven en `%APPDATA%\GrokAssistant` en Windows y en `~/.config/grok-assistant` en Linux. Los archivos de los agentes van a `~/.grok/agents`, la carpeta de la cuenta de Grok, no esta copia de git. El asistente usa su propia carpeta de datos. No trabaja dentro de un árbol de código lleno de proyectos.

La música necesita `yt-dlp` y `mpv`. Si faltan, la primera canción los descarga. Si eso falla, el asistente lo dice en una frase.

## Qué es esto

Una voz para las horas en las que leer cuesta y la casa está en silencio. La versión de portátil es para una persona mayor que ya tiene un ordenador pequeño cerca. La Raspberry Pi 4, de 4 GB, es el mismo asistente cuando el portátil debería quedarse cerrado. El micrófono puede seguir despierto. Solo sale como texto una frase que iba dirigida al asistente.
