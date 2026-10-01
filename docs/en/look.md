[← README.md](../../README.md)

# Look

Settings → Look chooses the colors of the window and of the icon menu. Buttons and tabs are rounded in every look.

The ones that ship with the program are Noche, Aurora, Cobre, Día, Lino, Mar, and Oliva. Noche is the one in the pictures, and the one used when a color is missing. Aurora is indigo, Cobre is wood and copper, Día is light, Lino is a lighter linen, Mar is a dark sea, and Oliva is a deep green. Noche is listed first. The others follow by name.

## Changing it

1. Copy [the template](../themes/template.json). It has the same colors as Noche. The file in the program is [`noche.json`](../../src/grok_assistant/ui/themes/noche.json).
2. Save it as `themes/my-look.json` in the same folder as `GrokAssistant.exe`. The file name, without `.json`, is the id. A run from the source tree uses `dist/themes/`.
3. Change `"name"`. That is what the menu shows.
4. Change the colors you want. A missing color, or one that is not `#` plus six digits, stays on Noche.
5. Open Settings → Look and choose the name.

A file with the same id as a built-in one replaces it. `themes/noche.json` changes Noche. Another id adds a new row.

A small try, without copying the whole template, can be a file like this:

```json
{
  "name": "Casa",
  "bg": "#14181e",
  "ink": "#e7eef2"
}
```

## What each color paints

- `bg` is the window background. `panel` is the top band, with the settings and the tabs, and the bottom band, with the version.
- `ink` is the text. `muted` is the secondary text. `amber` is the title. `teal` is WAITING and the links. `green` is IN CONVERSATION.
- `field` is the background of the text boxes.
- `button` and `button_active` are the buttons and the selected tab.
- `pause` and `pause_active` are the large pause button. Its text uses `teal`.
- `quit` and `quit_active` are the large quit button. Its text uses `amber`.
- `chip_ink` is the text that sits on the green.
- `time` and `mode_ink` are the time and the mode in the log.
- `danger` is the account when it runs high. `select` is the menu tick.
- `flow_on`, `flow_off`, and `flow_dim` are the Flow diagram.
- `menu_bg`, `menu_hot`, `menu_ink`, `menu_muted`, and `menu_line` are the icon menu. They are separate from the window colors.

`font`, `font_bold`, and `mono` are optional. They are lists, for example `["Segoe UI", 12]`. When they are left out, the program uses Segoe UI and Consolas.
