[← README.FR.md](../../README.FR.md)

# Lancer l'exécutable

Il n'y a pas d'installateur. `dist/GrokAssistant.exe` est tout le programme. On le copie n'importe où et on l'ouvre d'un double clic. Python n'a pas à être installé pour ce fichier. Une fenêtre s'ouvre avec le journal en direct — ce qui a été entendu, et ce qui se passe ensuite — et l'icône Grok reste dans la barre. Fermer la fenêtre la cache. Quitter est le bouton, ou Salir dans le menu de la barre.

Si Grok Build manque, ou si on ne s'est jamais connecté, le programme s'arrête sur une fenêtre avant la barre. **Instalar Grok Build** lance l'installateur officiel :

```powershell
irm https://x.ai/cli/install.ps1 | iex
```

**Iniciar sesión** ouvre `grok login`, qui passe par le navigateur. **Comprobar** demande à `grok models` si le compte est prêt. **Continuar** démarre l'assistant quand même, pour que les ordres locaux marchent encore pendant que le nuage est absent. Il n'y a pas de clé d'API à coller.

Les limites d'usage sont dans À propos, onglet Licence. Le programme ne copie pas ce texte à côté de l'exécutable.

Pour reconstruire cet exécutable depuis ce dossier :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```
