"""Tray icon, information window, debug transcript. Closing a window does not quit."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from grok_assistant.hub import Hub, build
from grok_assistant.listen import Dictation, windows_spanish_available
from grok_assistant.music import Music
from grok_assistant.paths import bundle_root
from grok_assistant.speech import Speaker


def shutdown_machine() -> None:
    if os.name == "nt":
        subprocess.Popen(["shutdown", "/s", "/t", "5"])
    else:
        subprocess.Popen(["systemctl", "poweroff"])


def run() -> None:
    root = tk.Tk()
    root.title("Grok")
    root.withdraw()
    app = TrayApp(root, build())
    app.start()
    root.mainloop()


class TrayApp:
    def __init__(self, root: tk.Tk, hub: Hub):
        self.root = root
        self.hub = hub
        self.speaker = Speaker()
        self.music = Music()
        self.user_paused = False
        self.jobs: queue.Queue = queue.Queue()
        self.ui: queue.Queue = queue.Queue()
        self.view_from = 0
        self.info = None
        self.debug = None
        self.vars: dict[str, tk.StringVar] = {}
        self.debug_text = None
        self.icon = None
        self.dictation: Dictation | None = None
        self.pause_file = hub.data_dir / "mic.pause"
        self._closing = False
        voices = self.speaker.list_voices() or ["Predeterminada"]
        recognizers = ["teclado"]
        if windows_spanish_available():
            recognizers.append("windows")
        self.hub.brain.set_devices(voices, recognizers)

    def start(self) -> None:
        threading.Thread(target=self._worker, daemon=True).start()
        self.jobs.put(("startup", ""))
        self._build_tray()
        self.root.after(400, self._open_info)
        self.root.after(500, self._pulse)
        self._sync_ear()

    def _build_tray(self) -> None:
        try:
            import pystray
            from PIL import Image
        except ImportError:
            self._fallback_window()
            return
        image = self._tray_image()
        menu = pystray.Menu(
            pystray.MenuItem(lambda item: "Seguir escuchando" if self.user_paused else "Pausar escucha", self._toggle_pause),
            pystray.MenuItem("Información", self._show_info, default=True),
            pystray.MenuItem("Depuración", self._show_debug),
            pystray.MenuItem("Reconocedor", pystray.Menu(self._recognizer_menu)),
            pystray.MenuItem("Voz", pystray.Menu(self._voice_menu)),
            pystray.MenuItem("Modelo", pystray.Menu(self._model_menu)),
            pystray.MenuItem("Sesiones", pystray.Menu(self._session_menu)),
            pystray.MenuItem("Contraseña de administrador", self._set_password),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self._quit),
        )
        self.icon = pystray.Icon("grok-assistant", image, "Grok Assistant", menu)
        try:
            self.icon.run_detached()
        except Exception:
            self.icon = None
            self._fallback_window()

    def _tray_image(self):
        from PIL import Image, ImageDraw

        mark = bundle_root() / "docs" / "img" / "grok-mark.png"
        if mark.exists():
            image = Image.open(mark).convert("RGBA")
            return image.resize((64, 64), Image.Resampling.LANCZOS)
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), outline=(255, 255, 255, 255), width=6)
        draw.line((10, 54, 54, 10), fill=(255, 255, 255, 255), width=6)
        return image

    def _fallback_window(self) -> None:
        self.root.deiconify()
        self.root.title("Grok — sin bandeja")
        ttk.Button(self.root, text="Información", command=lambda: self._show_info(None, None)).pack(fill="x")
        ttk.Button(self.root, text="Depuración", command=lambda: self._show_debug(None, None)).pack(fill="x")
        ttk.Button(self.root, text="Pausar / seguir", command=lambda: self._toggle_pause(None, None)).pack(fill="x")
        ttk.Button(self.root, text="Salir", command=lambda: self._quit(None, None)).pack(fill="x")

    def _worker(self) -> None:
        while True:
            kind, payload = self.jobs.get()
            if kind == "stop":
                break
            if kind == "startup":
                self.say(self.hub.startup())
                continue
            if kind == "tick":
                result = self.hub.tick(speaker=self.say)
                self._apply(result)
                continue
            if kind == "phrase":
                self._hold_mic(True)
                try:
                    result = self.hub.run(payload, speaker=self.say)
                    self._apply(result)
                    if any(item[0] == "ask_password" for item in result.effects):
                        password = self._ask("Contraseña de administrador")
                        follow = self.hub.submit_password(password, speaker=self.say) if password else self.hub.cancel_password(speaker=self.say)
                        self._apply(follow)
                finally:
                    self._hold_mic(False)

    def say(self, text: str) -> None:
        if not text:
            return
        self.music.hold_for_speech()
        try:
            voice = self._voice_name()
            ok = self.speaker.say(text, None if voice == "Predeterminada" else voice, self.hub.brain.settings.volume)
            if not ok:
                self.hub.brain.logs.append(f"no pude decir: {text}")
        finally:
            self.music.release_after_speech()

    def _voice_name(self) -> str:
        voices = self.hub.brain.voices
        index = self.hub.brain.settings.voice_index
        if not voices:
            return ""
        return voices[min(index, len(voices) - 1)]

    def _apply(self, result) -> None:
        for effect in result.effects:
            kind = effect[0]
            if kind == "play":
                trouble = self.music.play(effect[1], self.hub.brain.settings.volume)
                if trouble:
                    self.say(trouble)
                self._hold_mic(True)
            elif kind == "pause_music":
                self.music.pause()
                self._hold_mic(False)
            elif kind == "resume_music":
                self.music.resume()
                self._hold_mic(True)
            elif kind == "stop_music":
                self.music.stop()
                self._hold_mic(False)
            elif kind == "shutdown":
                self._shutdown()
            elif kind == "recognizer":
                self._sync_ear()

    def _hold_mic(self, hold: bool) -> None:
        if self.dictation is not None:
            self.dictation.set_paused(hold or self.user_paused or self.music.loaded)

    def _sync_ear(self) -> None:
        want = self.hub.brain.settings.recognizer == "windows" and not self.user_paused
        if want and self.dictation is None:
            ear = Dictation(self._heard, self.pause_file)
            if ear.start():
                self.dictation = ear
        if not want and self.dictation is not None:
            self.dictation.stop()
            self.dictation = None

    def _heard(self, text: str) -> None:
        if self.user_paused or self.music.loaded:
            return
        self.jobs.put(("phrase", text))

    def _pulse(self) -> None:
        if self._closing:
            return
        while True:
            try:
                job = self.ui.get_nowait()
            except queue.Empty:
                break
            job()
        self.jobs.put(("tick", ""))
        self._paint()
        self.root.after(1000, self._pulse)

    def _refresh(self) -> None:
        self.ui.put(self._paint)

    def _paint(self) -> None:
        try:
            snap = self.hub.brain.snapshot()
        except tk.TclError:
            return
        if self.icon is not None:
            self.icon.title = f"Grok — {snap['status']}"
        for key, var in self.vars.items():
            value = snap.get(key, "")
            if key == "shared":
                value = "sí, la compartida" if snap["shared"] else "no, una con nombre"
            var.set(str(value))
        if self.debug_text is not None:
            shown = self.hub.brain.logs[self.view_from:]
            self.debug_text.configure(state="normal")
            self.debug_text.delete("1.0", "end")
            self.debug_text.insert("end", "\n".join(shown))
            self.debug_text.configure(state="disabled")
            self.debug_text.see("end")

    def _window(self, title: str) -> tk.Toplevel:
        window = tk.Toplevel(self.root)
        window.title(title)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)
        return window

    def _show_info(self, icon, item) -> None:
        self.ui.put(self._open_info)

    def _open_info(self) -> None:
        if self.info is None or not self.info.winfo_exists():
            self.info = self._window("Información")
            labels = [
                ("status", "Estado"),
                ("model", "Modelo"),
                ("effort", "Razonamiento"),
                ("voice", "Voz"),
                ("recognizer", "Reconocedor"),
                ("session", "Sesión"),
                ("shared", "Compartida"),
                ("volume", "Volumen"),
                ("agent", "Agente"),
                ("last_heard", "Último oído"),
                ("last_spoken", "Último dicho"),
            ]
            for key, label in labels:
                row = ttk.Frame(self.info)
                row.pack(fill="x", padx=8, pady=2)
                ttk.Label(row, text=label, width=16).pack(side="left")
                var = tk.StringVar()
                self.vars[key] = var
                ttk.Label(row, textvariable=var).pack(side="left")
            text = tk.Text(self.info, height=16, width=78, wrap="word")
            text.insert("end", self.hub.brain.snapshot()["help"])
            text.configure(state="disabled")
            text.pack(fill="both", expand=True, padx=8, pady=8)
        self.info.deiconify()
        self.info.lift()
        self._refresh()

    def _show_debug(self, icon, item) -> None:
        self.ui.put(self._open_debug)

    def _open_debug(self) -> None:
        if self.debug is None or not self.debug.winfo_exists():
            self.debug = self._window("Depuración")
            self.debug_text = tk.Text(self.debug, height=22, width=88, wrap="word")
            self.debug_text.pack(fill="both", expand=True)
            self.debug_text.configure(state="disabled")
            bar = ttk.Frame(self.debug)
            bar.pack(fill="x")
            entry = ttk.Entry(bar)
            entry.pack(side="left", fill="x", expand=True, padx=4, pady=4)

            def send(_event=None) -> None:
                text = entry.get().strip()
                entry.delete(0, "end")
                if text:
                    self.jobs.put(("phrase", text))

            entry.bind("<Return>", send)
            ttk.Button(bar, text="Decir", command=send).pack(side="left")
            ttk.Button(bar, text="Limpiar vista", command=self._clear_view).pack(side="left", padx=4)
        self.debug.deiconify()
        self.debug.lift()
        self._refresh()

    def _clear_view(self) -> None:
        self.view_from = len(self.hub.brain.logs)
        self._refresh()

    def _toggle_pause(self, icon, item) -> None:
        self.user_paused = not self.user_paused
        self.hub.brain.set_paused(self.user_paused)
        self._sync_ear()
        if self.icon is not None:
            self.icon.update_menu()
        self._refresh()

    def _recognizer_menu(self):
        import pystray

        def choose(name):
            def action(icon, item, picked=name):
                self.hub.brain.settings.recognizer = picked
                self.hub.brain.persist()
                self._sync_ear()
                self.icon.update_menu()
            return action

        return tuple(
            pystray.MenuItem(name, choose(name), radio=True, checked=lambda item, name=name: self.hub.brain.settings.recognizer == name)
            for name in self.hub.brain.recognizers
        )

    def _voice_menu(self):
        import pystray

        def choose(index):
            def action(icon, item, picked=index):
                self.hub.brain.settings.voice_index = picked
                self.hub.brain.persist()
                self.icon.update_menu()
            return action

        return tuple(
            pystray.MenuItem(
                f"{index + 1}. {name}",
                choose(index),
                radio=True,
                checked=lambda item, index=index: self.hub.brain.settings.voice_index == index,
            )
            for index, name in enumerate(self.hub.brain.voices)
        )

    def _model_menu(self):
        import pystray

        models = [self.hub.brain.settings.model]
        if self.hub.cli is not None:
            found = self.hub.cli.models()
            if found:
                models = found

        def choose(name):
            def action(icon, item, picked=name):
                self.hub.brain.settings.model = picked
                self.hub.brain.persist()
                self.icon.update_menu()
            return action

        items = [
            pystray.MenuItem(
                name,
                choose(name),
                radio=True,
                checked=lambda item, name=name: self.hub.brain.settings.model == name,
            )
            for name in models
        ]
        effort = "alto" if self.hub.brain.effort_now == "high" else "bajo"
        items.append(pystray.MenuItem(f"Razonamiento: {effort}", None, enabled=False))
        return tuple(items)

    def _session_menu(self):
        import pystray

        def choose(name):
            def action(icon, item, picked=name):
                self.hub.brain.sessions.open(picked)
                self.icon.update_menu()
                self._refresh()
            return action

        return tuple(
            pystray.MenuItem(name, choose(name), radio=True, checked=lambda item, name=name: self.hub.brain.sessions.active == name)
            for name in self.hub.brain.sessions.names()
        )

    def _set_password(self, icon, item) -> None:
        self.ui.put(self._password_dialog)

    def _password_dialog(self) -> None:
        first = simpledialog.askstring("Administrador", "Nueva contraseña:", show="*", parent=self.root)
        if not first:
            return
        second = simpledialog.askstring("Administrador", "Repite la contraseña:", show="*", parent=self.root)
        if first != second:
            messagebox.showinfo("Administrador", "No coinciden.", parent=self.root)
            return
        self.hub.brain.auth.set_password(first)

    def _ask(self, title: str) -> str | None:
        event = threading.Event()
        box: dict[str, str | None] = {"value": None}

        def show() -> None:
            box["value"] = simpledialog.askstring(title, "Contraseña:", show="*", parent=self.root)
            event.set()

        self.ui.put(show)
        event.wait(timeout=180)
        return box["value"]

    def _shutdown(self) -> None:
        shutdown_machine()

    def _quit(self, icon, item) -> None:
        self._closing = True
        self.jobs.put(("stop", ""))
        if self.dictation is not None:
            self.dictation.stop()
        self.music.stop()
        if self.icon is not None:
            self.icon.stop()
        self.ui.put(self.root.destroy)
