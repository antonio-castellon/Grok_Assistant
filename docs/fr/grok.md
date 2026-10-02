[← README.FR.md](../../README.FR.md)

# Pourquoi Grok, et pas une autre fenêtre de chat

Un chat classique peut générer du code, mais il faut encore que quelqu'un le place au bon endroit, l'exécute, le teste et en fasse une modification réellement utilisable.

Grok Build est déjà installé et connecté sur cet ordinateur : aucune clé d'API n'est à copier. En ouvrant ce dossier, il peut examiner l'assistant, le modifier, lancer les tests et laisser ici la version mise à jour. L'approche est proche de celle d'[OpenClaw](https://github.com/openclaw/openclaw) : les instructions vivent dans de simples fichiers, ce qui permet d'ajouter une nouvelle étape en la décrivant directement dans un fichier.

Une question ordinaire — sur la météo, par exemple — ne modifie jamais le programme. Les changements de code passent par un flux distinct, lancé volontairement.

## La même réponse, avec un autre moteur

Ce programme est un compagnon vocal. Le microphone, le nom pour le réveiller, l'empreinte et la voix qui répond vivent sur cet ordinateur. Le moteur de raisonnement ne reçoit que du texte, et seulement lorsque quelqu'un s'est adressé à l'assistant.

Le moteur branché aujourd'hui est Grok, parce que Grok Build est déjà installé et connecté sur cette machine. Claude, ChatGPT et Codex peuvent eux aussi répondre à une question dite à voix haute. Sur cette partie du travail, les différences sont petites. Cette version est une expérience avec Grok. Si elle tient, l'étape suivante sera le même assistant dirigé vers un autre moteur de raisonnement. Cette étape n'est pas dans cette version.

| | Grok Build | Claude Code | Codex | ChatGPT |
| --- | --- | --- | --- | --- |
| Appelé par cet assistant | Oui | Non | Non | Non |
| Session ouverte, sans clé dans le programme | Oui, avec `grok login` | Oui, dans le navigateur, ou avec une clé d'API | Oui, avec le compte ChatGPT, ou avec une clé d'API | Oui, dans l'application ChatGPT |
| Faits actuels venus du web | Oui. La recherche et la lecture de pages sont actives pour une question parlée | Oui | Oui. La recherche est active. Les pages en direct sont un réglage à part | Oui, dans ChatGPT |
| Poursuivre la même conversation | Oui | Oui | Oui | Oui, dans ChatGPT |
| Modifier les fichiers de ce PC | Seulement si un administrateur l'autorise. Le shell reste éteint | Oui. C'est le rôle de l'outil | Oui, dans un bac à sable | Non. C'est Codex qui modifie les fichiers |
| Voix, nom et empreinte | Fournis par cet assistant | Cet assistant devrait les fournir | Cet assistant devrait les fournir | La voix de ChatGPT est un autre produit |
| Où va l'audio | Il reste sur ce PC. Seul le texte sort | Cet outil n'entend pas la pièce | Cet outil n'entend pas la pièce | Le flux de sa voix part chez OpenAI |

Claude, dans ce tableau, est Claude Code, l'outil de terminal. Le chat de claude.ai est une autre fenêtre de conversation. ChatGPT est l'application de discussion et de voix. Codex est l'outil de terminal qui se connecte avec ce même compte. Gemini CLI et GitHub Copilot CLI sont dans le même groupe que Claude Code et Codex : on les ouvre exprès pour travailler le code. Ils ne sont pas la voix de la maison.
