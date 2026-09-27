[Read in English](README.md)

![Marca de Grok, con Assistance debajo](docs/img/banner.jpg)

# Grok Assistant

Llevaba años esperando a que el Amazon Echo escuchara mejor. Siguió siendo un altavoz con un anillo de luz, así que hice el mío para una persona mayor que ya tiene un portátil pequeño cerca.

En mi caso esa persona es mi padre. Tiene la vista limitada y pasa muchas horas solo. Quería una voz que pueda conversar y explicar las cosas, sin una pantalla que buscar y sin letra pequeña que leer. Ahora es posible. Grok, en este equipo, es por donde llegarán más funciones e integraciones. Si alguien de la familia sabe un poco más y prefiere no dejar un portátil abierto, el mismo asistente es el que estoy montando en una Raspberry Pi 4 de 4 GB.

Puede seguir escuchando mientras el programa está abierto. El sonido se queda en el ordenador. Una frase se convierte en texto aquí, y Grok recibe ese texto solo cuando iba dirigido al asistente: un saludo, luego una pregunta, una orden que empieza por `comando`, o una canción que se ha pedido. La charla de todos los días se anota en una sesión local y ahí se queda. Una orden mal oída se puede consultar con Grok, y aun así espera un sí antes de ejecutarla.

Esa es la idea. El dibujo de abajo es el camino de una frase.

![Cómo se mueve una frase: el oído se queda en local, y solo una pregunta o una orden reparada envía texto a Grok](docs/img/flow.svg)

## Español primero, porque la casa es ruidosa

El primer idioma es el español. Es el que de verdad se habla en casa, así que es el sitio honesto para empezar el experimento. Un escritorio en silencio y unos auriculares harían quedar bien a cualquier asistente. La cocina no. La gente habla a la vez, la televisión sigue encendida, alguien pide una canción mientras otro está a mitad de una frase. Quiero ese ruido. La prueba es si un aviso y una orden corta siguen funcionando en una habitación real, y si todo lo demás se queda en la máquina cuando la habitación está desordenada.

Las respuestas son cortas a propósito. Una voz en una casa ruidosa que recita un párrafo ya ha perdido.

El francés, el alemán y el inglés llegarán después, cada uno en su versión. Cada idioma supone adaptar el oído, la boca y las voces: el motor de voz a texto, el motor de texto a voz, y la lista de voces que recorre `otra voz`. Los saludos, las frases de espera y las palabras de las órdenes viajan con el idioma. La regla de debajo no. Una frase sale solo cuando se le dijo al asistente.

En este PC la boca es la voz en español que Windows ya tenga, o una voz Piper elegida en Mercado, o espeak en Linux. La Pi tiene su propio conjunto Piper. El oído del micrófono en español es Kroko: un modelo local en streaming. El audio no sale de la máquina. Mercado lo descarga cuando se lo pides; si la carpeta ya está en el disco y el oído guardado seguía siendo el teclado, el asistente arranca Kroko solo. El teclado de la ventana de depuración sigue disponible. El dictado de Windows en español es el reconocedor de escritorio. Si ese idioma falta, Escucha y Mercado lo instalan a través del propio Windows. Whisper, base y Canary son los otros oídos, cada uno a la espera de su modelo. Un reconocedor en la nube no sirve de sustituto. Subir la habitación para probar una habitación ruidosa tiraría el experimento.

## El empleado que no necesita tu hardware

Una sesión local es un cuaderno. Vive en la carpeta de datos de esta máquina. La compartida se tira y empieza de nuevo a las 24 horas. Una con nombre se queda hasta que la borras. Nada de ese cuaderno es la cuenta de Grok.

Un agente es la otra criatura. Se abre a propósito (`comando abrir agente …`). Crearlo pide la contraseña de administrador, porque «poner en marcha a alguien que recuerda cosas y puede mirar internet» no es un truco para quien pasa por delante del micrófono. El agente es un agente de Grok en tu cuenta, no una sesión con otro nombre. Puede guardar fechas, sitios y listas, y puede buscar. Esa memoria se queda en la cuenta, así que otra máquina en la que ya hayas iniciado sesión puede abrir el mismo agente.

Esta es la parte que el Echo nunca ofreció y que el teléfono no va a alojar. El agente no necesita el ventilador de la Pi, este icono de la bandeja, ni un micrófono que un sistema operativo haya aceptado desbloquear. El ordenador del salón es un timbre. El empleado vive con la cuenta. Desconectas el timbre y el empleado sigue en nómina: llegas a él desde cualquier otro Grok con la sesión iniciada, cuando te apetezca trabajar, también a una hora en la que todos los aparatos de la casa hacen su mejor imitación de un ladrillo. El timbre no tiene que seguir despierto para que la oficina exista. La oficina, con poca educación, no oye la habitación. Hay que hablarle a propósito. Estar siempre encendido nunca quiso decir estar siempre compartiendo. El cilindro tenía una idea sobre eso. Era la idea equivocada, y venía con un anillo de luz.

`comando cerrar agente` vuelve al asistente normal. No borra el agente y no termina la conversación. Cerrar la conversación (`gracias`, `vale`, `adiós`, `cierra conversación`) no cierra la sesión. Cerrar la sesión vuelve al cuaderno compartido y, si estabas hablando, se detiene. La pantalla, o la bandeja, vuelve a esperar. La vida normal sigue, sin haberse subido.

## Por qué Grok, que es un taller y no otra ventana de chat

ChatGPT escribe un programa. Claude escribe uno cuidadoso. Los dos lo hacen en una ventana que vive en otro sitio, y luego devuelven el resultado como texto. Alguien tiene que saber qué es una carpeta, cuál es el archivo de verdad y qué comando convierte una sugerencia educada en un programa que de verdad se ejecuta. Ese alguien iba a ser yo, y ya estaba cansado.

Lo que quería es la forma de [OpenClaw](https://github.com/openclaw/openclaw): un agente que se queda en el ordenador, crece escribiendo sus propias instrucciones y hace aquí el trabajo de software. Las habilidades de OpenClaw son archivos sencillos, y por eso el agente puede aprender un truco nuevo escribiéndolo. Grok Build es esa idea con las garras ya en esta máquina. El comando `grok` está instalado aquí. Tiene la sesión iniciada. Apúntalo a esta carpeta y puede leer el asistente, cambiarlo, ejecutar las pruebas y dejar la siguiente versión en el mismo sitio. El programa de voz es el timbre. Grok Build es el taller detrás de la casa.

Por eso se puede seguir añadiendo sin empezar de cero. No hay una clave de API que buscar, ni un formulario que pregunte qué modelo entusiasma a internet esta semana. El asistente encuentra `grok` en la ruta, le pregunta a ese comando qué modelos puede ejecutar de verdad y usa la voz en español que el ordenador ya tiene. La configuración es el hecho de que Grok está instalado. Después puedo abrir esta carpeta con Grok y decir, en lenguaje normal, lo que todavía le falta a la casa. Un saludo más alto. Una orden nueva. Un reconocedor. Otra integración. Grok escribe el cambio en local y produce aquí el programa nuevo.

Una pregunta sobre el tiempo no puede reescribir el ordenador. Eso sería la mala idea del cilindro, con mejor gramática. El taller tiene su propia puerta, y se abre a propósito, igual que se abre un agente.

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

Una frase termina cuando el reconocedor decide que la persona ha parado. Kroko y el oído de Windows usan unos 3,5 segundos de silencio al final. Mientras el asistente habla, ese oído está en pausa, para que la respuesta no se oiga como una orden nueva. La misma pausa vale para la música.

Fuera de una conversación las reglas son estrechas. Más de seis palabras se descarta, salvo que la línea sea un aviso de verdad o `pon la canción` más un título, hasta dieciséis palabras. Dentro de una conversación el límite de seis palabras desaparece. Sesenta segundos sin nada nuevo terminan la charla. El tiempo esperando a la nube no cuenta. El modo administrador dura cinco minutos.

Hay dos llamadas distintas, y no se intercambian.

- Una orden mal oída es una clasificación. Un turno, sin búsqueda web, sin herramientas, un solo objeto JSON (`accion`, `orden`, `texto`). Si la línea reparada es una orden conocida, el asistente pregunta sí o no y solo entonces la ejecuta.
- Una pregunta de verdad es una conversación. El modelo puede buscar en la web. Las herramientas se limitan a esa búsqueda. El directorio de trabajo es la carpeta de datos del asistente, así que una voz en la cocina no está metida en un árbol de código. El primer turno crea un id de sesión. Los siguientes lo reanudan. Las líneas ignoradas no entran en esa sesión, porque no se enviaron.

Si hay un agente abierto, la pregunta usa el archivo de ese agente y la sesión de ese agente. `cerrar agente` vuelve al asistente normal. El cuaderno local se queda donde estaba.

El español hablado vive en unos pocos sitios, que es lo que un idioma posterior tiene que sustituir: `hellos-es.txt`, `waits-es.txt`, las palabras de las órdenes en `match.py`, las líneas de ayuda y los prompts de `prompts.py`. La cultura del reconocedor y la lista de voces cambian con ellos. `brain.py` y `hub.py` se quedan. Ese es el plan entero para el francés, el alemán y el inglés. La misma política de puerta. Un oído nuevo, una boca nueva y voces nuevas.

Al arrancar dice la siguiente línea de la lista de saludos y luego se calla. Una espera a la nube dice la siguiente línea de la otra lista. Las dos listas son largas para que el mismo chiste no vuelva cada mañana.

## Qué se puede decir

Se despierta con `hola grok` o `¿estás ahí?`. Fuera de una conversación, el resto de órdenes empieza por `comando`, y una frase terminada de más de seis palabras se ignora salvo que sea un aviso de verdad o `pon la canción` más un título (hasta dieciséis palabras). Dentro de una conversación no hay límite de seis palabras. Una canción se puede pedir sin la palabra `comando`. El adiós es local e inmediato. Mientras se busca una respuesta, se oye una línea corta de una lista larga que va rotando, el micrófono descansa y luego se oye la respuesta. Al arrancar dice la siguiente línea de otra lista, los saludos, y después se calla. Sin visita guiada. Sin soltar la lista de órdenes. La ventana de información tiene la lista, para quien prefiere leer antes que recibir una charla del altavoz.

La bandeja es la aplicación. El clic izquierdo abre la ventana de información. El clic derecho abre el menú: pausa, información, depuración, reconocedor, voz, modelo, sesiones, contraseña de administrador, salir. Cerrar una ventana no sale. Salir es una opción del menú, porque algunos llevamos años entrenados por el «¿seguro que quieres esconder la ventana y fingir que eso es una salida?».

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

Los datos, las sesiones, el hash de la contraseña y el registro local del oído viven en `%APPDATA%\GrokAssistant` en Windows y en `~/.config/grok-assistant` en Linux. Las definiciones de los agentes se escriben en `~/.grok/agents`, que es la carpeta de la cuenta de Grok, no esta copia de git. No apuntes el directorio de trabajo del asistente a un árbol de código lleno de proyectos. Ya se niega, y usa su propia carpeta de datos, porque una voz en la cocina no debería descubrir de pronto un interés por refactorizar.

La música quiere `yt-dlp` y `mpv` en el PATH. Si no están, el asistente lo dice, en una frase, y no finge tararear.

## Qué es esto

Una voz para las horas en las que leer cuesta y la casa está en silencio. La versión de portátil es para una persona mayor que ya tiene un ordenador pequeño cerca. La Raspberry Pi 4, de 4 GB, es el mismo asistente cuando el portátil debería quedarse cerrado. El micrófono puede seguir despierto. Solo sale como texto una frase que iba dirigida al asistente.
