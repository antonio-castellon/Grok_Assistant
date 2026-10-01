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
        "El micrófono ya está escuchando, pero mientras la esquina diga ESPERA no se manda nada a Grok. "
        "Para abrir la charla, saluda por su nombre. Si la pregunta va en la misma frase, sale en ese momento. "
        "En la pestaña Simple eliges cómo quieres hablar: la pregunta en el mismo aliento, primero el saludo, o la charla abierta. "
        "De fábrica se llama grok. El nombre se cambia en Escucha, Cambiar nombre. Si el oído lo deforma, puedes repetirlo seis veces: "
        "cada repetición enseña lo que se oyó, y esas formas también sirven para despertarlo.",
        "hola grok",
    ),
    (
        "Preguntar",
        "Con la charla abierta, lo que no sea una orden se envía tal cual a tu cuenta de Grok. "
        "El audio se queda en este equipo: Grok solo recibe el texto. "
        "Mientras busca, dice una frase corta de espera y deja de escuchar, para no tomarse su propia voz por otra pregunta.",
        "qué hora es",
    ),
    (
        "Acabar",
        "gracias, vale o adiós cierran la charla aquí mismo. No llaman a la nube y no dicen la frase de espera. "
        "También valen las formas cercanas, como nada gracias u ok. "
        "Cerrar la charla no cierra una sesión con nombre ni borra un agente.",
        "gracias",
    ),
    (
        "Órdenes",
        "Casi todas empiezan por la palabra comando. Si el oído cambia una letra, todavía la reconoce. Con dos letras de diferencia, ya no. "
        "Si dices comando y lo que sigue no está en esta guía, Grok intenta reconocerlo. Si da con una orden conocida, te la repite y espera un sí antes de hacerla. "
        "Sin charla abierta, y sin identificador local, una frase de más de seis palabras no se tiene en cuenta, salvo un saludo o una canción.",
        "comando subir volumen",
    ),
    (
        "Volumen",
        "Sube o baja el volumen de la voz del asistente, de cinco en cinco, y dice en voz alta el porcentaje al que ha quedado.",
        "comando bajar volumen",
    ),
    (
        "Voces",
        "otra voz pasa a la siguiente voz instalada en este equipo. "
        "voz y un número elige esa entrada del menú Voz. El número es el que aparece delante del nombre.",
        "comando voz 2",
    ),
    (
        "Motor escucha (STT)",
        "Es quien convierte lo que dices en texto. Teclado significa escribir en esta ventana. "
        "Windows español es el dictado de escritorio y el audio no sale de este PC. Si no está instalado, Windows pide permiso de administrador para bajarlo, desde la línea Windows español… instalar o desde el botón del Mercado. "
        "El motor en streaming para español también se queda en este equipo y cierra la frase poco después de que te calles. "
        "Whisper pequeño, Whisper base, Whisper small, Canary, Cohere, Zipformer francés y Zipformer inglés están en el Mercado de voz. Hay que descargarlos antes de poder elegirlos. Un Zipformer de otro idioma no se elige solo. "
        "Dentro de una charla, el texto reconocido sigue hacia Grok hasta que te despides. "
        "Si al arrancar el único oído era el teclado y uno de estos motores ya está en el disco, se elige ese.",
        "comando reconocedor teclado",
    ),
    (
        "Canción",
        "Pide una canción por el título. No hace falta decir comando, y el título puede tener hasta dieciséis palabras. "
        "La primera vez se bajan yt-dlp y mpv a este equipo. Buscan el audio en YouTube y lo ponen aquí, sin cuenta. "
        "Mientras suena, el micrófono sigue abierto, pero solo atiende a una voz que ya tenga huella guardada, para no tomar la canción por una orden. "
        "Cuando el asistente habla, la canción se pausa y luego sigue, salvo que la hayas pausado tú.",
        "pon la canción luna de miel",
    ),
    (
        "Música",
        "Pausa, reanuda o para la canción que está sonando. No busca otra.",
        "comando para la musica",
    ),
    (
        "Sesiones",
        "La sesión compartida es el cuaderno de esta máquina. En la pestaña Simple eliges cuántos días se recuerdan: entra el día nuevo y sale el más antiguo. Por defecto es un día. "
        "Una sesión con nombre se queda hasta que la borras. Abrir sesión cambia de cuaderno. "
        "Cerrar sesión vuelve a la compartida y, si había una charla, la termina. Crear y borrar piden un sí. "
        "Nada de esto se sube por su cuenta. Solo salen las preguntas que hagas dentro.",
        "comando crear sesion cocina",
    ),
    (
        "Agentes",
        "Un agente es un Grok de tu cuenta, no el cuaderno de este PC. La lista junta los que guardas aquí y los que esa cuenta ya publica. "
        "Puede recordar fechas, sitios y listas, y puede buscar. "
        "Al abrirlo dice su nombre, y a partir de ahí las preguntas van a él. Cerrar agente vuelve al asistente de siempre y no lo borra. "
        "Crear uno guarda un archivo en este equipo y pide la contraseña de administrador.",
        "comando abrir agente compras",
    ),
    (
        "Administrador",
        "La contraseña y el modo están en Ajustes. En el disco solo se guarda un hash, nunca la contraseña, y no hay una clave de fábrica. "
        "El modo dura cinco minutos. Hace falta para crear un agente y para listar o borrar a las personas identificadas.",
        "comando modo administrador",
    ),
    (
        "Personas e identificar la voz",
        "identifica mi voz pregunta cómo te llamas y graba dieciséis frases, una sola vez. "
        "Un pitido agudo abre cada toma. La ventana enseña la frase que toca y lo que el motor ha oído. Reintentar repite esa frase, Seguir pasa a la siguiente y Salir tira el audio de esta grabación. "
        "Se guarda el sonido en crudo y con él se hace la huella, la misma para todos los motores. El motor que escucha no decide si dijiste lo que tocaba. "
        "Cada motor se puntúa con esas frases, porque ya se sabe lo que había que decir. El porcentaje que sale al lado, por ejemplo (92 %), es solo información. "
        "Al arrancar se elige el motor sumando todas las huellas, y esa elección se escribe en Depuración. Cambiarlo está en Escucha. Las huellas están en Personas. "
        "Si las tomas no son de una sola voz, el sonido se guarda y los motores se puntúan, pero la huella de esa persona no se cambia. "
        "Sin el modelo de huella, el asistente oye a todo el mundo. Con el modelo, solo pasa la persona reconocida. Listar y borrar personas pide el modo administrador.",
        "comando identifica mi voz",
    ),
    (
        "Prueba",
        "Sirve para ver, en el registro, lo que el oído ha escrito, sin que se ejecute nada. "
        "Al entrar lo dice. Para salir, di salir, o usa Desactivar prueba en el menú Escucha.",
        "comando prueba",
    ),
    (
        "Saludos y esperas",
        "En Voz, Saludos, marcas el tipo y el tema de tres frases que ya están guardadas: la del arranque, la del saludo cuando hace rato que no hablas, y la de espera mientras Grok busca. "
        "Decirlas no pide internet.",
        "comando ayuda",
    ),
    (
        "Ayuda hablada",
        "comando ayuda dice en voz alta la lista corta. La explicación larga, con un ejemplo en cada caso, es esta pantalla.",
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
