[← README.ES.md](../../README.ES.md)

# Aspecto

Ajustes → Aspecto elige el color de la ventana y del menú del icono. Los botones y las pestañas van redondeados en todos los aspectos.

Los que vienen con el programa son Noche, Aurora, Cobre, Día, Lino, Mar y Oliva. Noche es el de las fotos y el que se usa cuando falta un color. Aurora es índigo, Cobre es madera con cobre, Día es claro, Lino es un lino más claro, Mar es un mar oscuro y Oliva es verde oscuro. Noche sale el primero. Los demás, por el nombre.

## Cambiarlo

1. Copia [la plantilla](../themes/template.json). Lleva los mismos colores que Noche. El archivo del programa está en [`noche.json`](../../src/grok_assistant/ui/themes/noche.json).
2. Guárdala como `themes/mi-aspecto.json` en la misma carpeta que `GrokAssistant.exe`. El nombre del archivo, sin `.json`, es el id. Si arrancas desde el código, esa carpeta es `dist/themes/`.
3. Cambia `"name"`. Eso es lo que sale en el menú.
4. Cambia los colores que quieras. Un color que falte, o que no sea `#` y seis cifras, se queda en el de Noche.
5. Abre Ajustes → Aspecto y elige el nombre.

Un archivo con el mismo id que uno incluido lo sustituye. `themes/noche.json` cambia Noche. Otro id añade una fila nueva.

Para probar un cambio pequeño, sin copiar la plantilla entera, basta un archivo así:

```json
{
  "name": "Casa",
  "bg": "#14181e",
  "ink": "#e7eef2"
}
```

## Qué pinta cada color

- `bg` es el fondo de la ventana. `panel` es la banda de arriba, con la configuración y las pestañas, y la banda de abajo, con la versión.
- `ink` es el texto. `muted` es el texto secundario. `amber` es el título. `teal` es ESPERA y los enlaces. `green` es EN CONVERSACIÓN.
- `field` es el fondo de las cajas de texto.
- `button` y `button_active` son los botones y la pestaña elegida.
- `pause` y `pause_active` son el botón grande de pausa. Su texto usa `teal`.
- `quit` y `quit_active` son el botón grande de salir. Su texto usa `amber`.
- `chip_ink` es el texto que va sobre el verde.
- `time` y `mode_ink` son la hora y el modo en el registro.
- `danger` es la cuenta cuando va muy alta. `select` es la marca del menú.
- `flow_on`, `flow_off` y `flow_dim` son el diagrama de Flujo.
- `menu_bg`, `menu_hot`, `menu_ink`, `menu_muted` y `menu_line` son el menú del icono. Van aparte de los colores de la ventana.

`font`, `font_bold` y `mono` son opcionales. Van en lista, por ejemplo `["Segoe UI", 12]`. Si no están, se usan Segoe UI y Consolas.
