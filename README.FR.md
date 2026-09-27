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

La première langue est l'espagnol. C'est celle qu'on parle vraiment à la maison, donc c'est l'endroit honnête pour commencer l'expérience. Un bureau silencieux et un casque feraient paraître n'importe quel assistant malin. La cuisine, non. Les gens parlent en même temps, la télévision reste allumée, quelqu'un demande une chanson pendant qu'un autre est au milieu d'une phrase. Je veux ce bruit. L'épreuve, c'est de voir si un appel et un ordre court survivent encore dans une vraie pièce, et si tout le reste reste sur la machine quand la pièce est en désordre.

Les réponses restent courtes exprès. Une voix dans une maison bruyante qui récite un paragraphe a déjà perdu.

Le menu Langue bascule entre Español, Français, Deutsch et English. Les commandes, l'aide et les personnalités vivent dans `lang/*.json`, et ce menu peut modifier les commandes et l'aide de la langue qui est active. Une langue de plus, c'est un autre fichier json dans ce dossier. L'oreille doit suivre : Kroko écoute en espagnol, et Whisper base lit les autres. Choisir une langue autre que l'espagnol passe l'oreille à Whisper base quand ce modèle est déjà sur le disque. Les bonjours, les phrases d'attente et les mots des commandes voyagent avec la langue. La règle du dessous, non. Une phrase ne sort que lorsqu'elle a été dite à l'assistant.

Sur ce PC, la bouche est la voix espagnole que Windows a déjà, ou une voix Piper choisie dans Voice market, ou espeak sous Linux. Le Pi a son propre jeu Piper. L'oreille du micro en espagnol est Kroko : un modèle local en flux. L'audio ne quitte pas la machine. Voice market le télécharge quand on le demande ; une fois le dossier sur le disque, si l'oreille enregistrée était encore le clavier, l'assistant démarre Kroko tout seul. Le clavier de la fenêtre de débogage reste disponible. La dictée Windows en espagnol est le reconnaisseur de bureau. S'il manque, Écoute et Voice market l'installent par Windows lui-même. Whisper, base et Canary sont les autres oreilles, chacune en attente de son modèle. Un reconnaisseur dans le nuage ne sert pas de remplaçant. Envoyer la pièce pour tester une pièce bruyante jetterait l'expérience.

## L'employé qui n'a pas besoin de ton matériel

Une session locale est un cahier. Elle vit dans le dossier de données de cette machine. La session partagée est jetée et recommence au bout de 24 heures. Une session nommée reste jusqu'à ce qu'on la supprime. Rien de ce cahier n'est le compte Grok.

Un agent est l'autre créature. On l'ouvre exprès (`commande ouvre l'agent …`, ou en espagnol `comando abrir agente …`). Le créer demande le mot de passe administrateur, parce que « mettre en marche quelqu'un qui se souvient des choses et peut regarder internet » n'est pas un tour pour qui passe devant le micro. L'agent est un agent Grok de ton compte, pas une session renommée. Il peut garder des dates, des lieux et des listes, et il peut chercher. Cette mémoire reste avec le compte, donc une autre machine où tu es déjà connecté peut ouvrir le même agent.

C'est la partie que l'Echo n'a jamais offerte et que le téléphone n'hébergera pas. L'agent n'a pas besoin du ventilateur du Pi, de cette icône de barre des tâches, ni d'un micro qu'un système d'exploitation a bien voulu débloquer. L'ordinateur du salon est une sonnette. L'employé vit avec le compte. Tu débranches la sonnette et l'employé est toujours sur la liste de paie : tu le rejoins depuis n'importe quel autre Grok déjà connecté, quand tu as envie de travailler, y compris à une heure où tous les appareils de la maison font leur plus belle imitation d'une brique. La sonnette n'a pas à rester éveillée pour que le bureau existe. Le bureau, sans façon, n'entend pas la pièce. Il faut lui parler exprès. Toujours allumé n'a jamais voulu dire toujours partagé. Le cylindre avait une idée là-dessus. C'était la mauvaise, et elle venait avec un anneau lumineux.

`commande ferme l'agent` revient à l'assistant normal. Ça n'efface pas l'agent et ça ne termine pas la conversation. Fermer la conversation (`merci`, `d'accord`, `au revoir`) ne ferme pas la session. Fermer la session revient au cahier partagé et, si tu parlais, s'arrête. L'écran, ou la barre des tâches, se remet à attendre. La vie ordinaire reprend, sans avoir été envoyée.

## Pourquoi Grok, qui est un atelier et pas une autre fenêtre de chat

ChatGPT écrit un programme. Claude en écrit un soigneux. Les deux le font dans une fenêtre qui vit ailleurs, puis rendent le résultat comme du texte. Quelqu'un doit encore savoir ce qu'est un dossier, quel fichier est le vrai, et quelle commande transforme une suggestion polie en logiciel qui tourne vraiment. Ce quelqu'un, c'était moi, et j'étais déjà fatigué.

Ce que je voulais, c'est la forme d'[OpenClaw](https://github.com/openclaw/openclaw) : un agent qui reste sur l'ordinateur, grandit en écrivant ses propres instructions, et fait le travail logiciel ici. Les skills d'OpenClaw sont de simples fichiers, c'est pour ça que l'agent peut apprendre un nouveau tour en l'écrivant. Grok Build est cette idée avec les griffes déjà sur cette machine. La commande `grok` est installée ici. Elle est connectée. Pointe-la vers ce dossier et elle peut lire l'assistant, le changer, lancer les tests, et laisser la version suivante au même endroit. Le programme vocal est la sonnette. Grok Build est l'atelier derrière la maison.

C'est aussi pour ça qu'on peut en ajouter sans tout recommencer. Il n'y a pas de clé d'API à chercher, ni de formulaire qui demande quel modèle excite internet cette semaine. L'assistant trouve `grok` sur le chemin, demande à cette commande quels modèles elle peut vraiment faire tourner, et utilise la voix que l'ordinateur a déjà. La configuration, c'est le fait que Grok est installé. Ensuite je peux ouvrir ce dossier avec Grok et dire, en langage ordinaire, ce qu'il manque encore à la maison. Un bonjour plus fort. Un nouvel ordre. Un reconnaisseur. Une autre intégration. Grok écrit le changement ici et produit le nouveau programme ici.

Une question sur la météo n'a toujours pas le droit de réécrire l'ordinateur. Ce serait la mauvaise idée du cylindre, avec une meilleure grammaire. L'atelier a sa propre porte, et on l'ouvre exprès, de la même façon qu'on ouvre un agent.

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

Les phrases parlées, les mots des commandes, l'aide et les personnalités voyagent dans le paquet de langue, sous `src/grok_assistant/lang/`. `hellos-es.txt` et `waits-es.txt` sont encore les listes espagnoles que la voix fait tourner. `brain.py` et `hub.py` restent. La même politique de porte. Une oreille nouvelle, une bouche nouvelle et des voix nouvelles, quand la langue en a besoin.

Au démarrage, il dit la ligne suivante de la liste des bonjours, puis il se tait. Une attente du nuage dit la ligne suivante de l'autre liste. Les deux listes sont longues pour que la même blague ne revienne pas chaque matin.

## Ce qu'on peut dire

On appelle avec `bonjour grok` en français, ou `hola grok` et `¿estás ahí?` en espagnol, qui est la langue de départ. Hors conversation, les autres ordres commencent par `commande` (ou `comando`). Une phrase finie de plus de six mots est ignorée, sauf si c'est un vrai appel ou une chanson plus un titre (jusqu'à seize mots). Dans une conversation, il n'y a pas de limite de six mots. Une chanson peut se demander sans le mot `commande`. L'au revoir est local et immédiat. Pendant qu'une réponse se cherche, on entend une ligne courte d'une longue liste qui tourne, le micro fait une pause, puis on entend la réponse. Au démarrage, il dit la ligne suivante d'une autre liste, les bonjours, et ensuite il se tait. Pas de visite guidée. Pas de déversement de commandes. La fenêtre d'information a la liste, pour qui préfère lire plutôt que se faire faire un cours par un haut-parleur.

La barre des tâches est l'application. Le clic gauche ouvre la fenêtre d'information. Le clic droit ouvre le menu : pause, reconnaissance, voix, modèle, sessions, personnalité, langue, quitter. Fermer une fenêtre ne quitte pas. Quitter est une entrée du menu, parce que certains d'entre nous ont été mal entraînés par des années de « es-tu sûr de vouloir cacher la fenêtre et faire semblant que c'est une sortie ».

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

Les données, les sessions, le hash du mot de passe et le journal local de l'oreille vivent dans `%APPDATA%\GrokAssistant` sous Windows et dans `~/.config/grok-assistant` sous Linux. Les définitions d'agents s'écrivent dans `~/.grok/agents`, qui est le dossier du compte Grok, pas cette copie git. Ne pointe pas le dossier de travail de l'assistant vers un arbre de sources plein de projets. Il refuse déjà, et utilise son propre dossier de données, parce qu'une voix dans la cuisine ne devrait pas découvrir un soudain intérêt pour le refactoring.

La musique veut `yt-dlp` et `mpv` sur le PATH. Sans eux, l'assistant le dit, en une phrase, et ne fait pas semblant de fredonner.

## Ce que c'est

Une voix pour les heures où lire coûte et où la maison est silencieuse. La version portable est pour une personne âgée qui a déjà un petit ordinateur près d'elle. Le Raspberry Pi 4, de 4 Go, est le même assistant quand le portable devrait rester fermé. Le micro peut rester éveillé. Seule une phrase qui était destinée à l'assistant sort, et elle sort comme du texte.
