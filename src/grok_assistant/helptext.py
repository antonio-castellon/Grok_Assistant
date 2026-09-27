"""The on-screen command list. Speech reads the same lines, without the quotes."""

SCREEN_HELP = """\
iniciar: "hola grok" o "¿estás ahí?"   acabar: "gracias" o "vale"
COMANDOS (iniciar con palabra "comando")
SESION ( abrir ¦ crear ¦ borrar ) NOMBRE , listar , cerrar
AGENTE ( abrir ¦ crear ) NOMBRE , listar , cerrar
modo administrador
subir volumen
bajar volumen
voz NÚMERO
otra voz
otro reconocedor
pon la canción X
para la música
apaga el dispositivo
prueba
identifica mi voz
"""


# title, what it does, example. Spoken help stays short. This is the window.
HELP_TOPICS = (
    (
        "Empezar a hablar",
        "Fuera de una conversación el micrófono oye, pero no manda nada a Grok. "
        "Para abrir la charla di un saludo. Las palabras dichas en el mismo aliento que el saludo no se envían: la pregunta es la frase siguiente. "
        "También valen oídos cercanos, como hola grop u ok grok.",
        "hola grok",
    ),
    (
        "Preguntar",
        "Con la conversación abierta, una frase que no es una orden se envía como texto a tu cuenta de Grok. "
        "El audio no sale. Mientras busca, dice una frase corta de espera y el micrófono se apaga hasta que termina la respuesta.",
        "qué hora es",
    ),
    (
        "Acabar",
        "Estas frases cierran la charla en casa, sin llamar a la nube. "
        "gracias se contesta con De nada. vale, adiós, hasta luego o cierra conversación acaban la charla. "
        "No cierran la sesión con nombre ni borran un agente.",
        "gracias",
    ),
    (
        "Órdenes",
        "Casi toda orden empieza por la palabra comando. Una letra mal oída todavía vale. Dos, no. "
        "Si la frase no coincide aquí, Grok solo intenta repararla y luego hay que decir sí. "
        "Fuera de la charla, una frase de más de seis palabras se ignora, salvo el saludo o una canción.",
        "comando subir volumen",
    ),
    (
        "Volumen",
        "Sube o baja el volumen del asistente de cinco en cinco y dice el porcentaje nuevo.",
        "comando bajar volumen",
    ),
    (
        "Voces",
        "otra voz pasa a la siguiente voz instalada en este equipo. voz y un número elige esa voz de la lista del menú Voz.",
        "comando voz 2",
    ),
    (
        "Reconocedor",
        "Elige el oído. Teclado es escribir en esta ventana. Windows español es el dictado de escritorio de Windows y el audio se queda aquí. "
        "Si falta, la línea Windows español… instalar y el botón del Mercado lo bajan: Windows pide permiso de administrador. "
        "Kroko es el micrófono en español: el audio se queda en este PC y la frase queda lista en menos de dos segundos después de callarte. "
        "Dentro de una conversación, lo que se oye pasa directo a Grok hasta un adiós. "
        "Si el teclado era el único oído y Kroko ya está en el disco, al arrancar se elige Kroko. "
        "Whisper pequeño, Whisper base y Canary están en Mercado, al principio de la lista. Descargar los deja listos y entonces el menú permite elegirlos.",
        "comando reconocedor teclado",
    ),
    (
        "Canción",
        "Pide una canción por el título. Puede ir sin la palabra comando. Cabe hasta dieciséis palabras. "
        "Hace falta yt-dlp y mpv. Mientras suena, el micrófono está cerrado. La voz pausa la música y luego la sigue, salvo que tú la hayas pausado.",
        "pon la canción luna de miel",
    ),
    (
        "Música",
        "Pausa, sigue o para la canción que está sonando. No busca una nueva.",
        "comando para la musica",
    ),
    (
        "Sesiones",
        "La compartida es el cuaderno de esta máquina y se tira a las veinticuatro horas. "
        "Una sesión con nombre se queda hasta que la borras. Abrir cambia de cuaderno. "
        "Cerrar sesión vuelve a la compartida y, si había charla, la acaba. Crear y borrar piden sí o no. "
        "Nada de esto se sube solo: solo salen las preguntas que hagas dentro.",
        "comando crear sesion cocina",
    ),
    (
        "Agentes",
        "Un agente es un Grok de tu cuenta, no el cuaderno local. Puede recordar fechas, sitios y listas, y buscar. "
        "Abrir uno dice su nombre y las preguntas siguientes van a él. Cerrar agente vuelve al asistente normal y no borra al agente. "
        "Crear uno pide la contraseña de administrador.",
        "comando abrir agente compras",
    ),
    (
        "Administrador",
        "La contraseña se elige en el menú y en el disco solo queda un hash. No hay clave de fábrica. "
        "El modo dura cinco minutos. Hace falta para crear un agente, listar las personas identificadas y borrar una. "
        "Apagar el equipo no pide esa clave: pide sí o no, y luego el apagado normal del sistema.",
        "comando modo administrador",
    ),
    (
        "Personas e identificar la voz",
        "identifica mi voz pregunta el nombre y hace repetir cuatro frases. "
        "Sin el modelo de huella de voz te apunta, pero no cierra la puerta: sigue oyendo a todo el mundo. "
        "Con el modelo, solo esa persona pasa. Listar y borrar personas pide administrador.",
        "comando identifica mi voz",
    ),
    (
        "Prueba",
        "Entra en un modo que enseña en el registro lo que el oído escribió y no ejecuta nada. "
        "Al entrar lo dice: para salir, di salir, o usa Desactivar prueba en el menú Escucha.",
        "comando prueba",
    ),
    (
        "Ayuda hablada",
        "comando ayuda dice en voz alta la lista corta. La explicación larga, con estos ejemplos, está en este menú.",
        "comando ayuda",
    ),
    (
        "Apagar",
        "Pide sí o no. Sí apaga el equipo con el apagado normal del sistema. No, o cualquier otra frase, dice Vale y no apaga.",
        "comando apagar",
    ),
)


def spoken_help() -> str:
    lines = []
    for line in SCREEN_HELP.splitlines():
        clean = line.replace("¦", ",").replace('"', "")
        lines.append(clean)
    return ". ".join(lines)
