[← README.ES.md](../../README.ES.md)

# Trucos

## La huella separa a las personas

La huella de voz está para que dos personas en el mismo sitio no se mezclen en una sola conversación. Cuando ya está lista, el micrófono sigue a una voz guardada. Otra persona que hable se queda fuera, antes del modelo local y antes de una orden. **Escucha → Activar prueba** muestra las palabras y no hace nada con ellas. La misma fila pasa a **Desactivar prueba**. `salir` también sale. La esquina pone PRUEBA.

## El micrófono forma parte de la huella

Un micrófono flojo o turbio hace menos seguras las palabras y la huella. La huella es la voz tal como la oyó ese micrófono. La misma persona en otro micrófono puede quedarse por debajo del parecido, aunque el texto de la pantalla sea el correcto. Conviene grabar la huella otra vez en el micrófono que se va a usar.

**Ajustes → Micrófono** cambia el micrófono. Si ese ya tiene huella, se usa esa. Un micrófono que aún no tiene la suya sigue con la huella anterior hasta que se grabe ahí. **Predeterminado** es el micrófono de Windows.

## Cómo acaba una frase

Una frase se cierra 1,2 segundos después de la última palabra nueva, cuando ya hubo al menos 0,4 segundos de voz. Un ruido más corto no cuenta. Con **Primero el saludo**, un saludo solo espera 2 segundos mientras la charla sigue cerrada, por si la pregunta viene detrás. Los minutos de Simple cierran la charla. No cierran la frase. Lo más rápido es el nombre y la pregunta en la misma respiración: «Hola grok, ¿qué hora es?».

## Mientras responde

El micrófono sigue abierto mientras el asistente habla. La huella descarta la voz del propio asistente. **Pausar escucha** y una grabación de huella sí cierran el micrófono. Mientras suena una canción, solo se sigue una voz guardada. Si otro programa ya tiene el micrófono, este no puede abrirlo. Elige otro micrófono, o cierra el programa que lo tiene.

## Qué dicen las líneas de depuración

`LLM: comando o accion no detectada` quiere decir que el modelo local pequeño no vio una orden. El motor de escucha sí oyó la frase. Con la charla cerrada, esa frase se queda en el equipo. Abre antes la charla, o pon la pregunta en la misma respiración que el nombre. **Limpiar registro** vacía la ventana de depuración. Las frases de después vuelven a salir. **Guardar traza** guarda un zip de esta ejecución. El audio de casa se queda en el equipo. Grok recibe el texto de una pregunta o de una orden.
