[← README.FR.md](../../README.FR.md)

# Sessions et agents

Une session peut être vue comme le carnet local de la conversation. Elle reste sur cet ordinateur. La session partagée repart de zéro après 24 heures, tandis qu'une session nommée reste disponible jusqu'à sa suppression. Ces sessions locales sont indépendantes du compte Grok.

Un agent appartient à ton compte Grok et s'ouvre explicitement avec `commande ouvre l'agent …` (ou `comando abrir agente …` en espagnol). Le menu Agent montre les fichiers de ce PC (`~/.grok/agents`) et les agents que le compte connecté publie déjà. Il peut mémoriser des dates, des lieux et des listes, et rechercher des informations lorsque c'est nécessaire. Cette mémoire étant liée au compte, le même agent reste disponible sur un autre ordinateur où tu es connecté. En créer un enregistre un fichier sur ce PC et demande le mot de passe administrateur.

Dire au revoir (`merci`, `d'accord`) met fin à la conversation en cours, mais ne supprime pas la session. Fermer une session ramène à la session partagée. `commande ferme l'agent` quitte l'agent actif et revient à l'assistant standard, sans supprimer l'agent. Sa mémoire étant liée au compte, elle ne dépend pas du fait que cet ordinateur reste allumé. L'ouverture d'un agent reste toujours une action volontaire.
