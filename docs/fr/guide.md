[← README.FR.md](../../README.FR.md)

# Mode d'emploi

Des étapes courtes pour ouvrir le programme, le préparer et lui parler. Chaque chapitre long reste sur sa page.

## Ouvrir

1. Double-clique sur `GrokAssistant.exe`. Il n'y a pas d'installateur, et Python n'est pas nécessaire.
2. Si une fenêtre Grok Build apparaît, clique **Instalar Grok Build**, puis **Iniciar sesión** dans le navigateur, puis **Comprobar**. **Continuar** ouvre l'assistant même si le nuage n'est pas prêt. Les ordres locaux marchent encore. Il n'y a pas de clé à coller.
3. La fenêtre s'ouvre. En haut à droite : **EN ATTENTE**. L'icône Grok reste dans la barre.
4. Clic gauche sur l'icône : la fenêtre. Clic droit : le menu.
5. Fermer la fenêtre la cache. **Quitter** ferme le programme.

## Régler

Une fois, dans cet ordre.

1. **Langue.** Choisis Español, Français, Deutsch ou English. Les menus et les réponses passent à cette langue.
2. **Moteur d'écoute (STT).** C'est le programme qui transforme la parole en texte. Choisis-en un dans le menu. S'il manque, ouvre **Voice market**, onglet **Moteur d'écoute (STT)**, et télécharge-le. On peut le choisir à 100 %.
3. **Voix.** Choisis une voix de la même langue. **Voice market**, onglet **Voix**, en propose d'autres. Seules les voix de la langue active apparaissent.
4. **Empreinte.** **Admin → Empreintes → Nouvelle empreinte…**. Dis les seize phrases une fois. Le programme garde le son, en fait une empreinte pour tous les moteurs, et note ce que chacun retrouve. Changer de moteur ne demande pas un nouvel enregistrement.
5. **Mot de passe.** Seulement pour créer des agents. **Admin → Mot de passe…**. Écris-le deux fois. Le programme garde un résumé, pas le mot de passe en clair.
6. **Démarrer avec Windows** reste éteint tant que tu ne l'actives pas dans **Admin**.

## Parler

1. Dis le nom d'appel. Au début c'est `hola grok`. En haut à droite, ça passe à **EN CONVERSATION**.
2. Parle. Une question va à Grok. Un ordre peut commencer par `commande`.
3. `merci` ou `d'accord` ramène à **EN ATTENTE**. La session n'est pas effacée.
4. Pour une chanson, dis le titre. La première fois, le lecteur se télécharge.
5. Le journal de la fenêtre montre ce qui a été entendu. En dessous, `LLM:` est la décision du modèle local et `Grok:` est la réponse.

Plus de détail : [Empreintes et oreilles](empreintes.md) · [Ce qu'on peut dire](dire.md) · [Lancer l'exécutable](lancer.md)
