[← README.FR.md](../../README.FR.md)

# Aspect

Réglages → Aspect choisit les couleurs de la fenêtre et du menu de l'icône. Les boutons et les onglets sont arrondis dans tous les aspects.

Ceux qui viennent avec le programme sont Noche, Aurora, Cobre, Día, Lino, Mar et Oliva. Noche est celui des photos, et celui qui sert quand une couleur manque. Aurora est indigo, Cobre est bois et cuivre, Día est clair, Lino est un lin plus clair, Mar est une mer sombre et Oliva est un vert profond. Noche est en premier. Les autres suivent par le nom.

## Le changer

1. Copie [le modèle](../themes/template.json). Il a les mêmes couleurs que Noche. Le fichier du programme est [`noche.json`](../../src/grok_assistant/ui/themes/noche.json).
2. Enregistre-le sous `themes/mon-aspect.json` dans le même dossier que `GrokAssistant.exe`. Le nom du fichier, sans `.json`, est l'id. Un lancement depuis les sources lit `dist/themes/`.
3. Change `"name"`. C'est ce que le menu affiche.
4. Change les couleurs que tu veux. Une couleur absente, ou qui n'est pas `#` suivi de six chiffres, reste celle de Noche.
5. Ouvre Réglages → Aspect et choisis le nom.

Un fichier avec le même id qu'un aspect inclus le remplace. `themes/noche.json` change Noche. Un autre id ajoute une ligne.

Pour un petit essai, sans copier tout le modèle, un fichier comme celui-ci suffit :

```json
{
  "name": "Casa",
  "bg": "#14181e",
  "ink": "#e7eef2"
}
```

## Ce que peint chaque couleur

- `bg` est le fond de la fenêtre. `panel` est la bande du haut, avec la configuration et les onglets, et la bande du bas, avec la version.
- `ink` est le texte. `muted` est le texte secondaire. `amber` est le titre. `teal` est l'attente et les liens. `green` est la conversation ouverte.
- `field` est le fond des zones de texte.
- `button` et `button_active` sont les boutons et l'onglet choisi.
- `pause` et `pause_active` sont le grand bouton pause. Son texte utilise `teal`.
- `quit` et `quit_active` sont le grand bouton quitter. Son texte utilise `amber`.
- `chip_ink` est le texte posé sur le vert.
- `time` et `mode_ink` sont l'heure et le mode dans le journal.
- `danger` est le compte quand il monte haut. `select` est la coche du menu.
- `flow_on`, `flow_off` et `flow_dim` sont le schéma Flux.
- `menu_bg`, `menu_hot`, `menu_ink`, `menu_muted` et `menu_line` sont le menu de l'icône. Ils sont à part des couleurs de la fenêtre.

`font`, `font_bold` et `mono` sont facultatifs. Ce sont des listes, par exemple `["Segoe UI", 12]`. S'ils manquent, le programme utilise Segoe UI et Consolas.
