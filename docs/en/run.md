[← README.md](../../README.md)

# Run the executable

There is no traditional installer: `dist/GrokAssistant.exe` is the complete application. Copy it wherever you like and double-click it; Python does not need to be installed. The application opens a window with a live debug view showing what it heard and what happened next, while the Grok icon remains in the system tray. Closing the window simply hides it. To stop the application completely, use **Salir** in the window or tray menu.

If Grok Build is missing, or if you have never signed in, the program stops on a window before the tray. **Instalar Grok Build** runs the official installer:

```powershell
irm https://x.ai/cli/install.ps1 | iex
```

**Iniciar sesión** opens `grok login`, which uses the browser. **Comprobar** asks `grok models` whether the account is ready. **Continuar** starts the assistant anyway, so local orders still work while the cloud is absent. There is no API key to paste in.

To build that executable again from this folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```
