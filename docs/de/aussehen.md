[← README.DE.md](../../README.DE.md)

# Aussehen

Einstellungen → Aussehen wählt die Farben des Fensters und des Symbolmenüs. Schaltflächen und Reiter sind in jedem Aussehen abgerundet.

Mit dem Programm kommen Noche, Aurora, Cobre, Día, Lino, Mar und Oliva. Noche ist das der Bilder, und das, das gilt, wenn eine Farbe fehlt. Aurora ist Indigo, Cobre ist Holz und Kupfer, Día ist hell, Lino ist ein helleres Leinen, Mar ist ein dunkles Meer und Oliva ist ein tiefes Grün. Noche steht zuerst. Die anderen folgen nach dem Namen.

## Es ändern

1. Kopiere [die Vorlage](../themes/template.json). Sie hat dieselben Farben wie Noche. Die Datei im Programm ist [`noche.json`](../../src/grok_assistant/ui/themes/noche.json).
2. Speichere sie als `themes/mein-aussehen.json` im selben Ordner wie `GrokAssistant.exe`. Der Dateiname ohne `.json` ist die Id. Ein Start aus dem Quellbaum liest `dist/themes/`.
3. Ändere `"name"`. Das zeigt das Menü.
4. Ändere die Farben, die du willst. Eine fehlende Farbe, oder eine, die nicht `#` und sechs Ziffern ist, bleibt bei Noche.
5. Öffne Einstellungen → Aussehen und wähle den Namen.

Eine Datei mit derselben Id wie ein mitgeliefertes Aussehen ersetzt es. `themes/noche.json` ändert Noche. Eine andere Id fügt eine Zeile hinzu.

Für einen kleinen Versuch, ohne die ganze Vorlage zu kopieren, reicht eine Datei wie diese:

```json
{
  "name": "Casa",
  "bg": "#14181e",
  "ink": "#e7eef2"
}
```

## Was jede Farbe malt

- `bg` ist der Fenstergrund. `panel` ist das obere Band, mit der Konfiguration und den Reitern, und das untere Band, mit der Version.
- `ink` ist der Text. `muted` ist der zweite Text. `amber` ist der Titel. `teal` ist WARTEN und die Links. `green` ist das offene Gespräch.
- `field` ist der Grund der Textfelder.
- `button` und `button_active` sind die Schaltflächen und der gewählte Reiter.
- `pause` und `pause_active` sind die große Pause-Schaltfläche. Ihr Text nutzt `teal`.
- `quit` und `quit_active` sind die große Beenden-Schaltfläche. Ihr Text nutzt `amber`.
- `chip_ink` ist der Text auf dem Grün.
- `time` und `mode_ink` sind die Uhrzeit und der Modus im Protokoll.
- `danger` ist das Konto, wenn es hoch liegt. `select` ist das Häkchen im Menü.
- `flow_on`, `flow_off` und `flow_dim` sind das Ablaufdiagramm.
- `menu_bg`, `menu_hot`, `menu_ink`, `menu_muted` und `menu_line` sind das Symbolmenü. Sie stehen neben den Fensterfarben.

`font`, `font_bold` und `mono` sind optional. Sie sind Listen, zum Beispiel `["Segoe UI", 12]`. Fehlen sie, nimmt das Programm Segoe UI und Consolas.
