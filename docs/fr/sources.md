[← README.FR.md](../../README.FR.md)

# Le lancer depuis les sources

```powershell
cd C:\DEV.Personal\Grok_Assistant
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m grok_assistant
```

`--console` permet de saisir au clavier le texte qui viendrait normalement du microphone. C'est pratique pour tester la reconnaissance vocale — ou simplement quand on n'a pas envie de parler à son bureau.

```powershell
.venv\Scripts\python -m grok_assistant --console
```

Les empreintes et le son brut vivent dans `dist/data/`, à côté de l'exécutable. Une personne a une empreinte. Chaque moteur est noté avec ce même son. Les données, les sessions, le hash du mot de passe et le journal de l'oreille vivent dans `%APPDATA%\GrokAssistant` sous Windows et dans `~/.config/grok-assistant` sous Linux. Les agents créés ici vont dans `~/.grok/agents`. Le menu montre aussi ceux que le compte connecté publie. Aucun des deux ne vit dans cette copie git. L'assistant utilise son propre dossier de données. Il ne travaille pas dans un arbre de sources plein de projets.

La musique a besoin de `yt-dlp` et de `mpv`. S'ils manquent, la première chanson les télécharge. Si ça échoue, l'assistant le dit en une phrase.
