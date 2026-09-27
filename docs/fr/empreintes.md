[← README.FR.md](../../README.FR.md)

# Empreintes et oreilles

Une empreinte mesure le morceau de micro, pas les mots. Chaque oreille coupe ce morceau à sa façon. Chaque moteur STT — Whisper petit, Whisper base, Canary et la dictée Windows — ne donne pas le même audio, donc une empreinte enregistrée avec une oreille n'identifie pas la personne quand une autre oreille est active.

**Administrador → Huellas** liste chaque personne. Sous le nom, chaque oreille montre combien de prises sont gardées, ou *sin huella* s'il n'y en a aucune. Une oreille qui n'est pas installée est marquée et ne peut pas encore être enregistrée. La choisir bascule l'écoute et enregistre douze prises pour cette oreille seulement.

Le fichier est `dist/data/speakers.json`, à côté de `GrokAssistant.exe`. Reconstruire le programme remplace l'exécutable et laisse ce dossier. `dist/data/` est dans `.gitignore`, donc les empreintes ne partent pas dans le dépôt. Le clavier n'a pas d'empreinte : il n'y a pas de morceau de micro.
