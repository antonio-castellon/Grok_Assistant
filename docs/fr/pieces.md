[← README.FR.md](../../README.FR.md)

# Ce qui tourne vraiment

Le schéma ci-dessus résume le produit dans son ensemble. Voici les composants qui le font fonctionner.

| Pièce | Où elle vit | Ce qu'elle a le droit de faire |
| --- | --- | --- |
| Moteur STT | `listen.py`, `kroko_ear.py`, `listeners/dictation.ps1` | Transformer le son en texte sur ce PC. Le moteur STT en flux diffuse l'espagnol en local. Dictée Windows en espagnol quand ce moteur est là. Le clavier est toujours là. |
| Règles | `brain.py`, `match.py`, `textutil.py` | Décider d'ignorer, d'un ordre local, ou du nuage. Une lettre fausse correspond encore à un ordre local. Deux, non. |
| Cahier | `store.py`, `%APPDATA%\GrokAssistant` | Garder les sessions, les noms et l'historique de dépuration. La session partagée est remplacée au bout de 24 heures. |
| Mot de passe | `auth.py` | Garder un hash salé. Le mot de passe lui-même n'est jamais écrit. |
| Bouche | `speech.py`, `scripts/speak.ps1` | Parler avec une voix locale. Les voix espagnoles sont proposées d'abord. |
| Musique | `music.py` | Jouer l'audio avec `yt-dlp` et `mpv` quand les deux sont là. Pendant une chanson, le micro reste ouvert et ne suit qu'une empreinte enregistrée. |
| Porte du nuage | `hub.py`, `grok_cli.py` | Appeler la commande locale `grok` avec une ligne de texte finie. Il n'y a pas d'argument audio. |
| Agents | `~/.grok/agents` | Définitions sur ce compte. En ouvrir un est un choix. Leur mémoire n'est pas le cahier local. |
| Coque | `tray.py` | Icône de barre, fenêtre d'information, journal. Fermer une fenêtre laisse le programme tourner. |

Une phrase se termine quand la personne s'est arrêtée. Le moteur STT et l'oreille Windows la ferment en moins de deux secondes. Un bonjour seul reste ouvert deux secondes, au cas où la question suit dans le même souffle. Pendant que l'assistant parle, cette oreille est en pause, pour que la réponse ne soit pas prise pour un nouvel ordre. Pendant une chanson le micro reste ouvert et ne suit qu'une empreinte enregistrée. Voir [Empreintes et oreilles](empreintes.md). Dans une conversation, ce qui a été entendu va droit à Grok jusqu'à l'au revoir.

Hors conversation, les règles sont étroites. Plus de six mots est laissé, sauf si la ligne est un vrai appel ou `mets la chanson` plus un titre, jusqu'à seize mots. Dans une conversation, la barrière des six mots n'est plus là. Soixante secondes sans rien de nouveau terminent la discussion. Le temps passé à attendre le nuage ne compte pas. Le mode administrateur dure cinq minutes.

Grok est appelé de deux manières distinctes, chacune avec un rôle bien précis.

- Un ordre embrouillé est un classement. Un tour, pas de recherche web, pas d'outils, un seul objet JSON (`accion`, `orden`, `texto`). Si la ligne réparée est un ordre connu, l'assistant demande oui ou non et seulement alors l'exécute.
- Une vraie question est une conversation. Le modèle peut chercher sur le web. Les outils se limitent à cette recherche. Le dossier de travail est le dossier de données de l'assistant, donc une voix dans la cuisine n'est pas plantée dans un arbre de sources. Le premier tour crée un identifiant de session. Les tours suivants le reprennent. Les lignes ignorées ne sont jamais dans cette session, parce qu'elles n'ont jamais été envoyées.

Si un agent est ouvert, la question utilise le fichier de cet agent et la session de cet agent. Fermer l'agent revient à l'assistant normal. Le cahier local reste où il était.

Les phrases parlées, les mots des commandes, l'aide et les personnalités sont dans `src/grok_assistant/lang/`. `hellos-es.txt` et `waits-es.txt` sont les phrases espagnoles que la voix fait tourner. `brain.py` et `hub.py` restent les mêmes.

Au démarrage, l'assistant choisit le prochain message d'accueil de la liste, puis se met à écouter. Lorsqu'il attend une réponse du cloud, il utilise la prochaine courte phrase d'attente. Les deux listes sont volontairement longues afin d'éviter de répéter la même phrase chaque matin.
