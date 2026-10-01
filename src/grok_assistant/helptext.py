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
prueba
identifica mi voz
"""


# title, what it does, example. Spoken help stays short. This is the window.
HELP_TOPICS = (
    (
        "Empezar a hablar",
        "Fuera de una conversación el micrófono oye, pero no manda nada a Grok. "
        "Para abrir la charla di un saludo. Si la pregunta va en la misma frase, también se envía. "
        "Si solo saludas, el oído espera hasta dos segundos por si la pregunta sigue. "
        "El nombre de fábrica es grok. Cambiar nombre pide el nombre y luego lo repites seis veces. "
        "Cada vez se enseña lo que se entendió, y esas variaciones también abren la charla.",
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
        "Estas frases cierran la charla en casa, sin llamar a la nube y sin la frase de espera. "
        "gracias, nada gracias, ok, vale, adiós, cierra y las variaciones que el modelo local reconozca acaban la charla. "
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
        "Motor escucha (STT)",
        "Elige el motor de STT, el que convierte la voz en texto. Teclado es escribir en esta ventana. Windows español es el dictado de escritorio de Windows y el audio se queda aquí. "
        "Si falta, la línea Windows español… instalar y el botón del Mercado lo bajan: Windows pide permiso de administrador. "
        "El motor de STT en streaming para español deja el audio en este PC y cierra la frase en menos de dos segundos después de callarte. "
        "Dentro de una conversación, lo que se oye pasa directo a Grok hasta un adiós. "
        "Si el teclado era el único oído y ese motor ya está en el disco, al arrancar se elige él. "
        "Whisper pequeño, Whisper base, Whisper small, Canary y Cohere están en Mercado. Zipformer francés y Zipformer inglés también. Descargar los deja listos y entonces el menú permite elegirlos. Un Zipformer de otro idioma no se elige solo.",
        "comando reconocedor teclado",
    ),
    (
        "Canción",
        "Pide una canción por el título. Puede ir sin la palabra comando. Cabe hasta dieciséis palabras. "
        "La primera vez baja yt-dlp y mpv a este equipo. Buscan el audio en YouTube y lo ponen aquí, sin cuenta. "
        "Mientras suena, el micrófono está cerrado. La voz pausa la música y luego la sigue, salvo que tú la hayas pausado.",
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
        "Un agente es un Grok de tu cuenta, no el cuaderno local. La lista junta los que guardas en este PC y los que esa cuenta ya publica. "
        "Puede recordar fechas, sitios y listas, y buscar. "
        "Abrir uno dice su nombre y las preguntas siguientes van a él. Cerrar agente vuelve al asistente normal y no borra al agente. "
        "Crear uno guarda un archivo en este PC y pide la contraseña de administrador.",
        "comando abrir agente compras",
    ),
    (
        "Administrador",
        "La contraseña y el modo están en Ajustes. En el disco solo queda un hash. No hay clave de fábrica. "
        "El modo dura cinco minutos. Hace falta para crear un agente, listar las personas identificadas y borrar una. "
        "Apagar el equipo no pide esa clave: pide sí o no, y luego el apagado normal del sistema.",
        "comando modo administrador",
    ),
    (
        "Personas e identificar la voz",
        "identifica mi voz pregunta el nombre y graba dieciséis frases una sola vez. "
        "Un pitido agudo abre cada frase y otro más grave la cierra. Una pausa breve deja la frase abierta. "
        "El motor que escucha no decide si la frase era la esperada. Se guarda el sonido en crudo y con él se hace la huella, la misma para todos los motores. "
        "Cada motor se valora con esas frases, porque ya se sabe lo que había que decir. "
        "Al lado del motor sale el acierto de esa persona, por ejemplo (92%). Es información. "
        "El motor se elige sumando todas las huellas, al arrancar, y se escribe en Depuración. "
        "Cambiarlo está en Escucha. Las huellas y la identificación están en Personas. "
        "Si las tomas no son una sola voz, no se guarda a otra persona. "
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
        "Saludos y esperas",
        "En Voz, Saludos marca el tipo y el tema de tres frases: la del arranque, la del saludo cuando hace rato que no hablas, "
        "y la espera mientras Grok busca. Ya están guardadas. Decirlas no pide internet.",
        "comando ayuda",
    ),
    (
        "Ayuda hablada",
        "comando ayuda dice en voz alta la lista corta. La explicación larga, con estos ejemplos, está en este menú.",
        "comando ayuda",
    ),
)


def help_topics() -> tuple:
    from grok_assistant.i18n import help_topics as packed

    rows = packed()
    return tuple(rows) if rows else HELP_TOPICS


def spoken_help() -> str:
    from grok_assistant.i18n import screen_help

    source = screen_help() or SCREEN_HELP
    lines = []
    for line in source.splitlines():
        clean = line.replace("¦", ",").replace('"', "")
        lines.append(clean)
    return ". ".join(lines)
