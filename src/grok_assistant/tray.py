"""Main window plus a Windows tray icon. Closing the window hides it. Quit is explicit."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from grok_assistant.helptext import HELP_TOPICS
from grok_assistant.hub import Hub, build
from grok_assistant.listen import RECOGNIZER_LABELS, Dictation, discover_recognizers
from grok_assistant.marketplace import Offer, download, offers
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
        self.status_var = tk.StringVar(value="Arrancando")
        self.detail_var = tk.StringVar(value="")
        self.tray: WinTray | None = None
        self.tray_ok = False
        self.dictation: Dictation | None = None
        self.pause_file = hub.data_dir / "mic.pause"
        self._closing = False
        voices = self.speaker.list_voices() or ["Predeterminada"]
        self.models = [self.hub.brain.settings.model]
        self.hub.brain.set_devices(voices, discover_recognizers())
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
        self._build_menus()

    def _start_tray(self) -> None:
        icon = str(bundle_root() / "docs" / "img" / "grok.ico")
        self.tray = WinTray(
            icon,
            on_show=lambda: self.ui.put(self._show_main),
            on_command=lambda key: self.ui.put(lambda key=key: self._menu_action(key)),
            items=self._tray_items,
        )
        threading.Thread(target=self._refresh_models, daemon=True).start()
        self.tray_ok = self.tray.start()
        if self.tray_ok:
            self._note("bandeja activa. Cerrar esta ventana la esconde; el icono de Grok se queda.")
        else:
            self._note(f"la bandeja no arrancó ({self.tray.error}). Esta ventana es el programa.")

    def _menu_kw(self) -> dict:
        return {
            "tearoff": 0,
            "bg": PANEL,
            "fg": INK,
            "activebackground": "#3a4656",
            "activeforeground": INK,
            "font": ("Segoe UI", 11),
        }

    def _build_menus(self) -> None:
        kw = self._menu_kw()
        bar = tk.Menu(self.root, **kw)
        self.root.configure(menu=bar)
        self.menu_escucha = tk.Menu(bar, postcommand=self._fill_escucha, **kw)
        self.menu_ear = tk.Menu(self.menu_escucha, **kw)
        self.menu_voz = tk.Menu(bar, postcommand=self._fill_voz, **kw)
        self.menu_modelo = tk.Menu(bar, postcommand=self._fill_modelo, **kw)
        self.menu_sesion = tk.Menu(bar, postcommand=self._fill_sesion, **kw)
        self.menu_agente = tk.Menu(bar, postcommand=self._fill_agente, **kw)
        self.menu_musica = tk.Menu(bar, **kw)
        self.menu_admin = tk.Menu(bar, **kw)
        self.menu_about = tk.Menu(bar, **kw)
        self.menu_market = tk.Menu(bar, **kw)
        self.menu_market.add_command(label="Voces, oídos y modelo local…", command=self._open_market)
        bar.add_cascade(label="Escucha", menu=self.menu_escucha)
        bar.add_cascade(label="Voz", menu=self.menu_voz)
        bar.add_cascade(label="Modelo", menu=self.menu_modelo)
        bar.add_cascade(label="Sesión", menu=self.menu_sesion)
        bar.add_cascade(label="Agente", menu=self.menu_agente)
        bar.add_cascade(label="Música", menu=self.menu_musica)
        bar.add_cascade(label="Administrador", menu=self.menu_admin)
        bar.add_cascade(label="Mercado", menu=self.menu_market)
        bar.add_cascade(label="Acerca de + Ayuda", menu=self.menu_about)
        self.menu_about.add_command(label="Comandos…", command=self._open_help)
        self.menu_about.add_command(label="Acerca de…", command=self._open_about)
        self.menu_musica.add_command(label="Pausar", command=lambda: self._command("pausa musica"))
        self.menu_musica.add_command(label="Seguir", command=lambda: self._command("seguir musica"))
        self.menu_musica.add_command(label="Parar", command=lambda: self._command("para la musica"))
        self.menu_admin.add_command(label="Modo administrador", command=lambda: self._command("modo administrador"))
        self.menu_admin.add_command(label="Contraseña…", command=self._password_dialog)
        self.menu_admin.add_separator()
        self.menu_admin.add_command(label="Apagar el equipo…", command=self._confirm_shutdown)

    def _fill_escucha(self) -> None:
        menu = self.menu_escucha
        menu.delete(0, "end")
        menu.add_command(
            label="Seguir escuchando" if self.user_paused else "Pausar escucha",
            command=self._toggle_from_ui,
        )
        menu.add_separator()
        self.menu_ear.delete(0, "end")
        current = self.hub.brain.settings.recognizer
        present = set(self.hub.brain.recognizers)
        for name, label in RECOGNIZER_LABELS.items():
            if name in present:
                shown = ("✓  " if name == current else "") + label
                self.menu_ear.add_command(label=shown, command=lambda picked=name: self._command(f"reconocedor {picked}"))
            else:
                self.menu_ear.add_command(label=f"{label}  (no instalado)", state="disabled")
        menu.add_cascade(label="Reconocedor", menu=self.menu_ear)
        menu.add_separator()
        menu.add_command(label="Prueba", command=lambda: self._command("prueba"))
        menu.add_command(label="Identificar mi voz", command=lambda: self._command("identifica mi voz"))

    def _fill_voz(self) -> None:
        menu = self.menu_voz
        menu.delete(0, "end")
        current = self.hub.brain.settings.voice_index
        for index, name in enumerate(self.hub.brain.voices):
            mark = "✓  " if index == current else ""
            menu.add_command(label=f"{mark}{index + 1}. {name}", command=lambda number=index + 1: self._command(f"voz {number}"))
        menu.add_separator()
        menu.add_command(label="Subir volumen", command=lambda: self._command("subir volumen"))
        menu.add_command(label="Bajar volumen", command=lambda: self._command("bajar volumen"))

    def _fill_modelo(self) -> None:
        menu = self.menu_modelo
        menu.delete(0, "end")
        current = self.hub.brain.settings.model
        for name in self.models:
            mark = "✓  " if name == current else ""
            menu.add_command(label=mark + name, command=lambda picked=name: self._pick_model(picked))
        menu.add_separator()
        menu.add_command(label="Actualizar lista", command=self._refresh_models)
        effort = "alto" if self.hub.brain.effort_now == "high" else "bajo"
        menu.add_command(label=f"Razonamiento: {effort}", state="disabled")

    def _fill_sesion(self) -> None:
        menu = self.menu_sesion
        menu.delete(0, "end")
        active = self.hub.brain.sessions.active
        for name in self.hub.brain.sessions.names():
            mark = "✓  " if name == active else ""
            menu.add_command(label=mark + name, command=lambda picked=name: self._command(f"abrir sesion {picked}"))
        menu.add_separator()
        menu.add_command(label="Cerrar sesión", command=lambda: self._command("cerrar sesion"))
        menu.add_command(label="Nueva sesión…", command=self._new_session)
        menu.add_command(label="Borrar sesión…", command=self._delete_session)

    def _fill_agente(self) -> None:
        menu = self.menu_agente
        menu.delete(0, "end")
        active = self.hub.brain.agents.active or ""
        found = self.hub.brain.agents.list()
        if not found:
            menu.add_command(label="No hay agentes", state="disabled")
        for record in found:
            mark = "✓  " if record.name == active else ""
            menu.add_command(label=mark + record.name, command=lambda picked=record.name: self._command(f"abrir agente {picked}"))
        menu.add_separator()
        menu.add_command(label="Cerrar agente", command=lambda: self._command("cerrar agente"))
        menu.add_command(label="Crear agente…", command=self._new_agent)

    def _tray_items(self) -> list:
        brain = self.hub.brain
        ears = []
        present = set(brain.recognizers)
        for name, label in RECOGNIZER_LABELS.items():
            if name in present:
                ears.append(("cmd", label, f"ear:{name}", name == brain.settings.recognizer))
            else:
                ears.append(("cmd", f"{label} (no instalado)", "noop", False))
        voices = []
        for index, name in enumerate(brain.voices):
            voices.append(("cmd", f"{index + 1}. {name}", f"voice:{index + 1}", index == brain.settings.voice_index))
        models = [("cmd", name, f"model:{name}", name == brain.settings.model) for name in self.models]
        models.append(("sep",))
        models.append(("cmd", "Actualizar lista", "models-refresh", False))
        sessions = [("cmd", name, f"session:{name}", name == brain.sessions.active) for name in brain.sessions.names()]
        sessions += [("sep",), ("cmd", "Cerrar sesión", "session-close", False), ("cmd", "Nueva sesión…", "session-new", False)]
        agents = [("cmd", record.name, f"agent:{record.name}", record.name == (brain.agents.active or "")) for record in brain.agents.list()]
        if not agents:
            agents = [("cmd", "No hay agentes", "noop", False)]
        agents += [("sep",), ("cmd", "Cerrar agente", "agent-close", False), ("cmd", "Crear agente…", "agent-new", False)]
        return [
            ("cmd", "Mostrar", "show", False),
            ("cmd", "Seguir escuchando" if self.user_paused else "Pausar escucha", "pause", self.user_paused),
            ("sub", "Reconocedor", ears),
            ("sub", "Voz", voices + [("sep",), ("cmd", "Subir volumen", "vol-up", False), ("cmd", "Bajar volumen", "vol-down", False)]),
            ("sub", "Modelo", models),
            ("sub", "Sesión", sessions),
            ("sub", "Agente", agents),
            ("sub", "Música", [
                ("cmd", "Pausar", "music-pause", False),
                ("cmd", "Seguir", "music-resume", False),
                ("cmd", "Parar", "music-stop", False),
            ]),
            ("cmd", "Mercado…", "market", False),
            ("sub", "Acerca de + Ayuda", [
                ("cmd", "Comandos…", "help", False),
                ("cmd", "Acerca de…", "about", False),
            ]),
            ("sep",),
            ("cmd", "Salir", "quit", False),
        ]

    def _menu_action(self, key: str) -> None:
        if key == "show":
            self._show_main()
        elif key == "pause":
            self._toggle_from_ui()
        elif key == "quit":
            self._quit(None, None)
        elif key == "noop":
            return
        elif key.startswith("voice:"):
            self._command(f"voz {key.split(':', 1)[1]}")
        elif key.startswith("ear:"):
            self._command(f"reconocedor {key.split(':', 1)[1]}")
        elif key.startswith("model:"):
            self._pick_model(key.split(":", 1)[1])
        elif key == "models-refresh":
            self._refresh_models()
        elif key.startswith("session:"):
            self._command(f"abrir sesion {key.split(':', 1)[1]}")
        elif key == "session-close":
            self._command("cerrar sesion")
        elif key == "session-new":
            self._new_session()
        elif key.startswith("agent:"):
            self._command(f"abrir agente {key.split(':', 1)[1]}")
        elif key == "agent-close":
            self._command("cerrar agente")
        elif key == "agent-new":
            self._new_agent()
        elif key == "vol-up":
            self._command("subir volumen")
        elif key == "vol-down":
            self._command("bajar volumen")
        elif key == "music-pause":
            self._command("pausa musica")
        elif key == "music-resume":
            self._command("seguir musica")
        elif key == "music-stop":
            self._command("para la musica")
        elif key == "market":
            self._open_market()
        elif key == "help":
            self._open_help()
        elif key == "about":
            self._open_about()

    def _command(self, words: str) -> None:
        self.jobs.put(("phrase", f"comando {words}"))

    def _pick_model(self, name: str) -> None:
        self.hub.brain.settings.model = name
        self.hub.brain.persist()
        self._note(f"modelo {name}. La próxima pregunta lo usa.")
        self._paint()

    def _refresh_models(self) -> None:
        if self.hub.cli is None:
            self._note("no hay Grok Build, así que no puedo listar modelos.")
            return
        found = self.hub.cli.models()
        if found:
            self.models = found
            self._note("modelos: " + ", ".join(found))
        else:
            self._note("no pude leer la lista de modelos.")
        self._refresh()

    def _new_session(self) -> None:
        name = simpledialog.askstring("Sesión", "Nombre de la sesión:", parent=self.root)
        if name and name.strip():
            self._command(f"crear sesion {name.strip()}")

    def _delete_session(self) -> None:
        name = simpledialog.askstring("Sesión", "Nombre de la sesión a borrar:", parent=self.root)
        if name and name.strip():
            self._command(f"borrar sesion {name.strip()}")

    def _new_agent(self) -> None:
        name = simpledialog.askstring("Agente", "Nombre del agente:", parent=self.root)
        if name and name.strip():
            self._command(f"crear agente {name.strip()}")

    def _open_market(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Mercado")
        window.configure(bg=BG)
        window.geometry("760x640")
        ttk.Label(window, text="Mercado", style="Status.TLabel").pack(anchor="w", padx=16, pady=(14, 2))
        ttk.Label(
            window,
            text="Elige qué se descarga a este equipo y qué queda en uso. Nada baja solo.",
            style="Muted.TLabel",
        ).pack(anchor="w", padx=16, pady=(0, 8))
        canvas = tk.Canvas(window, bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        status = tk.StringVar(value="")
        ttk.Label(window, textvariable=status, style="Muted.TLabel").pack(anchor="w", padx=16, pady=(0, 10))
        headings = {"voice": "Voces", "stt": "Reconocimiento", "llm": "Modelo local"}
        last = ""
        for offer in offers():
            if offer.kind != last:
                ttk.Label(inner, text=headings[offer.kind], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=8, pady=(12, 4))
                last = offer.kind
            self._market_row(inner, offer, status)

    def _market_row(self, parent, offer: Offer, status: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=8, pady=4)
        ready = offer.ready()
        state = "en este equipo" if ready else "sin descargar"
        ttk.Label(row, text=f"{offer.title}   {offer.size}   {state}", font=("Segoe UI", 11)).pack(anchor="w")
        ttk.Label(row, text=offer.detail, style="Muted.TLabel").pack(anchor="w")
        buttons = ttk.Frame(row)
        buttons.pack(anchor="w", pady=(2, 0))
        if not ready:
            ttk.Button(buttons, text="Descargar", command=lambda item=offer: self._download_offer(item, status)).pack(side="left")
        else:
            ttk.Button(buttons, text="Usar", command=lambda item=offer: self._use_offer(item)).pack(side="left")

    def _download_offer(self, offer: Offer, status: tk.StringVar) -> None:
        def work() -> None:
            try:
                download(offer, lambda message: self.ui.put(lambda message=message: status.set(message)))
                self.ui.put(lambda: status.set(f"{offer.title} listo"))
                self.ui.put(self._refresh_devices)
            except Exception as exc:
                self.ui.put(lambda: status.set(str(exc)[:180]))

        status.set(f"descargando {offer.title}…")
        threading.Thread(target=work, daemon=True).start()

    def _refresh_devices(self) -> None:
        self.hub.brain.set_devices(self.speaker.list_voices(), discover_recognizers())
        self._note("lista de voces y oídos actualizada")
        self._paint()

    def _use_offer(self, offer: Offer) -> None:
        self._refresh_devices()
        if offer.kind == "voice":
            try:
                index = self.hub.brain.voices.index(offer.use_label)
            except ValueError:
                self._note(f"la voz {offer.title} está en disco, pero no entra en la lista")
                return
            self.hub.brain.settings.voice_index = index
            self.hub.brain.persist()
            self._note(f"uso la voz {offer.use_label}")
        elif offer.kind == "stt":
            if offer.engine_id not in self.hub.brain.recognizers:
                self.hub.brain.recognizers.append(offer.engine_id)
            self.hub.brain.settings.recognizer = offer.engine_id
            self.hub.brain.persist()
            self._sync_ear()
            self._note(f"oído activo: {offer.title}")
        elif offer.kind == "llm":
            self.hub.brain.settings.local_llm = True
            self.hub.brain.persist()
            self._note("el modelo local revisa la frase antes de la nube")
        self._paint()

    def _password_dialog(self) -> None:
        first = simpledialog.askstring("Administrador", "Nueva contraseña:", show="*", parent=self.root)
        if not first:
            return
        second = simpledialog.askstring("Administrador", "Repite la contraseña:", show="*", parent=self.root)
        if first != second:
            messagebox.showinfo("Administrador", "No coinciden.", parent=self.root)
            return
        self.hub.brain.auth.set_password(first)
        self._note("contraseña de administrador guardada. En el disco solo está el hash.")
        self._paint()

    def _open_help(self) -> None:
        self._open_text(
            "Comandos",
            "Cada orden de abajo se puede decir. Casi todas empiezan por comando. "
            "El ejemplo es una frase completa.\n\n"
            + "\n\n".join(
                f"{title}\n{body}\nEjemplo: {example}"
                for title, body, example in HELP_TOPICS
            ),
        )

    def _open_about(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Acerca de")
        window.configure(bg=BG)
        window.geometry("640x460")
        text = tk.Text(
            window, wrap="word", bg=FIELD, fg=INK, font=("Segoe UI", 12),
            relief="flat", padx=18, pady=16, insertbackground=INK,
        )
        text.pack(fill="both", expand=True)
        text.tag_configure("name", font=("Segoe UI", 16, "bold"), foreground=AMBER, spacing3=6)
        text.tag_configure("quiet", foreground=MUTED, spacing3=10)
        self._link_tag(text, "github", "https://github.com/antonio-castellon")
        self._link_tag(text, "site", "https://www.castellon.ch")
        text.insert("end", "Antonio Castellon\n", "name")
        text.insert("end", "Castellon.CH\n", "quiet")
        text.insert("end", "GitHub  ")
        text.insert("end", "antonio-castellon", "github")
        text.insert("end", "\nWeb  ")
        text.insert("end", "www.castellon.ch", "site")
        text.insert(
            "end",
            "\n\nGrok Assistant escucha en casa. El audio no sale. "
            "A Grok solo se le manda el texto de una pregunta o de una orden, y solo cuando las reglas lo permiten. "
            "Lo demás se queda en el cuaderno de este equipo.\n\n"
            "Esta ventana es el registro: lo que se oyó y lo que se hizo después. "
            "Cerrarla esconde el programa. El icono de Grok en la bandeja lo vuelve a abrir. Salir lo cierra.",
        )
        text.bind("<Key>", lambda _event: "break")
        window.protocol("WM_DELETE_WINDOW", window.destroy)

    def _link_tag(self, text: tk.Text, tag: str, url: str) -> None:
        text.tag_configure(tag, foreground=TEAL, underline=True)
        text.tag_bind(tag, "<Button-1>", lambda _event, url=url: webbrowser.open(url))
        text.tag_bind(tag, "<Enter>", lambda _event: text.configure(cursor="hand2"))
        text.tag_bind(tag, "<Leave>", lambda _event: text.configure(cursor="arrow"))

    def _open_text(self, title: str, body: str) -> None:
        window = tk.Toplevel(self.root)
        window.title(title)
        window.configure(bg=BG)
        window.geometry("720x560")
        text = tk.Text(
            window, wrap="word", bg=FIELD, fg=INK, font=("Segoe UI", 12),
            relief="flat", padx=18, pady=16, insertbackground=INK,
        )
        text.pack(fill="both", expand=True)
        text.tag_configure("title", font=("Segoe UI", 14, "bold"), foreground=AMBER, spacing1=14, spacing3=4)
        text.tag_configure("example", font=("Consolas", 12), foreground=TEAL, spacing3=8)
        if title == "Comandos":
            intro, _, rest = body.partition("\n\n")
            text.insert("end", intro + "\n")
            for block in rest.split("\n\n"):
                lines = block.split("\n")
                text.insert("end", lines[0] + "\n", "title")
                for line in lines[1:]:
                    tag = "example" if line.startswith("Ejemplo:") else ""
                    text.insert("end", line + "\n", tag)
        else:
            text.insert("end", body)
        text.configure(state="disabled")
        window.protocol("WM_DELETE_WINDOW", window.destroy)

    def _confirm_shutdown(self) -> None:
        if messagebox.askyesno("Apagar", "¿Apago el equipo?", parent=self.root):
            self._note("apago el equipo.")
            shutdown_machine()

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
