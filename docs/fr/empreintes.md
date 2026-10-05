[← README.FR.md](../../README.FR.md)

# Empreintes et oreilles

Chaque microphone a sa propre empreinte. Le choisir utilise celle enregistrée avec lui. Un microphone qui n'a pas encore la sienne garde l'empreinte précédente, et un nouvel enregistrement sur le microphone que l'on va utiliser correspond mieux. Une fenêtre montre la phrase et ce que le moteur entend. Réessayer reprend cette phrase. Suivant passe à la suivante. Quitter jette les sons de cet enregistrement. Le programme garde le son brut de chaque phrase avec la personne. Le moteur qui écoute ne décide pas si la phrase était la bonne. Avec ce même son il fait l'empreinte, puis passe chaque moteur sur les phrases. Les phrases sont connues, donc il note combien chacun en retrouve. L'utilisateur choisit dans Écoute le moteur qui entend bien sur ce micro.

Ce sont seize phrases différentes, une fois chacune. Il en faut plusieurs pour que l'empreinte et le pourcentage soient fins. Une prise qui ne va pas avec les autres reste hors de l'empreinte. Le son brut des seize phrases est quand même gardé. S'il ne reste pas une seule voix claire, l'empreinte de la personne n'est pas remplacée.

**Personnes → Empreintes** liste chaque personne. Sous le nom, le nombre de prises. À côté de chaque moteur installé, le taux de cette personne, par exemple `Whisper pequeño (92%)`. C'est une information : ça ne choisit pas le moteur. Enregistrer un profil note tous les moteurs. Au démarrage, le programme additionne les réussites de toutes les empreintes et garde le moteur le plus haut. Il l'écrit dans Débogage. Le moteur se change dans **Écoute → Moteur d'écoute (STT)**. Un moteur qui n'est pas encore là est noté à l'installation, sans reparler. **Réenregistrer** répète les seize phrases.

Le son et l'empreinte sont dans `dist/data/`, à côté de `GrokAssistant.exe`. Reconstruire le programme remplace l'exécutable et laisse ce dossier. `dist/data/` est dans `.gitignore`. Le clavier n'a pas d'empreinte : il n'y a pas de micro.
