[Read in English](README.md) · [Leer en español](README.ES.md) · [Auf Deutsch lesen](README.DE.md)

![Marque Grok, avec Assistance en dessous](docs/img/banner.jpg)

# Grok Assistant

J'ai attendu des années que l'Amazon Echo écoute mieux. Il est resté un haut-parleur avec un anneau lumineux, alors j'ai fait le mien pour une personne âgée qui a déjà un petit ordinateur portable à portée de main.

Dans mon cas, cette personne est mon père. Sa vue est limitée, et il passe de longues heures seul. Je voulais une voix capable de tenir une conversation et d'expliquer les choses, sans écran à chercher et sans petit texte à lire. C'est possible maintenant. Grok, sur cette machine, est le chemin par lequel arriveront d'autres fonctions et d'autres intégrations. Si quelqu'un dans la famille en sait un peu plus et préfère ne pas laisser un portable ouvert, le même assistant est celui que je monte sur un Raspberry Pi 4 de 4 Go, et je publierai bientôt son code aussi, pour qu'on puisse le cloner si on préfère un appareil à soi.

Il peut continuer d'écouter tant que le programme est ouvert. Le son reste sur l'ordinateur. Une phrase devient du texte ici, et Grok ne reçoit ce texte que lorsqu'il était destiné à l'assistant : un bonjour, puis une question, un ordre qui commence par `commande`, ou une chanson demandée. La conversation de tous les jours s'écrit dans une session locale et y reste. Un ordre mal entendu peut être vérifié avec Grok, et il attend quand même un oui avant de l'exécuter.

Toute l'idée est là. Voici la fenêtre pendant qu'il écoute, et le menu de la barre des tâches avec Langue ouvert.

![La fenêtre d'information, à l'écoute, avec le journal en direct en dessous](docs/img/app-window.png)

![Le menu de la barre des tâches, avec la liste des langues ouverte](docs/img/tray-menu.png)

Le dessin ci-dessous est le chemin d'une phrase.

![Comment une phrase se déplace : l'oreille reste locale, et seul un texte de question ou d'ordre réparé part vers Grok](docs/img/flow.svg)

## L'espagnol d'abord, parce que la maison est bruyante

L'espagnol est la langue de la maison, donc l'assistant commence là. Les réponses restent courtes. Un long discours est difficile à suivre quand il y a du bruit.

Le point difficile est le STT, la voix vers le texte. C'est l'étape qui transforme une voix en mots, sur cet ordinateur. L'audio ne sort pas. Les modèles locaux qui le font, Kroko et Whisper, entendent souvent un mot de travers. « Hola » peut arriver comme « ola ». Un nom anglais peut arriver en espagnol. Le reste de l'application dépend de ce texte. Si les mots sont faux, l'ordre est faux, et la question n'arrive pas à Grok.

Kroko est l'oreille espagnole. Whisper base garde les noms anglais, et il lit le français, l'allemand et l'anglais. Le menu Langue change déjà la langue. Voice market télécharge une oreille quand on le demande.

## Sessions et agents

Une session est le cahier de la discussion. Elle reste sur cet ordinateur. Le cahier partagé recommence au bout de 24 heures. Un cahier avec un nom reste jusqu'à ce qu'on le supprime. Ce cahier n'est pas le compte Grok.

Un agent est un Grok de ton compte. On l'ouvre exprès avec `commande ouvre l'agent …` (en espagnol, `comando abrir agente …`). Il peut retenir des dates, des lieux et des listes, et il peut chercher. Cette mémoire reste dans le compte, donc le même agent s'ouvre sur un autre ordinateur où tu es déjà connecté. Le créer demande le mot de passe administrateur.

Dire au revoir (`merci`, `d'accord`) termine la discussion. Ça ne ferme pas la session. Fermer la session revient au cahier partagé. `commande ferme l'agent` revient à l'assistant normal. Ça n'efface pas l'agent. L'agent n'a pas besoin que ce portable reste allumé. Il faut lui parler exprès.

## Pourquoi Grok, et pas une autre fenêtre de chat

Un chat ordinaire peut écrire un programme et le rendre comme du texte. Quelqu'un doit encore mettre ce texte dans le bon dossier et le faire tourner.

Grok Build est déjà sur cet ordinateur, et il est connecté. Il n'y a pas de clé d'API à coller. Tu ouvres ce dossier et il peut lire l'assistant, le changer, lancer les tests et laisser le nouveau programme ici. L'idée est la même que [OpenClaw](https://github.com/openclaw/openclaw) : les instructions sont de simples fichiers, donc une étape nouvelle peut s'écrire comme un fichier.

Une question sur la météo ne change pas le programme. Changer le programme est une autre étape, et on l'ouvre exprès.

## Ce qui tourne vraiment

Le schéma plus haut est tout le produit. Voici les pièces qui le font.

| Pièce | Où elle vit | Ce qu'elle a le droit de faire |
| --- | --- | --- |
| Oreille | `listen.py`, `kroko_ear.py`, `listeners/dictation.ps1` | Transformer le son en texte sur ce PC. Kroko diffuse l'espagnol en local. Dictée Windows en espagnol quand ce reconnaisseur est là. Le clavier est toujours là. |
| Règles | `brain.py`, `match.py`, `textutil.py` | Décider d'ignorer, d'un ordre local, ou du nuage. Une lettre fausse correspond encore à un ordre local. Deux, non. |
| Cahier | `store.py`, `%APPDATA%\GrokAssistant` | Garder les sessions, les noms et l'historique de dépuration. La session partagée est remplacée au bout de 24 heures. |
| Mot de passe | `auth.py` | Garder un hash salé. Le mot de passe lui-même n'est jamais écrit. |
| Bouche | `speech.py`, `scripts/speak.ps1` | Parler avec une voix locale. Les voix espagnoles sont proposées d'abord. |
| Musique | `music.py` | Jouer l'audio avec `yt-dlp` et `mpv` quand les deux sont là. L'oreille se ferme pendant une chanson. |
| Porte du nuage | `hub.py`, `grok_cli.py` | Appeler la commande locale `grok` avec une ligne de texte finie. Il n'y a pas d'argument audio. |
| Agents | `~/.grok/agents` | Définitions sur ce compte. En ouvrir un est un choix. Leur mémoire n'est pas le cahier local. |
| Coque | `tray.py` | Icône de barre, fenêtre d'information, journal. Fermer une fenêtre laisse le programme tourner. |

Une phrase se termine quand la personne s'est arrêtée. Kroko et l'oreille Windows la ferment en moins de deux secondes. Un bonjour seul reste ouvert deux secondes, au cas où la question suit dans le même souffle. Pendant que l'assistant parle, cette oreille est en pause, pour que la réponse ne soit pas prise pour un nouvel ordre. La même pause vaut pour la musique. Dans une conversation, ce qui a été entendu va droit à Grok jusqu'à l'au revoir.

Hors conversation, les règles sont étroites. Plus de six mots est laissé, sauf si la ligne est un vrai appel ou `mets la chanson` plus un titre, jusqu'à seize mots. Dans une conversation, la barrière des six mots n'est plus là. Soixante secondes sans rien de nouveau terminent la discussion. Le temps passé à attendre le nuage ne compte pas. Le mode administrateur dure cinq minutes.

Deux appels existent, et ils ne sont pas interchangeables.

- Un ordre embrouillé est un classement. Un tour, pas de recherche web, pas d'outils, un seul objet JSON (`accion`, `orden`, `texto`). Si la ligne réparée est un ordre connu, l'assistant demande oui ou non et seulement alors l'exécute.
- Une vraie question est une conversation. Le modèle peut chercher sur le web. Les outils se limitent à cette recherche. Le dossier de travail est le dossier de données de l'assistant, donc une voix dans la cuisine n'est pas plantée dans un arbre de sources. Le premier tour crée un identifiant de session. Les tours suivants le reprennent. Les lignes ignorées ne sont jamais dans cette session, parce qu'elles n'ont jamais été envoyées.

Si un agent est ouvert, la question utilise le fichier de cet agent et la session de cet agent. Fermer l'agent revient à l'assistant normal. Le cahier local reste où il était.

Les phrases parlées, les mots des commandes, l'aide et les personnalités sont dans `src/grok_assistant/lang/`. `hellos-es.txt` et `waits-es.txt` sont les phrases espagnoles que la voix fait tourner. `brain.py` et `hub.py` restent les mêmes.

Au démarrage, il dit le bonjour suivant, puis il se tait. Pendant l'attente du nuage, il dit la phrase courte suivante de l'autre liste. Les listes sont longues pour que la même phrase ne revienne pas chaque matin.

## Ce qu'on peut dire

On commence avec `bonjour grok` en français, ou `hola grok` et `¿estás ahí?` en espagnol, la langue de départ. Hors conversation, les autres ordres commencent par `commande` (ou `comando`). Une phrase de plus de six mots est ignorée, sauf si c'est un vrai bonjour ou une chanson plus un titre (jusqu'à seize mots). Dans une conversation, il n'y a pas de limite de six mots. Une chanson n'a pas besoin du mot `commande`. L'au revoir reste sur cet ordinateur et il est immédiat. Pendant qu'une réponse arrive, on entend une phrase courte, le micro fait une pause, puis on entend la réponse. La fenêtre d'information a la liste des commandes.

L'icône de la barre est le programme. Le clic gauche ouvre la fenêtre. Le clic droit ouvre le menu. Fermer la fenêtre la cache. Quitter est le bouton, dans la fenêtre ou dans le menu.

## Lancer l'exécutable

Il n'y a pas d'installateur. `dist/GrokAssistant.exe` est tout le programme. On le copie n'importe où et on l'ouvre d'un double clic. Python n'a pas à être installé pour ce fichier. Une fenêtre s'ouvre avec le journal en direct — ce qui a été entendu, et ce qui se passe ensuite — et l'icône Grok reste dans la barre. Fermer la fenêtre la cache. Quitter est le bouton, ou Salir dans le menu de la barre.

Si Grok Build manque, ou si on ne s'est jamais connecté, le programme s'arrête sur une fenêtre avant la barre. **Instalar Grok Build** lance l'installateur officiel :

```powershell
irm https://x.ai/cli/install.ps1 | iex
```

**Iniciar sesión** ouvre `grok login`, qui passe par le navigateur. **Comprobar** demande à `grok models` si le compte est prêt. **Continuar** démarre l'assistant quand même, pour que les ordres locaux marchent encore pendant que le nuage est absent. Il n'y a pas de clé d'API à coller.

Pour reconstruire cet exécutable depuis ce dossier :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## Le lancer depuis les sources

```powershell
cd C:\DEV.Personal\Grok_Assistant
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m grok_assistant
```

`--console` tape ce que le micro aurait entendu. Utile avant qu'un moteur de voix existe, et utile aussi quand on n'a pas envie de parler à la table.

```powershell
.venv\Scripts\python -m grok_assistant --console
```

Les données, les sessions, le hash du mot de passe et le journal de l'oreille vivent dans `%APPDATA%\GrokAssistant` sous Windows et dans `~/.config/grok-assistant` sous Linux. Les fichiers d'agents vont dans `~/.grok/agents`, le dossier du compte Grok, pas cette copie git. L'assistant utilise son propre dossier de données. Il ne travaille pas dans un arbre de sources plein de projets.

La musique a besoin de `yt-dlp` et de `mpv`. S'ils manquent, la première chanson les télécharge. Si ça échoue, l'assistant le dit en une phrase.

## Ce que c'est

Une voix pour les heures où lire coûte et où la maison est silencieuse. La version portable est pour une personne âgée qui a déjà un petit ordinateur près d'elle. Le Raspberry Pi 4, de 4 Go, est le même assistant quand le portable devrait rester fermé. Le micro peut rester éveillé. Seule une phrase qui était destinée à l'assistant sort, et elle sort comme du texte.
