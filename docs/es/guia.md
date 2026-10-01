[← README.ES.md](../../README.ES.md)

# Guía de uso

Pasos cortos para abrir el programa, dejarlo listo y hablar con él. Cada apartado largo está en su propio capítulo.

## Abrir

1. Haz doble clic en `GrokAssistant.exe`. No hay instalador y no hace falta Python.
2. Si sale una ventana de Grok Build, pulsa **Instalar Grok Build**, luego **Iniciar sesión** en el navegador y **Comprobar**. **Continuar** abre el asistente aunque la nube no esté lista. Las órdenes locales siguen funcionando. No hay una clave que pegar.
3. Se abre la ventana. Arriba a la derecha pone **ESPERA**. El icono de Grok queda en la bandeja.
4. Clic izquierdo en el icono: muestra la ventana. Clic derecho: abre el menú.
5. Cerrar la ventana la esconde. **Salir** cierra el programa.

## Configurar

Hazlo una vez, en este orden.

1. **Idioma.** Elige Español, Français, Deutsch o English. Los menús y las respuestas pasan a esa lengua.
2. **Motor escucha (STT).** Es el programa que pasa la voz a texto. Elige uno en el menú. Si falta, abre **Voice market**, pestaña **Motor escucha (STT)**, y descárgalo. Se puede elegir cuando llega al 100 %.
3. **Voz.** Elige una voz de la misma lengua. En **Voice market**, pestaña **Voces**, hay más. Solo salen las de la lengua activa.
4. **Huella.** **Administrador → Huellas → Nueva huella…**. Di las dieciséis frases una vez. El programa guarda el sonido, hace la huella para todos los motores y anota el acierto de cada uno, como `(92%)`. Esa lista informa. Al arrancar suma todas las huellas, deja el motor más alto y lo escribe en Depuración. El motor se cambia en **Escucha**.
5. **Contraseña.** Solo si vas a crear agentes. **Administrador → Contraseña…**. Escríbela dos veces. El programa guarda un resumen, no la contraseña en claro.
6. **Arranque con Windows** queda apagado hasta que lo actives en **Administrador**.

## Hablar

1. Di el nombre de aviso. Al principio es `hola grok`. Arriba a la derecha pasa a **EN CONVERSACIÓN**.
2. Habla. Una pregunta va a Grok. Una orden puede empezar por `comando`.
3. `gracias`, `vale` o `adiós` vuelven a **ESPERA**. La sesión no se borra.
4. Para una canción, di el título. La primera vez se descarga el reproductor.
5. El registro de la ventana muestra lo que se oyó. Debajo, `LLM:` es lo que decidió el modelo local y `Grok:` es la respuesta.

Más detalle: [Huellas y oídos](huellas.md) · [Qué se puede decir](decir.md) · [Ejecutar el programa](ejecutar.md)
