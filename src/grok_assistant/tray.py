"""Main window plus a Windows tray icon. Closing the window hides it. Quit is explicit."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from grok_assistant.helptext import SCREEN_HELP
from grok_assistant.hub import Hub, build
from grok_assistant.listen import Dictation, windows_spanish_available
from grok_assistant.music import Music
from grok_assistant.paths import bundle_root
from grok_assistant.speech import Speaker
from grok_assistant.win_tray import WinTray

BG = "#14181e"
PANEL = "#1c232c"
INK = "#e7eef2"
MUTED = "#8ea0ab"
AMBER = "#e8a030"
TEAL = "#8fd0c4"
FIELD = "#0e1216"
FONT = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 18, "bold")
MONO = ("Consolas", 12)


def shutdown_machine() -> None:
    if os.name == "nt":
        subprocess.Popen(["shutdown", "/s", "/t", "5"])
    else:
        subprocess.Popen(["systemctl", "poweroff"])


def run() -> None:
    if os.name == "nt":
        try:
            ctypes_shell = __import__("ctypes").windll.shell32
            ctypes_shell.SetCurrentProcessExplicitAppUserModelID("xai.GrokAssistant")
        except Exception:
            pass
    root = tk.Tk()
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
        self.debug_text = None
        self.help_text = None
        self.status_var = tk.StringVar(value="Arrancando")
        self.detail_var = tk.StringVar(value="")
        self.tray: WinTray | None = None
        self.tray_ok = False
        self.dictation: Dictation | None = None
        self.pause_file = hub.data_dir / "mic.pause"
        self._closing = False
        voices = self.speaker.list_voices() or ["Predeterminada"]
        recognizers = ["teclado"]
        if windows_spanish_available():
            recognizers.append("windows")
        self.hub.brain.set_devices(voices, recognizers)
        self._style()
        self._build_window()

    def start(self) -> None:
        threading.Thread(target=self._worker, daemon=True).start()
        self.jobs.put(("startup", ""))
        self._start_tray()
        self._sync_ear()
        self._note("ventana lista")
        self.root.after(200, self._pulse)

    def _style(self) -> None:
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BG, foreground=INK, font=FONT)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=INK, font=FONT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=BG, foreground=AMBER, font=FONT_BOLD)
        style.configure("TButton", background="#2a3340", foreground=INK, font=FONT, padding=(12, 6), borderwidth=0)
        style.map("TButton", background=[("active", "#3a4656")])
        style.configure("TEntry", fieldbackground=FIELD, foreground=INK, insertcolor=INK, font=FONT)

    def _build_window(self) -> None:
        self.root.title("Grok Assistant")
        self.root.geometry("860x680")
        self.root.minsize(640, 480)
        icon = bundle_root() / "docs" / "img" / "grok.ico"
        if icon.exists():
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass
        self.root.protocol("WM_DELETE_WINDOW", self._hide)

        head = ttk.Frame(self.root)
        head.pack(fill="x", padx=18, pady=(16, 4))
        ttk.Label(head, text="Grok Assistant", style="Status.TLabel").pack(side="left")
        ttk.Label(head, textvariable=self.status_var, font=FONT).pack(side="right")
        ttk.Label(self.root, textvariable=self.detail_var, style="Muted.TLabel").pack(anchor="w", padx=18)

        ttk.Label(self.root, text="Depuración — lo que oye y lo que hace después", style="Muted.TLabel").pack(anchor="w", padx=18, pady=(12, 4))
        log_wrap = tk.Frame(self.root, bg=PANEL, padx=1, pady=1)
        log_wrap.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.debug_text = tk.Text(
            log_wrap, height=18, wrap="word", bg=FIELD, fg=INK, insertbackground=INK,
            font=MONO, relief="flat", padx=12, pady=10, borderwidth=0,
        )
        self.debug_text.pack(fill="both", expand=True)
        self.debug_text.tag_configure("time", foreground="#667884")
        self.debug_text.tag_configure("oi", foreground=AMBER)
        self.debug_text.tag_configure("sigue", foreground=TEAL)
        self.debug_text.configure(state="disabled")

        ttk.Label(self.root, text="Ayuda — no es el registro", style="Muted.TLabel").pack(anchor="w", padx=18, pady=(4, 2))
        self.help_text = tk.Text(
            self.root, height=6, wrap="word", bg=PANEL, fg=MUTED, font=("Segoe UI", 10),
            relief="flat", padx=12, pady=8, borderwidth=0,
        )
        self.help_text.insert("end", SCREEN_HELP.strip())
        self.help_text.configure(state="disabled")
        self.help_text.pack(fill="x", padx=18, pady=(0, 8))

        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=18, pady=(0, 8))
        self.entry = ttk.Entry(bar)
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry.bind("<Return>", self._send)
        ttk.Button(bar, text="Enviar", command=self._send).pack(side="left", padx=(8, 0))

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", padx=18, pady=(0, 16))
        self.pause_button = ttk.Button(actions, text="Pausar escucha", command=self._toggle_from_ui)
        self.pause_button.pack(side="left")
        ttk.Button(actions, text="Limpiar registro", command=self._clear_view).pack(side="left", padx=8)
        ttk.Button(actions, text="Salir", command=lambda: self._quit(None, None)).pack(side="right")

    def _start_tray(self) -> None:
        icon = str(bundle_root() / "docs" / "img" / "grok.ico")
        self.tray = WinTray(
            icon,
            on_show=lambda: self.ui.put(self._show_main),
            on_pause=lambda: self.ui.put(self._toggle_from_ui),
            on_quit=lambda: self.ui.put(lambda: self._quit(None, None)),
        )
        self.tray_ok = self.tray.start()
        if self.tray_ok:
            self._note("bandeja activa. Cerrar esta ventana la esconde; el icono de Grok se queda.")
        else:
            self._note(f"la bandeja no arrancó ({self.tray.error}). Esta ventana es el programa.")

    def _note(self, text: str) -> None:
        import time
        self.hub.brain.logs.append(f"{time.strftime('%H:%M:%S')}  sigue   {text}")

    def _hide(self) -> None:
        if self.tray_ok:
            self.root.withdraw()
            self._note("ventana escondida. El icono de la bandeja sigue.")
        else:
            self._note("sin bandeja no escondo la ventana. Salir cierra el programa.")

    def _show_main(self) -> None:
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except tk.TclError:
            pass

    def _worker(self) -> None:
        while True:
            kind, payload = self.jobs.get()
            if kind == "stop":
                break
            if kind == "startup":
                self.say(self.hub.startup())
                self._refresh()
                continue
            if kind == "tick":
                result = self.hub.tick(speaker=self.say)
                self._apply(result)
                self._refresh()
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
                self._refresh()

    def say(self, text: str) -> None:
        if not text:
            return
        self.music.hold_for_speech()
        try:
            voice = self._voice_name()
            ok = self.speaker.say(text, None if voice == "Predeterminada" else voice, self.hub.brain.settings.volume)
            if not ok:
                self._note(f"no pude decir: {text}")
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
                shutdown_machine()
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

    def _send(self, _event=None) -> None:
        text = self.entry.get().strip()
        self.entry.delete(0, "end")
        if text:
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
        self.root.after(400, self._pulse)

    def _refresh(self) -> None:
        self.ui.put(self._paint)

    def _paint(self) -> None:
        try:
            snap = self.hub.brain.snapshot()
        except tk.TclError:
            return
        self.status_var.set(snap["status"])
        self.detail_var.set(
            f"{snap['model']}  ·  {snap['effort']}  ·  {snap['voice']}  ·  {snap['recognizer']}  ·  {snap['session']}  ·  {snap['volume']}%"
        )
        if self.tray_ok and self.tray is not None:
            self.tray.set_tip(f"Grok Assistant — {snap['status']}")
        if self.debug_text is None:
            return
        shown = self.hub.brain.logs[self.view_from:]
        self.debug_text.configure(state="normal")
        self.debug_text.delete("1.0", "end")
        for line in shown:
            self._insert_log(line)
        self.debug_text.configure(state="disabled")
        self.debug_text.see("end")

    def _insert_log(self, line: str) -> None:
        parts = line.split("  ", 2)
        if len(parts) == 3 and parts[1].strip() in {"oí", "sigue"}:
            stamp, kind, rest = parts[0], parts[1].strip(), parts[2]
            self.debug_text.insert("end", stamp + "  ", "time")
            self.debug_text.insert("end", kind.ljust(6), "oi" if kind == "oí" else "sigue")
            self.debug_text.insert("end", rest.strip() + "\n")
            return
        self.debug_text.insert("end", line + "\n")

    def _clear_view(self) -> None:
        self.view_from = len(self.hub.brain.logs)
        self._paint()

    def _toggle_from_ui(self) -> None:
        self.user_paused = not self.user_paused
        self.hub.brain.set_paused(self.user_paused)
        self._sync_ear()
        self.pause_button.configure(text="Seguir escuchando" if self.user_paused else "Pausar escucha")
        self._note("escucha en pausa" if self.user_paused else "vuelvo a escuchar")
        self._paint()

    def _ask(self, title: str) -> str | None:
        event = threading.Event()
        box: dict[str, str | None] = {"value": None}

        def show() -> None:
            box["value"] = simpledialog.askstring(title, "Contraseña:", show="*", parent=self.root)
            event.set()

        self.ui.put(show)
        event.wait(timeout=180)
        return box["value"]

    def _quit(self, _icon, _item) -> None:
        self._closing = True
        self.jobs.put(("stop", ""))
        if self.dictation is not None:
            self.dictation.stop()
        self.music.stop()
        if self.tray is not None:
            self.tray.stop()
        self.root.after(0, self.root.destroy)
