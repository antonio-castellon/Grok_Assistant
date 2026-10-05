[← README.FR.md](../../README.FR.md)

# Astuces

## L'empreinte sépare les personnes

L'empreinte vocale est là pour que deux personnes dans la même pièce ne se mélangent pas dans une seule conversation. Une fois prête, le microphone suit une voix enregistrée. Une autre personne qui parle est laissée de côté, avant le modèle local et avant un ordre. **Écoute → Activer l'essai** montre les mots et n'en fait rien. La même ligne devient **Désactiver l'essai**. `salir` sort aussi. Le coin affiche ESSAI.

## Le microphone fait partie de l'empreinte

Un microphone faible ou sourd rend les mots et l'empreinte moins sûrs. L'empreinte est la voix telle que ce microphone l'a entendue. La même personne sur un autre microphone peut rester sous le seuil, même quand le texte à l'écran est le bon. Il vaut mieux enregistrer l'empreinte à nouveau sur le microphone que l'on va utiliser.

**Réglages → Microphone** change le microphone. S'il a déjà une empreinte, c'est celle-là qui sert. Un microphone qui n'a pas encore la sienne garde l'empreinte précédente, jusqu'à un enregistrement sur celui-là. **Par défaut** est le microphone de Windows.

## Comment une phrase se termine

Une phrase se ferme 1,2 seconde après le dernier mot nouveau, une fois qu'il y a eu au moins 0,4 seconde de voix. Un bruit plus court ne compte pas. Avec **D'abord bonjour**, un bonjour seul attend 2 secondes tant que la discussion est encore fermée, pour que la question puisse suivre. Les minutes de Simple ferment la discussion. Elles ne ferment pas la phrase. Le plus rapide est le nom et la question dans le même souffle : « Bonjour grok, quelle heure est-il ? ».

## Pendant qu'il répond

Le microphone reste ouvert pendant que l'assistant parle. L'empreinte écarte la voix de l'assistant. **Pause de l'écoute** et un enregistrement d'empreinte ferment bien le microphone. Pendant une chanson, seule une voix enregistrée est suivie. Si un autre programme tient déjà le microphone, celui-ci ne peut pas l'ouvrir. Choisis un autre microphone, ou ferme le programme qui le tient.

## Ce que disent les lignes de débogage

`LLM: comando o accion no detectada` veut dire que le petit modèle local n'a pas vu d'ordre. Le moteur d'écoute a bien entendu la phrase. Avec la discussion fermée, cette phrase reste sur l'ordinateur. Ouvre d'abord la discussion, ou mets la question dans le même souffle que le nom. **Effacer le journal** vide la fenêtre de débogage. Les phrases d'après reviennent. **Enregistrer une trace** range un zip de cette exécution. L'audio de la maison reste sur l'ordinateur. Grok reçoit le texte d'une question ou d'un ordre.
