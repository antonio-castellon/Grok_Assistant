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


def spoken_help() -> str:
    lines = []
    for line in SCREEN_HELP.splitlines():
        clean = line.replace("¦", ",").replace('"', "")
        lines.append(clean)
    return ". ".join(lines)
