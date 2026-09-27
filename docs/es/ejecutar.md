[← README.ES.md](../../README.ES.md)

# Ejecutar el programa

No hay un instalador tradicional: `dist/GrokAssistant.exe` contiene la aplicación completa. Puedes copiarlo donde quieras y abrirlo con doble clic; no hace falta tener Python instalado. Al arrancar aparece una ventana de depuración en vivo que muestra qué se ha oído y qué ocurre después, mientras el icono de Grok permanece en la bandeja del sistema. Cerrar la ventana solo la oculta. Para detener la aplicación por completo, usa **Salir** en la ventana o en el menú de la bandeja.

Si falta Grok Build, o si nunca se ha iniciado sesión, el programa se detiene en una ventana antes de la bandeja. **Instalar Grok Build** ejecuta el instalador oficial:

```powershell
irm https://x.ai/cli/install.ps1 | iex
```

**Iniciar sesión** abre `grok login`, que usa el navegador. **Comprobar** pregunta a `grok models` si la cuenta está lista. **Continuar** arranca el asistente de todos modos, para que las órdenes locales sigan funcionando mientras la nube no está. No hay una clave de API que pegar.

Para volver a construir ese ejecutable desde esta carpeta:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```
