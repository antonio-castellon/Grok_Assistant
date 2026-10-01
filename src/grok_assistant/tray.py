"""Main window plus a Windows tray icon. Closing the window hides it. Quit is explicit."""

from __future__ import annotations

import os
import queue
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from grok_assistant.helptext import help_topics
from grok_assistant.hub import Hub, build
from grok_assistant.kroko_ear import STREAMING_KINDS, KrokoEar
from grok_assistant.offline_ear import OFFLINE_KINDS, OfflineEar
from grok_assistant.listen import (
    RECOGNIZER_LABELS,
    Dictation,
    discover_recognizers,
    EAR_LANG,
    eligible_ears,
    highest_accuracy,
    install_windows_speech,
    preferred_recognizer,
    with_accuracy,
)
from grok_assistant.marketplace import Offer, download, offers, offers_for
from grok_assistant.music import Music
from grok_assistant.refine import Refiner, pick_transcript
from grok_assistant.voiceprint import VoicePrint
from grok_assistant.paths import bundle_root
from grok_assistant.speech import Speaker
from grok_assistant.win_tray import WinTray

BG = "#14181e"
PANEL = "#1c232c"
INK = "#e7eef2"
MUTED = "#8ea0ab"
AMBER = "#e8a030"
TEAL = "#8fd0c4"
GREEN = "#3ddc97"
FIELD = "#0e1216"
FONT = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 18, "bold")
MONO = ("Consolas", 12)


def _ui(key: str, fallback: str = "") -> str:
    from grok_assistant.i18n import text

    return text(key, fallback)


def _version_line() -> str:
    from grok_assistant import __version__

    return f"{__version__} · {_ui('about.channel', 'still a release candidate')}"


def _used(active: bool) -> str:
    if not active:
        return ""
    return "✓  "


def _agent_label(record) -> str:
    if getattr(record, "origin", "local") != "account":
        return record.name
    return f"{record.name} · {_ui('menu.agent_account', 'cuenta')}"


def run() -> None:
    if os.name == "nt":
        try:
            ctypes_shell = __import__("ctypes").windll.shell32
            ctypes_shell.SetCurrentProcessExplicitAppUserModelID("xai.GrokAssistant")
        except Exception:
            pass
        from grok_assistant.win_tray import install_white_submenu_arrows

        install_white_submenu_arrows()
    root = tk.Tk()
    app = TrayApp(root, build())
    app.start()
    root.mainloop()


_HEARS = {"es": "español", "fr": "francés", "en": "inglés", "de": "alemán"}


def _outside_clause(blocked: list[str], title, rated: dict[str, int]) -> str:
    """Why a higher score stayed off: that ear only hears one language."""
    groups: list[tuple[str, list[str]]] = []
    index: dict[str, int] = {}
    for ear in blocked:
        locked = EAR_LANG.get(ear, "")
        if locked not in index:
            index[locked] = len(groups)
            groups.append((locked, []))
        groups[index[locked]][1].append(ear)
    parts = []
    for locked, members in groups:
        names = ", ".join(with_accuracy(title(ear), rated[ear]) for ear in members)
        verb = "queda" if len(members) == 1 else "quedan"
        heard = _HEARS.get(locked, locked or "otro idioma")
        parts.append(f"{names} {verb} fuera: solo oye {heard}.")
    return " ".join(parts)


class TrayApp:
    def __init__(self, root: tk.Tk, hub: Hub):
        self.root = root
        self.hub = hub
        self.speaker = Speaker()
        self.music = Music()
        self.voiceprint = VoicePrint()
        self.refiner = Refiner()
        self._music_note = False
        self.user_paused = False
        self.jobs: queue.Queue = queue.Queue()
        self.ui: queue.Queue = queue.Queue()
        self.view_from = 0
        self._debug_cache: list[str] = []
        self.debug_text = None
        self.status_var = tk.StringVar(value=_ui("status.starting", "Arrancando"))
        self.detail_var = tk.StringVar(value="")
        self._usage_percent: int | None = None
        self._usage_known = False
        self.usage_var = tk.StringVar(value=_ui("window.account", "cuenta {n}%").replace("{n}", "…"))
        self.tray: WinTray | None = None
        self.tray_ok = False
        self.dictation: Dictation | None = None
        self.kroko: KrokoEar | None = None
        self.offline: OfflineEar | None = None
        self._ears_suspended = False
        self._take_box: queue.Queue = queue.Queue()
        self._take_open = False
        self._print_wait: queue.Queue = queue.Queue()
        self._print_win = None
        self._drop_take_audio = 0.0
        self._settled_seq = 0
        self._score_lock = threading.Lock()
        self._downloads: dict[str, dict] = {}
        self._download_rows: dict[str, dict] = {}
        self.pause_file = hub.data_dir / "mic.pause"
        self._closing = False
        voices = self.speaker.list_voices() or ["Predeterminada"]
        self.models = [self.hub.brain.settings.model]
        self.hub.brain.set_devices(voices, discover_recognizers())
        chosen = preferred_recognizer(self.hub.brain.settings.recognizer, self.hub.brain.recognizers)
        if chosen != self.hub.brain.settings.recognizer:
            self.hub.brain.settings.recognizer = chosen
            self.hub.brain.persist()
        self._choose_best_ear(False)
        self._style()
        self._build_window()

    def start(self) -> None:
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=self.hub.brain.agents.refresh_account, daemon=True).start()
        self.jobs.put(("startup", ""))
        self._start_tray()
        self._sync_ear()
        self._ensure_identifier()
        self._poll_usage()
        threading.Thread(target=self._arm_voiceprint, daemon=True).start()
        threading.Thread(target=self._arm_refiner, daemon=True).start()
        threading.Thread(target=self._score_pending, daemon=True).start()
        threading.Thread(target=self._warm_piper, daemon=True).start()
        self._note("ventana lista")
        self._announce_combined()
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
        style.configure("Compact.TButton", background="#2a3340", foreground=INK, font=("Segoe UI", 10), padding=(10, 2), borderwidth=0)
        style.map("Compact.TButton", background=[("active", "#3a4656")])
        style.configure("TEntry", fieldbackground=FIELD, foreground=INK, insertcolor=INK, font=FONT)
        style.configure("Market.TNotebook", background=BG, borderwidth=0)
        style.configure("Market.TNotebook.Tab", background=PANEL, foreground=INK, padding=(14, 8), font=("Segoe UI", 11))
        style.map("Market.TNotebook.Tab", background=[("selected", "#3a4656")], foreground=[("selected", INK)])
        style.configure(
            "Market.Horizontal.TProgressbar",
            troughcolor=FIELD,
            background=TEAL,
            bordercolor=FIELD,
            lightcolor=TEAL,
            darkcolor=TEAL,
        )

    def _build_window(self) -> None:
        self.root.title("Grok Assistant")
        self.root.geometry("980x760")
        self.root.minsize(720, 560)
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
        corner = tk.Frame(head, bg=BG)
        corner.pack(side="right")
        self.state_var = tk.StringVar(value=_ui("status.banner_wait", "ESPERA"))
        self.state_label = tk.Label(
            corner, textvariable=self.state_var, bg=BG, fg=TEAL, font=("Segoe UI", 26, "bold"),
        )
        self.state_label.pack(anchor="e")
        self.usage_label = tk.Label(corner, textvariable=self.usage_var, bg=BG, fg=MUTED, font=("Segoe UI", 12, "bold"))
        self.usage_label.pack(anchor="e")
        ttk.Label(self.root, textvariable=self.detail_var, style="Muted.TLabel").pack(anchor="w", padx=18)

        self.footer = tk.Frame(self.root, bg=PANEL, height=46)
        self.footer.pack(side="bottom", fill="x")
        self.footer.pack_propagate(False)
        self.version_label = tk.Label(
            self.footer, text=_version_line(), bg=PANEL, fg=INK,
            font=("Segoe UI", 12), anchor="w",
        )
        self.version_label.pack(fill="both", padx=18)

        self.pages = ttk.Notebook(self.root, style="Market.TNotebook")
        self.pages.pack(fill="both", expand=True, padx=18, pady=(10, 12))
        self.page_simple = ttk.Frame(self.pages)
        self.page_debug = ttk.Frame(self.pages)
        self.page_flow = ttk.Frame(self.pages)
        self.pages.add(self.page_simple, text=_ui("window.tab_simple", "Simple"))
        self.pages.add(self.page_debug, text=_ui("window.tab_debug", "Depuración"))
        self.pages.add(self.page_flow, text=_ui("window.tab_flow", "Flujo"))
        self.pages.select(self.page_simple)

        simple = tk.Frame(self.page_simple, bg=BG)
        simple.pack(expand=True)
        row = tk.Frame(simple, bg=BG)
        row.pack()
        big = {
            "font": ("Segoe UI", 28, "bold"),
            "relief": "flat",
            "padx": 48,
            "pady": 28,
            "cursor": "hand2",
            "borderwidth": 0,
        }
        self.simple_pause = tk.Button(
            row, text=_ui("window.big_pause", "Pausar"), command=self._toggle_from_ui,
            bg="#1c3a36", fg=TEAL, activebackground="#24564e", activeforeground=TEAL, **big,
        )
        self.simple_pause.pack(side="left", padx=14)
        self.simple_quit = tk.Button(
            row, text=_ui("window.big_quit", "Salir"), command=lambda: self._quit(None, None),
            bg="#3a2a22", fg=AMBER, activebackground="#5a4030", activeforeground=AMBER, **big,
        )
        self.simple_quit.pack(side="left", padx=14)

        self.debug_label = ttk.Label(self.page_debug, text=_ui("window.debug", "Depuración — lo que oye y lo que hace después"), style="Muted.TLabel")
        self.debug_label.pack(anchor="w", padx=12, pady=(12, 4))
        log_wrap = tk.Frame(self.page_debug, bg=PANEL, padx=1, pady=1)
        log_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.debug_text = tk.Text(
            log_wrap, height=18, wrap="word", bg=FIELD, fg=INK, insertbackground=INK,
            font=MONO, relief="flat", padx=12, pady=10, borderwidth=0,
        )
        self.debug_text.pack(fill="both", expand=True)
        self.debug_text.tag_configure("time", foreground="#667884")
        self.debug_text.tag_configure("mode", foreground="#d7c4a3")
        self.debug_text.tag_configure("oi", foreground=AMBER)
        self.debug_text.tag_configure("sigue", foreground=TEAL)
        self.debug_text.configure(state="disabled")

        bar = ttk.Frame(self.page_debug)
        bar.pack(fill="x", padx=12, pady=(0, 8))
        self.entry = ttk.Entry(bar)
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry.bind("<Return>", self._send)
        self.send_button = ttk.Button(bar, text=_ui("window.send", "Enviar"), command=self._send)
        self.send_button.pack(side="left", padx=(8, 0))

        actions = ttk.Frame(self.page_debug)
        actions.pack(fill="x", padx=12, pady=(0, 12))
        self.pause_button = ttk.Button(actions, text=_ui("menu.pause", "Pausar escucha"), command=self._toggle_from_ui)
        self.pause_button.pack(side="left")
        self.clear_button = ttk.Button(actions, text=_ui("window.clear", "Limpiar registro"), command=self._clear_view)
        self.clear_button.pack(side="left", padx=8)
        self.quit_button = ttk.Button(actions, text=_ui("menu.quit", "Salir"), command=lambda: self._quit(None, None))
        self.quit_button.pack(side="right")

        self.flow = tk.Canvas(self.page_flow, bg=BG, highlightthickness=0)
        self.flow.pack(fill="both", expand=True)
        self._flow_snap = None
        self.flow.bind("<Configure>", lambda _event: self._draw_flow(None))
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
            "selectcolor": "#d7e2ea",
        }

    def _build_menus(self) -> None:
        kw = self._menu_kw()
        bar = tk.Menu(self.root, **kw)
        self.root.configure(menu=bar)
        self.menu_escucha = tk.Menu(bar, postcommand=self._fill_escucha, **kw)
        self.menu_ear = tk.Menu(self.menu_escucha, **kw)
        self.menu_identifier = tk.Menu(self.menu_escucha, postcommand=self._fill_identifiers, **kw)
        self.menu_voz = tk.Menu(bar, postcommand=self._fill_voz, **kw)
        self.menu_modelo = tk.Menu(bar, postcommand=self._fill_modelo, **kw)
        self.menu_sesion = tk.Menu(bar, postcommand=self._fill_sesion, **kw)
        self.menu_agente = tk.Menu(bar, postcommand=self._fill_agente, **kw)
        self.menu_persona = tk.Menu(bar, postcommand=self._fill_persona, **kw)
        self.menu_banter = tk.Menu(bar, **kw)
        self.menu_banter_kinds = tk.Menu(self.menu_banter, postcommand=self._fill_banter_kinds, **kw)
        self.menu_banter_themes = tk.Menu(self.menu_banter, postcommand=self._fill_banter_themes, **kw)
        self.menu_talk = tk.Menu(bar, **kw)
        self.menu_musica = tk.Menu(bar, **kw)
        self.menu_people = tk.Menu(bar, postcommand=self._fill_people, **kw)
        self.menu_prints = tk.Menu(self.menu_people, postcommand=self._fill_prints, **kw)
        self.menu_settings = tk.Menu(bar, postcommand=self._fill_settings, **kw)
        self.menu_language = tk.Menu(self.menu_settings, postcommand=self._fill_language, **kw)
        from grok_assistant.i18n import text

        bar.add_cascade(label=text("menu.listen", "Escucha"), menu=self.menu_escucha)
        bar.add_cascade(label=text("menu.voice", "Voz"), menu=self.menu_voz)
        bar.add_cascade(label=text("menu.talk", "Charla"), menu=self.menu_talk)
        bar.add_cascade(label=text("menu.music", "Música"), menu=self.menu_musica)
        bar.add_cascade(label=text("menu.people", "Personas"), menu=self.menu_people)
        bar.add_cascade(label=text("menu.settings", "Ajustes"), menu=self.menu_settings)
        bar.add_command(label=text("menu.about", "Acerca de"), command=self._open_about)
        self.menu_talk.add_cascade(label=text("menu.model", "Modelo"), menu=self.menu_modelo)
        self.menu_talk.add_cascade(label=text("menu.session", "Sesión"), menu=self.menu_sesion)
        self.menu_talk.add_cascade(label=text("menu.agent", "Agente"), menu=self.menu_agente)
        self.menu_banter.add_cascade(label=text("menu.banter_kinds", "Tipo"), menu=self.menu_banter_kinds)
        self.menu_banter.add_cascade(label=text("menu.banter_themes", "Tema"), menu=self.menu_banter_themes)
        self.menu_musica.add_command(label=_ui("menu.music_pause", "Pausar"), command=lambda: self._command("pausa musica"))
        self.menu_musica.add_command(label=_ui("menu.music_resume", "Seguir"), command=lambda: self._command("seguir musica"))
        self.menu_musica.add_command(label=_ui("menu.music_stop", "Parar"), command=lambda: self._command("para la musica"))

    def _fill_people(self) -> None:
        menu = self.menu_people
        menu.delete(0, "end")
        menu.add_command(label=_ui("menu.identify", "Identificar mi voz"), command=lambda: self._command("identifica mi voz"))
        menu.add_cascade(label=_ui("menu.prints", "Huellas"), menu=self.menu_prints)

    def _fill_settings(self) -> None:
        from grok_assistant.startup import enabled

        menu = self.menu_settings
        menu.delete(0, "end")
        menu.add_cascade(label=_ui("menu.language", "Idioma"), menu=self.menu_language)
        menu.add_command(label=_ui("menu.market", "Voice market"), command=self._open_market)
        menu.add_separator()
        if enabled():
            menu.add_command(label=_used(True) + _ui("menu.startup_off", "Desactivar arranque con Windows"), command=self._toggle_startup)
        else:
            menu.add_command(label=_ui("menu.startup_on", "Activar arranque con Windows"), command=self._toggle_startup)
        menu.add_separator()
        menu.add_command(label=_ui("menu.admin_mode", "Modo administrador"), command=lambda: self._command("modo administrador"))
        menu.add_command(label=_ui("menu.password", "Contraseña…"), command=self._password_dialog)

    def _choose_best_ear(self, sync: bool) -> None:
        """Pick the listener with the best hit rate across every print."""
        rated = self.hub.brain.speakers.combined_accuracies()
        current = self.hub.brain.settings.recognizer
        chosen = highest_accuracy(
            rated,
            eligible_ears(self.hub.brain.recognizers, self.hub.brain.settings.language),
            current,
        )
        if chosen == current or chosen not in self.hub.brain.recognizers:
            return
        self.hub.brain.settings.recognizer = chosen
        self.hub.brain.persist()
        if sync:
            self._sync_ear()

    def _announce_combined(self) -> None:
        rated = self.hub.brain.speakers.combined_accuracies()
        recognizers = self.hub.brain.recognizers
        eligible = set(eligible_ears(recognizers, self.hub.brain.settings.language))
        visible = [ear for ear in recognizers if ear != "teclado" and ear in rated]
        visible.sort(key=lambda ear: (-rated[ear], recognizers.index(ear)))
        current = self.hub.brain.settings.recognizer

        def title(ear: str) -> str:
            return _ui(f"ear.{ear}", RECOGNIZER_LABELS.get(ear, ear))

        current_label = title(current)
        if current in rated:
            current_label = with_accuracy(current_label, rated[current])
        if not visible:
            self._note(f"motor escucha: {current_label}. huellas combinadas: aún no hay porcentajes.")
            return
        joined = ", ".join(with_accuracy(title(ear), rated[ear]) for ear in visible)
        chosen_percent = rated.get(current, -1)
        blocked = [ear for ear in visible if ear not in eligible and rated[ear] > chosen_percent]
        line = f"motor escucha: {current_label}. huellas combinadas: {joined}."
        if blocked:
            line += " " + _outside_clause(blocked, title, rated)
        self._note(line)

    def _apply_best_ear(self) -> None:
        self._choose_best_ear(True)
        self._announce_combined()
        self._paint()

    def _listener_rows(self) -> list[tuple[str, str, bool]]:
        from grok_assistant.listen import RECOGNIZER_LABELS

        present = set(self.hub.brain.recognizers)
        rows = []
        for key, fallback in RECOGNIZER_LABELS.items():
            if key == "teclado":
                continue
            rows.append((key, _ui(f"ear.{key}", fallback), key in present))
        return rows

    def _listener_label(self, name: str, ear: str, title: str, installed: bool) -> str:
        book = self.hub.brain.speakers
        if not installed:
            return f"{title} · {_ui('menu.not_installed', '(no instalado)')}"
        score = book.score_of(name, ear)
        if score and score[1]:
            return with_accuracy(title, round(100 * score[0] / score[1]))
        if book.raw_clips(name):
            return f"{title} · {_ui('menu.unscored', 'sin valorar')}"
        if book.take_count(name):
            return f"{title} · {_ui('menu.no_audio', 'sin audio')}"
        return f"{title} · {_ui('menu.no_print', '(sin huella)')}"

    def _fill_prints(self) -> None:
        menu = self.menu_prints
        menu.delete(0, "end")
        book = self.hub.brain.speakers
        names = book.names()
        if not names:
            menu.add_command(label=_ui("menu.no_prints", "No hay huellas"), state="disabled")
        for name in names:
            child = tk.Menu(menu, **self._menu_kw())
            for ear, title, installed in self._listener_rows():
                label = self._listener_label(name, ear, title, installed)
                child.add_command(label=label, state="disabled")
            child.add_separator()
            child.add_command(label=_ui("menu.print_recapture", "Volver a grabar"), command=lambda picked=name: self._recapture_print(picked))
            child.add_command(label=_ui("menu.print_rename", "Renombrar…"), command=lambda picked=name: self._rename_print(picked))
            child.add_command(label=_ui("menu.print_delete", "Borrar"), command=lambda picked=name: self._delete_print(picked))
            label = _used(name == book.locked) + name
            takes = book.take_count(name)
            if takes:
                label += f"  ·  {takes} {_ui('menu.takes', 'tomas')}"
            else:
                label += "  " + _ui("menu.no_print", "(sin huella)")
            menu.add_cascade(label=label, menu=child)
        menu.add_separator()
        menu.add_command(label=_ui("menu.print_new", "Nueva huella…"), command=self._new_print)

    def _print_items(self) -> list:
        book = self.hub.brain.speakers
        rows = []
        names = book.names()
        if not names:
            rows.append(("cmd", _ui("menu.no_prints", "No hay huellas"), "noop", False))
        for name in names:
            children = []
            for ear, title, installed in self._listener_rows():
                label = self._listener_label(name, ear, title, installed)
                children.append(("cmd", label, "noop", False))
            children.append(("sep",))
            children.append(("cmd", _ui("menu.print_recapture", "Volver a grabar"), f"print-again:{name}", False))
            children.append(("cmd", _ui("menu.print_rename", "Renombrar…"), f"print-rename:{name}", False))
            children.append(("cmd", _ui("menu.print_delete", "Borrar"), f"print-delete:{name}", False))
            bare = _used(name == book.locked) + name
            takes = book.take_count(name)
            if takes:
                bare += f"  ·  {takes} {_ui('menu.takes', 'tomas')}"
            else:
                bare += "  " + _ui("menu.no_print", "(sin huella)")
            rows.append(("sub", bare, children))
        rows.append(("sep",))
        rows.append(("cmd", _ui("menu.print_new", "Nueva huella…"), "print-new", False))
        return rows

    def _new_print(self) -> None:
        name = simpledialog.askstring(
            _ui("dialog.print_name", "Huella"),
            _ui("dialog.print_new", "Nombre de la persona:"),
            parent=self.root,
        )
        if name and name.strip():
            self._recapture_print(name.strip())

    def _rename_assistant(self) -> None:
        current = self.hub.brain.settings.wake_name
        typed = simpledialog.askstring(
            _ui("dialog.wake_title", "Cambiar nombre"),
            _ui("dialog.wake_name", "Nombre del asistente. Una palabra en español se oye mejor:"),
            initialvalue=current,
            parent=self.root,
        )
        if not typed or not typed.strip() or typed.strip() == current:
            return
        self.jobs.put(("rename", typed.strip()))

    def _rename_print(self, name: str) -> None:
        new = simpledialog.askstring(
            _ui("dialog.print_name", "Huella"),
            _ui("dialog.print_rename", "Nuevo nombre:"),
            initialvalue=name,
            parent=self.root,
        )
        if not new or not new.strip():
            return
        stored = self.hub.brain.speakers.rename(name, new.strip())
        if stored:
            self._note(f"huella: {stored}")
        else:
            self._note("ese nombre ya está")

    def _recapture_print(self, name: str, ear: str | None = None) -> None:
        del ear
        self.jobs.put(("capture", name))

    def _rescore_print(self, name: str, ear: str) -> None:
        threading.Thread(target=self._score_named, args=(name, ear), daemon=True).start()

    def _delete_print(self, name: str) -> None:
        title = _ui("dialog.print_name", "Huella")
        if not messagebox.askyesno(title, _ui("dialog.print_delete", "¿Borro esta huella?"), parent=self.root):
            return
        if self.hub.brain.speakers.delete(name):
            self._note(f"huella borrada: {name}")

    def _toggle_startup(self) -> None:
        from grok_assistant.startup import enabled, set_enabled

        turn_on = not enabled()
        set_enabled(turn_on)
        if turn_on:
            self._note("el programa arrancará con Windows")
        else:
            self._note("el programa ya no arranca con Windows")

    def _fill_escucha(self) -> None:
        menu = self.menu_escucha
        menu.delete(0, "end")
        menu.add_command(
            label=_ui("menu.resume", "Seguir escuchando") if self.user_paused else _ui("menu.pause", "Pausar escucha"),
            command=self._toggle_from_ui,
        )
        menu.add_separator()
        self.menu_ear.delete(0, "end")
        current = self.hub.brain.settings.recognizer
        present = set(self.hub.brain.recognizers)
        for name, label in RECOGNIZER_LABELS.items():
            shown_name = _ui(f"ear.{name}", label)
            if name in present:
                self.menu_ear.add_command(
                    label=_used(name == current) + shown_name,
                    command=lambda picked=name: self._command(f"reconocedor {picked}"),
                )
            elif name == "windows":
                self.menu_ear.add_command(label=_ui("menu.install_windows", "Windows español… instalar"), command=self._install_windows)
            else:
                self.menu_ear.add_command(label=f"{shown_name}  {_ui('menu.not_installed', '(no instalado)')}", state="disabled")
        menu.add_cascade(label=_ui("menu.recognizer", "Reconocedor"), menu=self.menu_ear)
        menu.add_cascade(label=_ui("menu.identifier", "Identificador texto"), menu=self.menu_identifier)
        menu.add_separator()
        if self.hub.brain.test_mode:
            menu.add_command(label=_used(True) + _ui("menu.test_off", "Desactivar prueba"), command=self._toggle_test)
        else:
            menu.add_command(label=_ui("menu.test_on", "Activar prueba"), command=self._toggle_test)
        menu.add_command(label=_ui("menu.rename", "Cambiar nombre…"), command=self._rename_assistant)

    def _fill_identifiers(self) -> None:
        menu = self.menu_identifier
        menu.delete(0, "end")
        from grok_assistant.marketplace import offers

        current = self.hub.brain.settings.llm_file if self.hub.brain.settings.local_llm else ""
        menu.add_command(
            label=_used(not current) + _ui("menu.none", "Ninguno"),
            command=lambda: self._pick_identifier(None),
        )
        ready = [offer for offer in offers() if offer.kind == "llm" and offer.ready()]
        if not ready:
            menu.add_command(label=_ui("menu.none_downloaded", "(ninguno descargado)"), state="disabled")
            return
        for offer in ready:
            filename = offer.files[0][1].rsplit("/", 1)[-1]
            menu.add_command(label=_used(filename == current) + offer.title, command=lambda item=offer: self._pick_identifier(item))

    def _identifier_items(self) -> list:
        from grok_assistant.marketplace import offers

        current = self.hub.brain.settings.llm_file if self.hub.brain.settings.local_llm else ""
        rows = [("cmd", _ui("menu.none", "Ninguno"), "identifier-off", not current)]
        ready = [offer for offer in offers() if offer.kind == "llm" and offer.ready()]
        if not ready:
            rows.append(("cmd", _ui("menu.none_downloaded", "(ninguno descargado)"), "noop", False))
            return rows
        for offer in ready:
            filename = offer.files[0][1].rsplit("/", 1)[-1]
            rows.append(("cmd", offer.title, f"identifier:{filename}", filename == current))
        return rows

    def _pick_identifier_file(self, filename: str) -> None:
        from grok_assistant.marketplace import offers

        for offer in offers():
            if offer.kind == "llm" and offer.files and offer.files[0][1].rsplit("/", 1)[-1] == filename:
                self._pick_identifier(offer)
                return

    def _ensure_identifier(self) -> None:
        if not self.hub.brain.settings.local_llm or self.hub.brain.settings.llm_file:
            return
        from grok_assistant.marketplace import offers

        ready = [offer for offer in offers() if offer.kind == "llm" and offer.ready()]
        if ready:
            self._pick_identifier(ready[0])

    def _pick_identifier(self, offer: Offer | None) -> None:
        if offer is None:
            self.hub.brain.settings.local_llm = False
            self.hub.brain.settings.llm_file = ""
            self.hub.brain.persist()
            self._note("sin identificador de texto")
            self._paint()
            return
        filename = offer.files[0][1].rsplit("/", 1)[-1]
        self.hub.brain.settings.local_llm = True
        self.hub.brain.settings.llm_file = filename
        self.hub.brain.persist()
        if self.hub.mind is not None:
            self.hub.mind.select(filename)
        self._note(f"identificador de texto: {offer.title}")
        self._paint()

    def _fill_voz(self) -> None:
        menu = self.menu_voz
        menu.delete(0, "end")
        current = self.hub.brain.settings.voice_index
        for index, name in enumerate(self.hub.brain.voices):
            menu.add_command(label=f"{_used(index == current)}{index + 1}. {name}", command=lambda number=index + 1: self._command(f"voz {number}"))
        menu.add_separator()
        menu.add_command(label=_ui("menu.volume_up", "Subir volumen"), command=lambda: self._command("subir volumen"))
        menu.add_command(label=_ui("menu.volume_down", "Bajar volumen"), command=lambda: self._command("bajar volumen"))
        menu.add_separator()
        menu.add_cascade(label=_ui("menu.personality", "Personalidad"), menu=self.menu_persona)
        menu.add_cascade(label=_ui("menu.banter", "Saludos"), menu=self.menu_banter)

    def _fill_modelo(self) -> None:
        menu = self.menu_modelo
        menu.delete(0, "end")
        current = self.hub.brain.settings.model
        for name in self.models:
            menu.add_command(label=_used(name == current) + name, command=lambda picked=name: self._pick_model(picked))
        menu.add_separator()
        menu.add_command(label=_ui("menu.refresh_models", "Actualizar lista"), command=self._refresh_models)
        effort = _ui("menu.effort_high", "Razonamiento: alto") if self.hub.brain.effort_now == "high" else _ui("menu.effort_low", "Razonamiento: bajo")
        menu.add_command(label=effort, state="disabled")

    def _fill_sesion(self) -> None:
        menu = self.menu_sesion
        menu.delete(0, "end")
        active = self.hub.brain.sessions.active
        for name in self.hub.brain.sessions.names():
            menu.add_command(label=_used(name == active) + name, command=lambda picked=name: self._command(f"abrir sesion {picked}"))
        menu.add_separator()
        menu.add_command(label=_ui("menu.close_session", "Cerrar sesión"), command=lambda: self._command("cerrar sesion"))
        menu.add_command(label=_ui("menu.new_session", "Nueva sesión…"), command=self._new_session)
        menu.add_command(label=_ui("menu.delete_session", "Borrar sesión…"), command=self._delete_session)

    def _fill_agente(self) -> None:
        menu = self.menu_agente
        menu.delete(0, "end")
        active = self.hub.brain.agents.active or ""
        found = self.hub.brain.agents.list()
        if not found:
            menu.add_command(label=_ui("menu.no_agents", "No hay agentes"), state="disabled")
        for record in found:
            menu.add_command(
                label=_used(record.name == active) + _agent_label(record),
                command=lambda picked=record.name: self._command(f"abrir agente {picked}"),
            )
        menu.add_separator()
        menu.add_command(label=_ui("menu.close_agent", "Cerrar agente"), command=lambda: self._command("cerrar agente"))
        menu.add_command(label=_ui("menu.new_agent", "Crear agente…"), command=self._new_agent)

    def _tray_items(self) -> list:
        from grok_assistant.i18n import text

        brain = self.hub.brain
        ears = []
        present = set(brain.recognizers)
        for name, label in RECOGNIZER_LABELS.items():
            shown = _ui(f"ear.{name}", label)
            if name in present:
                ears.append(("cmd", shown, f"ear:{name}", name == brain.settings.recognizer))
            elif name == "windows":
                ears.append(("cmd", _ui("menu.install_windows", "Windows español… instalar"), "install-windows", False))
            else:
                ears.append(("cmd", f"{shown}  {_ui('menu.not_installed', '(no instalado)')}", "noop", False))
        voices = []
        for index, name in enumerate(brain.voices):
            voices.append(("cmd", f"{index + 1}. {name}", f"voice:{index + 1}", index == brain.settings.voice_index))
        models = [("cmd", name, f"model:{name}", name == brain.settings.model) for name in self.models]
        models.append(("sep",))
        models.append(("cmd", _ui("menu.refresh_models", "Actualizar lista"), "models-refresh", False))
        sessions = [
            ("cmd", name, f"session:{name}", name == brain.sessions.active)
            for name in brain.sessions.names()
        ]
        sessions += [
            ("sep",),
            ("cmd", _ui("menu.close_session", "Cerrar sesión"), "session-close", False),
            ("cmd", _ui("menu.new_session", "Nueva sesión…"), "session-new", False),
            ("cmd", _ui("menu.delete_session", "Borrar sesión…"), "session-delete", False),
        ]
        active_agent = brain.agents.active or ""
        agents = [
            ("cmd", _agent_label(record), f"agent:{record.name}", record.name == active_agent)
            for record in brain.agents.list()
        ]
        if not agents:
            agents = [("cmd", _ui("menu.no_agents", "No hay agentes"), "noop", False)]
        agents += [
            ("sep",),
            ("cmd", _ui("menu.close_agent", "Cerrar agente"), "agent-close", False),
            ("cmd", _ui("menu.new_agent", "Crear agente…"), "agent-new", False),
        ]
        effort = _ui("menu.effort_high", "Razonamiento: alto") if brain.effort_now == "high" else _ui("menu.effort_low", "Razonamiento: bajo")
        models.append(("cmd", effort, "noop", False))
        return [
            ("cmd", text("menu.show", "Mostrar"), "show", False),
            ("cmd", text("menu.resume", "Seguir escuchando") if self.user_paused else text("menu.pause", "Pausar escucha"), "pause", self.user_paused),
            ("sub", text("menu.listen", "Escucha"), [
                ("sub", text("menu.recognizer", "Reconocedor"), ears),
                ("sub", text("menu.identifier", "Identificador texto"), self._identifier_items()),
                ("sep",),
                ("cmd", _ui("menu.test_off", "Desactivar prueba") if brain.test_mode else _ui("menu.test_on", "Activar prueba"), "test-toggle", brain.test_mode),
                ("cmd", _ui("menu.rename", "Cambiar nombre…"), "rename", False),
            ]),
            ("sub", text("menu.voice", "Voz"), voices + [
                ("sep",),
                ("cmd", _ui("menu.volume_up", "Subir volumen"), "vol-up", False),
                ("cmd", _ui("menu.volume_down", "Bajar volumen"), "vol-down", False),
                ("sep",),
                ("sub", text("menu.personality", "Personalidad"), self._persona_items()),
                ("sub", text("menu.banter", "Saludos"), [
                    ("sub", text("menu.banter_kinds", "Tipo"), self._banter_kind_rows()),
                    ("sub", text("menu.banter_themes", "Tema"), self._banter_theme_rows()),
                ]),
            ]),
            ("sub", text("menu.talk", "Charla"), [
                ("sub", text("menu.model", "Modelo"), models),
                ("sub", text("menu.session", "Sesión"), sessions),
                ("sub", text("menu.agent", "Agente"), agents),
            ]),
            ("sub", text("menu.music", "Música"), [
                ("cmd", _ui("menu.music_pause", "Pausar"), "music-pause", False),
                ("cmd", _ui("menu.music_resume", "Seguir"), "music-resume", False),
                ("cmd", _ui("menu.music_stop", "Parar"), "music-stop", False),
            ]),
            ("sub", text("menu.people", "Personas"), [
                ("cmd", _ui("menu.identify", "Identificar mi voz"), "identify", False),
                ("sub", text("menu.prints", "Huellas"), self._print_items()),
            ]),
            ("sub", text("menu.settings", "Ajustes"), [
                ("sub", text("menu.language", "Idioma"), self._language_items()),
                ("cmd", text("menu.market", "Voice market"), "market", False),
                ("sep",),
                ("cmd", _ui("menu.startup_off", "Desactivar arranque con Windows") if self._startup_on() else _ui("menu.startup_on", "Activar arranque con Windows"), "startup", self._startup_on()),
                ("sep",),
                ("cmd", _ui("menu.admin_mode", "Modo administrador"), "admin", False),
                ("cmd", _ui("menu.password", "Contraseña…"), "password", False),
            ]),
            ("cmd", text("menu.about", "Acerca de"), "about", False),
            ("sep",),
            ("cmd", text("menu.quit", "Salir"), "quit", False),
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
        elif key == "test-toggle":
            self._toggle_test()
        elif key == "rename":
            self._rename_assistant()
        elif key == "identify":
            self._command("identifica mi voz")
        elif key == "admin":
            self._command("modo administrador")
        elif key == "password":
            self._password_dialog()
        elif key == "print-new":
            self._new_print()
        elif key.startswith("print-rename:"):
            self._rename_print(key.split(":", 1)[1])
        elif key.startswith("print-score:"):
            _tag, person, heard = key.split(":", 2)
            self._rescore_print(person, heard)
        elif key.startswith("print-again:"):
            self._recapture_print(key.split(":", 1)[1])
        elif key.startswith("print-delete:"):
            self._delete_print(key.split(":", 1)[1])
        elif key == "install-windows":
            self._install_windows()
        elif key == "identifier-off":
            self._pick_identifier(None)
        elif key.startswith("identifier:"):
            self._pick_identifier_file(key.split(":", 1)[1])
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
        elif key == "session-delete":
            self._delete_session()
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
        elif key == "startup":
            self._toggle_startup()
        elif key.startswith("lang:"):
            self._set_language(key.split(":", 1)[1])
        elif key == "edit-commands":
            self._edit_commands()
        elif key == "edit-help":
            self._edit_help()
        elif key.startswith("persona:"):
            self._choose_person(key.split(":", 1)[1])
        elif key == "persona-edit":
            self._open_personality()
        elif key.startswith("banter-"):
            self._banter_set(key)
        elif key == "market":
            self._open_market()
        elif key == "help":
            self._open_about()
        elif key == "about":
            self._open_about()

    def _startup_on(self) -> bool:
        from grok_assistant.startup import enabled

        return enabled()

    def _toggle_test(self) -> None:
        self._command("salir" if self.hub.brain.test_mode else "prueba")

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
        name = simpledialog.askstring(_ui("dialog.session", "Sesión"), _ui("dialog.session_name", "Nombre de la sesión:"), parent=self.root)
        if name and name.strip():
            self._command(f"crear sesion {name.strip()}")

    def _delete_session(self) -> None:
        name = simpledialog.askstring(_ui("dialog.session", "Sesión"), _ui("dialog.session_delete", "Nombre de la sesión a borrar:"), parent=self.root)
        if name and name.strip():
            self._command(f"borrar sesion {name.strip()}")

    def _new_agent(self) -> None:
        name = simpledialog.askstring(_ui("dialog.agent", "Agente"), _ui("dialog.agent_name", "Nombre del agente:"), parent=self.root)
        if name and name.strip():
            self._command(f"crear agente {name.strip()}")

    def _fill_persona(self) -> None:
        from grok_assistant.personality import persons

        menu = self.menu_persona
        menu.delete(0, "end")
        current = str(self.hub.brain.settings.personality.get("profile") or "")
        menu.add_command(
            label=_used(not current) + _ui("persona.none", "Sin persona — la voz de siempre"),
            command=lambda: self._choose_person(""),
        )
        menu.add_separator()
        for person in persons():
            menu.add_command(
                label=_used(person.id == current) + f"{person.name} — {person.label}",
                command=lambda picked=person.id: self._choose_person(picked),
            )
        menu.add_separator()
        menu.add_command(label=_ui("persona.adjust", "Ajustar rasgos y comportamiento…"), command=self._open_personality)

    def _fill_language(self) -> None:
        from grok_assistant.i18n import languages, text

        menu = self.menu_language
        menu.delete(0, "end")
        current = self.hub.brain.settings.language
        for code, name in languages():
            menu.add_command(label=_used(code == current) + name, command=lambda picked=code: self._set_language(picked))
        menu.add_separator()
        menu.add_command(label=text("menu.edit_commands", "Editar comandos…"), command=self._edit_commands)
        menu.add_command(label=text("menu.edit_help", "Editar ayuda…"), command=self._edit_help)

    def _language_items(self) -> list:
        from grok_assistant.i18n import languages, text

        current = self.hub.brain.settings.language
        rows = [("cmd", name, f"lang:{code}", code == current) for code, name in languages()]
        rows.append(("sep",))
        rows.append(("cmd", text("menu.edit_commands", "Editar comandos…"), "edit-commands", False))
        rows.append(("cmd", text("menu.edit_help", "Editar ayuda…"), "edit-help", False))
        return rows

    def _set_language(self, code: str) -> None:
        from grok_assistant.i18n import activate, languages

        activate(code)
        self.hub.brain.settings.language = code
        installed = set(self.hub.brain.recognizers)
        ear = self.hub.brain.settings.recognizer
        locked = EAR_LANG.get(ear)
        if locked and locked != code:
            for candidate in ("base", "whisper", "canary", "small", "cohere"):
                if candidate in installed:
                    self.hub.brain.settings.recognizer = candidate
                    break
        self._choose_best_ear(False)
        self.hub.brain.persist()
        self.hub.brain.set_devices(self.speaker.list_voices(code), self.hub.brain.recognizers)
        self._build_menus()
        self._apply_chrome()
        reopen_persona = self._drop_window("_persona_win")
        reopen_about = self._drop_window("_about_win")
        reopen_market = self._drop_window("_market_win")
        self._sync_ear()
        name = dict(languages()).get(code, code)
        self._note(f"idioma {name}")
        self._announce_combined()
        self._paint()
        if reopen_persona:
            self._build_personality()
        if reopen_about:
            self._build_about()
        if reopen_market:
            self._build_market()

    def _edit_commands(self) -> None:
        from grok_assistant.i18n import current, save_section

        window = tk.Toplevel(self.root)
        window.title(self.hub.brain.settings.language)
        window.configure(bg=BG)
        window.geometry("720x560")
        ttk.Label(window, text=_ui("dialog.commands_hint", "Un comando por línea: id = frase | frase"), style="Muted.TLabel").pack(anchor="w", padx=12, pady=8)
        box = tk.Text(window, wrap="word", bg=FIELD, fg=INK, insertbackground=INK, font=MONO, relief="flat", padx=10, pady=8)
        box.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        commands = dict(current().get("commands") or {})
        lines = []
        for item in commands.get("fixed") or []:
            lines.append(str(item.get("id") or "") + " = " + " | ".join(item.get("phrases") or []))
        box.insert("1.0", "\n".join(lines))

        def save() -> None:
            fixed = []
            for line in box.get("1.0", "end").splitlines():
                if "=" not in line:
                    continue
                ident, rest = line.split("=", 1)
                ident = ident.strip()
                if not ident:
                    continue
                phrases = [piece.strip() for piece in rest.split("|") if piece.strip()]
                previous = next((item for item in commands.get("fixed") or [] if item.get("id") == ident), {})
                fixed.append({
                    "id": ident,
                    "phrases": phrases,
                    "confirm": bool(previous.get("confirm")),
                    "admin": bool(previous.get("admin")),
                })
            commands["fixed"] = fixed
            save_section("commands", commands)
            self._note("comandos de este idioma guardados")
            window.destroy()

        ttk.Button(window, text=_ui("menu.apply", "Aplicar"), command=save).pack(anchor="e", padx=12, pady=(0, 12))

    def _edit_help(self) -> None:
        from grok_assistant.helptext import help_topics
        from grok_assistant.i18n import save_section

        window = tk.Toplevel(self.root)
        window.title(self.hub.brain.settings.language)
        window.configure(bg=BG)
        window.geometry("720x560")
        ttk.Label(
            window,
            text=_ui("dialog.help_hint", "Cada ayuda: título, luego example: ejemplo, luego el texto, y una línea ---"),
            style="Muted.TLabel",
        ).pack(anchor="w", padx=12, pady=8)
        box = tk.Text(window, wrap="word", bg=FIELD, fg=INK, insertbackground=INK, font=FONT, relief="flat", padx=10, pady=8)
        box.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        blocks = []
        for title, body, example in help_topics():
            blocks.append(f"{title}\nexample: {example}\n{body}\n---")
        box.insert("1.0", "\n".join(blocks))

        def save() -> None:
            topics = []
            for block in box.get("1.0", "end").split("\n---"):
                rows = [row for row in block.strip().splitlines() if row.strip()]
                if len(rows) < 2:
                    continue
                title = rows[0].strip()
                example = ""
                body_rows = []
                for row in rows[1:]:
                    if row.lower().startswith("example:"):
                        example = row.split(":", 1)[1].strip()
                    else:
                        body_rows.append(row)
                topics.append({"title": title, "body": " ".join(body_rows).strip(), "example": example})
            save_section("help", topics)
            self._note("ayuda de este idioma guardada")
            window.destroy()

        ttk.Button(window, text=_ui("menu.apply", "Aplicar"), command=save).pack(anchor="e", padx=12, pady=(0, 12))

    def _banter_kind_rows(self) -> list:
        from grok_assistant.banter import KINDS

        selected = set(self.hub.brain.settings.line_kinds)
        rows = [
            ("cmd", _ui(f"banter.kind.{kind}", kind), f"banter-kind:{kind}", kind in selected)
            for kind in KINDS
        ]
        rows.append(("sep",))
        rows.append(("cmd", _ui("banter.kind.mix", "Mezcla de todo"), "banter-kind:mix", set(KINDS) <= selected))
        return rows

    def _banter_theme_rows(self) -> list:
        from grok_assistant.banter import THEMES

        selected = set(self.hub.brain.settings.line_themes)
        return [
            ("cmd", _ui(f"banter.theme.{theme}", theme), f"banter-theme:{theme}", theme in selected)
            for theme in THEMES
        ]

    def _fill_banter_kinds(self) -> None:
        self._fill_checks(self.menu_banter_kinds, self._banter_kind_rows())

    def _fill_banter_themes(self) -> None:
        self._fill_checks(self.menu_banter_themes, self._banter_theme_rows())

    def _fill_checks(self, menu, rows: list) -> None:
        menu.delete(0, "end")
        held = []
        for row in rows:
            if row[0] == "sep":
                menu.add_separator()
                continue
            _kind, label, key, on = row
            var = tk.BooleanVar(value=on)
            menu.add_checkbutton(
                label=label,
                variable=var,
                command=lambda key=key, var=var: self._banter_set(key, bool(var.get()), var),
            )
            held.append(var)
        menu._held_vars = held

    def _banter_set(self, key: str, enabled: bool | None = None, var=None) -> None:
        from grok_assistant.banter import KINDS, THEMES, apply_choice

        head, item = key.split(":", 1)
        kinds = head == "banter-kind"
        allowed = KINDS if kinds else THEMES
        settings = self.hub.brain.settings
        current = list(settings.line_kinds if kinds else settings.line_themes)
        mix = kinds and item == "mix"
        if enabled is None:
            enabled = (set(allowed) != set(current)) if mix else item not in current
        chosen = apply_choice(current, allowed, item, bool(enabled), mix=mix)
        if kinds:
            settings.line_kinds = chosen
        else:
            settings.line_themes = chosen
        if var is not None:
            var.set(set(KINDS) <= set(chosen) if mix else item in chosen)
        self.hub.brain.persist()
        picked_kinds = ", ".join(_ui(f"banter.kind.{name}", name) for name in KINDS if name in settings.line_kinds)
        picked_themes = ", ".join(_ui(f"banter.theme.{name}", name) for name in THEMES if name in settings.line_themes)
        self._note(f"{_ui('menu.banter', 'Saludos')}: {picked_kinds}. {picked_themes}.")

    def _persona_items(self) -> list:
        from grok_assistant.personality import persons

        current = str(self.hub.brain.settings.personality.get("profile") or "")
        rows = [("cmd", _ui("persona.none", "Sin persona — la voz de siempre"), "persona:", not current)]
        for person in persons():
            rows.append(("cmd", f"{person.name} — {person.label}", f"persona:{person.id}", person.id == current))
        rows.append(("sep",))
        rows.append(("cmd", _ui("persona.adjust", "Ajustar rasgos y comportamiento…"), "persona-edit", False))
        return rows

    def _choose_person(self, person_id: str) -> None:
        from grok_assistant.personality import load_person, person_by_id

        self.hub.brain.settings.personality = load_person(person_id)
        self.hub.brain.persist()
        person = person_by_id(person_id)
        if person is None:
            self._note("sin persona. Grok contesta con la voz de siempre.")
        else:
            self._note(f"persona {person.name}: {person.label}")
        self._open_personality()
        self._paint()

    def _open_personality(self) -> None:
        existing = getattr(self, "_persona_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    self._persona_fill(self.hub.brain.settings.personality)
                    existing.deiconify()
                    existing.lift()
                    return
            except tk.TclError:
                pass
        self._build_personality()

    def _choice_map(self, prefix: str, pairs: tuple) -> tuple[list[str], dict[str, str], dict[str, str]]:
        labels: list[str] = []
        to_id: dict[str, str] = {}
        to_label: dict[str, str] = {}
        for key, fallback in pairs:
            shown = _ui(f"{prefix}.{key}", fallback)
            if shown in to_id:
                shown = f"{shown} · {key}"
            labels.append(shown)
            to_id[shown] = key
            to_label[key] = shown
        return labels, to_id, to_label

    def _build_personality(self) -> None:
        from grok_assistant.personality import CULTURES, FORMALITY, TONES, TRAITS, VERBOSITY, persons

        window = tk.Toplevel(self.root)
        window.title(_ui("persona.title", "Personalidad"))
        window.configure(bg=BG)
        window.geometry("760x720")
        self._persona_win = window
        self._persona_hold = False
        blank_label = _ui("persona.none", "Sin persona — la voz de siempre")
        self._persona_ids = {blank_label: ""}
        self._persona_labels = {"": blank_label}
        for person in persons():
            shown = f"{person.name} — {person.label}"
            self._persona_ids[shown] = person.id
            self._persona_labels[person.id] = shown
        self._persona_choice = tk.StringVar()
        self._persona_meaning = tk.StringVar()
        self._persona_tone = tk.StringVar()
        self._persona_culture = tk.StringVar()
        self._persona_verbosity = tk.StringVar()
        self._persona_formality = tk.StringVar()
        tone_labels, self._tone_ids, self._tone_labels = self._choice_map("tone", TONES)
        culture_labels, self._culture_ids, self._culture_labels = self._choice_map("culture", CULTURES)
        verbosity_labels, self._verbosity_ids, self._verbosity_labels = self._choice_map("form", VERBOSITY)
        formality_labels, self._formality_ids, self._formality_labels = self._choice_map("form", FORMALITY)

        ttk.Label(window, text=_ui("persona.title", "Personalidad"), style="Status.TLabel").pack(anchor="w", padx=16, pady=(14, 2))
        ttk.Label(
            window,
            text=_ui("persona.hint", "Elige una persona y, si quieres, mueve cada rasgo. El comportamiento es texto libre."),
            style="Muted.TLabel",
        ).pack(anchor="w", padx=16, pady=(0, 8))
        buttons = ttk.Frame(window)
        buttons.pack(side="bottom", anchor="e", padx=16, pady=12)
        ttk.Button(buttons, text=_ui("menu.restore", "Restaurar"), command=self._persona_restore).pack(side="right")
        ttk.Button(buttons, text=_ui("menu.apply", "Aplicar"), command=self._persona_save).pack(side="right", padx=(0, 8))
        page = ttk.Frame(window)
        page.pack(fill="both", expand=True, padx=8)
        _canvas, inner = self._scroll_page(page)

        head = ttk.Frame(inner)
        head.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(head, text=_ui("persona.person", "Persona")).pack(anchor="w")
        person_labels = list(self._persona_ids)
        picker = ttk.OptionMenu(head, self._persona_choice, person_labels[0], *person_labels[1:])
        picker.pack(anchor="w", pady=(2, 6))
        ttk.Label(head, textvariable=self._persona_meaning, wraplength=680, style="Muted.TLabel").pack(anchor="w")

        picks = ttk.Frame(inner)
        picks.pack(fill="x", padx=8, pady=(10, 4))
        self._option_row(picks, _ui("persona.tone", "Tono"), self._persona_tone, tone_labels)
        self._option_row(picks, _ui("persona.culture", "Cultura"), self._persona_culture, culture_labels)
        self._option_row(picks, _ui("persona.verbosity", "Verbosidad"), self._persona_verbosity, verbosity_labels)
        self._option_row(picks, _ui("persona.formality", "Formalidad"), self._persona_formality, formality_labels)

        self._persona_scales = {}
        for key, title, low, high in TRAITS:
            row = ttk.Frame(inner)
            row.pack(fill="x", padx=8, pady=3)
            shown = _ui(f"trait.{key}", title)
            low_label = _ui(f"trait.{key}.low", low)
            high_label = _ui(f"trait.{key}.high", high)
            ttk.Label(row, text=f"{shown}    {low_label}  ·  {high_label}").pack(anchor="w")
            scale = tk.Scale(
                row, from_=0, to=100, orient="horizontal", showvalue=True,
                bg=BG, fg=INK, troughcolor=FIELD, highlightthickness=0,
                activebackground=TEAL, length=640,
            )
            scale.pack(anchor="w")
            self._persona_scales[key] = scale

        ttk.Label(inner, text=_ui("persona.behavior", "Comportamiento")).pack(anchor="w", padx=8, pady=(12, 2))
        ttk.Label(
            inner,
            text=_ui("persona.behavior_hint", "Esto no es un número. Escribe cómo debe comportarse."),
            style="Muted.TLabel",
        ).pack(anchor="w", padx=8)
        self._persona_behavior = tk.Text(
            inner, height=8, wrap="word", bg=FIELD, fg=INK, insertbackground=INK,
            font=FONT, relief="flat", padx=10, pady=8,
        )
        self._persona_behavior.pack(fill="x", padx=8, pady=(4, 12))
        self._persona_choice.trace_add("write", self._on_person_picked)
        self._persona_fill(self.hub.brain.settings.personality)

    def _option_row(self, parent, title: str, variable: tk.StringVar, labels: list[str]) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=title, width=14).pack(side="left")
        ttk.OptionMenu(row, variable, labels[0], *labels[1:]).pack(side="left")

    def _on_person_picked(self, *_args) -> None:
        if self._persona_hold:
            return
        from grok_assistant.personality import load_person

        person_id = self._persona_ids.get(self._persona_choice.get(), "")
        self._persona_fill(load_person(person_id))

    def _persona_fill(self, raw) -> None:
        from grok_assistant.personality import normalize_personality, person_by_id

        cfg = normalize_personality(raw)
        self._persona_hold = True
        self._persona_choice.set(self._persona_labels.get(cfg["profile"], self._persona_labels[""]))
        person = person_by_id(cfg["profile"])
        if person is None:
            self._persona_meaning.set(_ui("persona.none_meaning", "Sin persona. Grok contesta con la voz de siempre."))
        else:
            self._persona_meaning.set(person.meaning)
        self._persona_tone.set(self._tone_labels.get(cfg["tone"], self._tone_labels["auto"]))
        self._persona_culture.set(self._culture_labels.get(cfg["culture"], self._culture_labels["spain_neutral"]))
        self._persona_verbosity.set(self._verbosity_labels.get(cfg["verbosity"], self._verbosity_labels["media"]))
        self._persona_formality.set(self._formality_labels.get(cfg["formality"], self._formality_labels["auto"]))
        for key, scale in self._persona_scales.items():
            scale.set(cfg[key])
        self._persona_behavior.delete("1.0", "end")
        if cfg["behavior"]:
            self._persona_behavior.insert("1.0", cfg["behavior"])
        self._persona_hold = False

    def _persona_restore(self) -> None:
        from grok_assistant.personality import load_person, person_by_id

        person_id = self._persona_ids.get(self._persona_choice.get(), "")
        self._persona_fill(load_person(person_id, stock=True))
        self._persona_save(restored=True)

    def _persona_save(self, restored: bool = False) -> None:
        from grok_assistant.personality import normalize_personality, person_by_id

        cfg = {
            "profile": self._persona_ids.get(self._persona_choice.get(), ""),
            "tone": self._tone_ids.get(self._persona_tone.get(), "auto"),
            "culture": self._culture_ids.get(self._persona_culture.get(), "spain_neutral"),
            "verbosity": self._verbosity_ids.get(self._persona_verbosity.get(), "media"),
            "formality": self._formality_ids.get(self._persona_formality.get(), "auto"),
            "behavior": self._persona_behavior.get("1.0", "end").strip(),
        }
        for key, scale in self._persona_scales.items():
            cfg[key] = int(round(float(scale.get())))
        self.hub.brain.settings.personality = normalize_personality(cfg)
        self.hub.brain.persist()
        person = person_by_id(cfg["profile"])
        if restored and person is not None:
            self._note(f"persona {person.name} restaurada a sus valores iniciales.")
        elif person is None:
            self._note("sin persona. La próxima respuesta usa la voz de siempre.")
        else:
            self._note(f"persona {person.name}. La próxima respuesta usa estos rasgos.")
        self._paint()
        if not restored:
            self._drop_window("_persona_win")

    def _alive(self, attr: str) -> bool:
        window = getattr(self, attr, None)
        if window is None:
            return False
        try:
            return bool(window.winfo_exists())
        except tk.TclError:
            return False

    def _drop_window(self, attr: str) -> bool:
        alive = self._alive(attr)
        if alive:
            try:
                getattr(self, attr).destroy()
            except tk.TclError:
                pass
        setattr(self, attr, None)
        return alive

    def _pause_caption(self, big: bool = False) -> str:
        if self.user_paused:
            return _ui("window.big_resume" if big else "menu.resume", "Seguir")
        return _ui("window.big_pause" if big else "menu.pause", "Pausar")

    def _apply_chrome(self) -> None:
        self.root.title("Grok Assistant")
        self.version_label.configure(text=_version_line())
        self.pages.tab(0, text=_ui("window.tab_simple", "Simple"))
        self.pages.tab(1, text=_ui("window.tab_debug", "Depuración"))
        self.pages.tab(2, text=_ui("window.tab_flow", "Flujo"))
        self.debug_label.configure(text=_ui("window.debug", "Depuración — lo que oye y lo que hace después"))
        self.send_button.configure(text=_ui("window.send", "Enviar"))
        self.clear_button.configure(text=_ui("window.clear", "Limpiar registro"))
        quit_label = _ui("menu.quit", "Salir")
        self.quit_button.configure(text=quit_label)
        self.simple_quit.configure(text=_ui("window.big_quit", "Salir"))
        self.pause_button.configure(text=self._pause_caption(False))
        self.simple_pause.configure(text=self._pause_caption(True))
        self._draw_flow(None)
        self._show_usage()

    def _show_usage(self) -> None:
        try:
            if not self._usage_known:
                self.usage_var.set(_ui("window.account", "cuenta {n}%").replace("{n}", "…"))
                self.usage_label.configure(fg=MUTED)
                return
            percent = self._usage_percent
            if percent is None:
                self.usage_var.set(_ui("window.no_account", "sin cuenta"))
                self.usage_label.configure(fg=MUTED)
                return
            self.usage_var.set(_ui("window.account", "cuenta {n}%").replace("{n}", str(percent)))
            if percent >= 90:
                color = "#e06a6a"
            elif percent >= 70:
                color = AMBER
            else:
                color = TEAL
            self.usage_label.configure(fg=color)
        except tk.TclError:
            return

    def _offer_used(self, offer: Offer) -> bool:
        settings = self.hub.brain.settings
        if offer.kind == "voice":
            voices = self.hub.brain.voices
            if not voices:
                return False
            current = voices[min(settings.voice_index, len(voices) - 1)]
            return current == offer.use_label or current == offer.title
        if offer.kind == "stt":
            return bool(offer.engine_id) and offer.engine_id == settings.recognizer
        if offer.kind == "llm":
            if not settings.local_llm or not offer.files:
                return False
            filename = offer.files[0][1].rsplit("/", 1)[-1]
            return filename == settings.llm_file
        return False

    def _offer_title(self, offer: Offer) -> str:
        if offer.kind == "stt" and offer.engine_id:
            return _ui(f"offer.{offer.engine_id}.title", offer.title)
        return offer.title

    def _offer_detail(self, offer: Offer) -> str:
        if offer.kind == "stt" and offer.engine_id:
            return _ui(f"offer.{offer.engine_id}.detail", offer.detail)
        if offer.kind == "llm":
            return _ui("offer.llm.detail", offer.detail)
        if offer.detail.startswith("Piper ·"):
            return offer.detail
        return _ui("offer.voice.detail", offer.detail)

    def _short_line(self, value: str, limit: int = 120) -> str:
        compact = " ".join(value.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + "…"

    def _refresh_market_marks(self) -> None:
        for offer, button, chip in list(getattr(self, "_market_marks", [])):
            try:
                self._show_market_action(offer, button, chip)
            except tk.TclError:
                return

    def _show_market_action(self, offer: Offer, button: ttk.Button, chip: tk.Label) -> None:
        """The active row keeps a green mark where Usar would be."""
        if offer.ready() and self._offer_used(offer):
            if button.winfo_manager():
                button.pack_forget()
            if not chip.winfo_manager():
                chip.pack(side="left")
            chip.configure(text=_ui("market.used", "EN USO"))
            return
        if chip.winfo_manager():
            chip.pack_forget()
        if not button.winfo_manager():
            button.pack(side="left")

    def _warm_piper(self) -> None:
        from grok_assistant.marketplace import fetch_piper_index, piper_cached

        if piper_cached():
            return
        found = fetch_piper_index()
        def apply() -> None:
            loading = getattr(self, "_market_loading", None)
            if loading is not None:
                try:
                    loading.set("" if found else _ui("market.catalog_fail", "No pude leer el catálogo Piper."))
                except tk.TclError:
                    pass
            if found and not getattr(self, "_market_busy", False):
                self._append_market_extras()

        self.ui.put(apply)

    def _append_market_extras(self) -> None:
        if not self._alive("_market_win"):
            return
        from grok_assistant.i18n import code
        from grok_assistant.marketplace import extra_piper_offers

        parent = getattr(self, "_market_voice_inner", None)
        status = getattr(self, "_market_status", None)
        if parent is None or status is None:
            return
        shown = getattr(self, "_market_shown", set())
        for offer in extra_piper_offers(code()):
            if offer.id in shown:
                continue
            try:
                self._market_row(parent, offer, status)
            except tk.TclError:
                return
            shown.add(offer.id)

    def _open_market(self) -> None:
        if self._alive("_market_win"):
            self._market_win.deiconify()
            self._market_win.lift()
            return
        self._build_market()

    def _build_market(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Voice market")
        window.configure(bg=BG)
        window.geometry("980x640")
        self._market_win = window
        self._market_marks = []
        self._market_shown = set()
        self._download_rows = {}
        self._market_busy = any(job.get("running") for job in self._downloads.values())
        ttk.Label(window, text="Voice market", style="Status.TLabel").pack(anchor="w", padx=16, pady=(14, 2))
        ttk.Label(
            window,
            text=_ui("market.hint", "Nada baja solo. En el menú entra cuando la descarga llega al 100 %."),
            style="Muted.TLabel",
        ).pack(anchor="w", padx=16, pady=(0, 8))
        status = tk.StringVar(value="")
        self._market_status = status
        ttk.Label(window, textvariable=status, style="Muted.TLabel").pack(side="bottom", anchor="w", padx=16, pady=(0, 10))
        book = ttk.Notebook(window, style="Market.TNotebook")
        book.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        groups = (
            ("stt", _ui("market.stt", "Reconocimiento")),
            ("voice", _ui("market.voices", "Voces")),
            ("llm", _ui("market.llm", "Modelo local")),
        )
        canvases: dict[str, tk.Canvas] = {}
        catalog = offers_for()
        for kind, title in groups:
            page = ttk.Frame(book)
            book.add(page, text=title)
            canvas, inner = self._scroll_page(page)
            canvases[str(page)] = canvas
            rows = [offer for offer in catalog if offer.kind == kind]
            rows.sort(key=lambda offer: (not self._offer_used(offer), offer.title.lower()))
            if kind == "voice":
                self._market_voice_inner = inner
                self._market_voice_head(inner)
            for offer in rows:
                self._market_row(inner, offer, status)
                self._market_shown.add(offer.id)

        def _wheel(event) -> None:
            canvas = canvases.get(str(book.select()))
            if canvas is not None:
                canvas.yview_scroll(int(-event.delta / 120), "units")

        window.bind("<MouseWheel>", _wheel)
        window.bind("<Destroy>", lambda event: window.unbind("<MouseWheel>") if event.widget is window else None)

    def _market_voice_head(self, parent) -> None:
        from grok_assistant.marketplace import piper_cached

        head = tk.Frame(parent, bg=BG)
        head.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(
            head,
            text=_ui("market.more", "Más voces del catálogo Piper (rhasspy/piper-voices)."),
            bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w",
        ).pack(fill="x")
        link = tk.Label(
            head,
            text="huggingface.co/rhasspy/piper-voices",
            bg=BG, fg=TEAL, cursor="hand2", font=("Segoe UI", 10, "underline"), anchor="w",
        )
        link.pack(fill="x")
        link.bind("<Button-1>", lambda _event: webbrowser.open("https://huggingface.co/rhasspy/piper-voices"))
        self._market_loading = tk.StringVar(value="" if piper_cached() else _ui("market.loading", "Busco más voces en el catálogo Piper…"))
        tk.Label(head, textvariable=self._market_loading, bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w").pack(fill="x")

    def _scroll_page(self, page: ttk.Frame) -> tuple[tk.Canvas, ttk.Frame]:
        canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _fit(event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        def _region(_event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _fit)
        inner.bind("<Configure>", _region)
        return canvas, inner

    def _market_row(self, parent, offer: Offer, status: tk.StringVar) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=4, pady=1)
        ready = offer.ready()
        percent = tk.IntVar(value=100 if ready else 0)
        label = tk.StringVar(value="")
        side = tk.Frame(row, bg=BG)
        side.pack(side="right", padx=(6, 8))
        tk.Label(side, text=offer.size, bg=BG, fg=MUTED, font=("Segoe UI", 9), width=16, anchor="e").pack(side="left", padx=(0, 6))
        chip = tk.Label(
            side,
            text=_ui("market.used", "EN USO"),
            bg=GREEN, fg="#10241c", font=("Segoe UI", 10, "bold"),
            width=12, padx=8, pady=2,
        )
        button = ttk.Button(side, style="Compact.TButton", width=12)
        self._market_marks.append((offer, button, chip))
        if ready and self._offer_used(offer):
            chip.pack(side="left")
        else:
            button.pack(side="left")
        body = tk.Frame(row, bg=BG)
        body.pack(side="left", fill="x", expand=True, padx=(2, 4))
        tk.Label(body, text=self._offer_title(offer), bg=BG, fg=INK, font=("Segoe UI", 11), anchor="w").pack(fill="x")
        tk.Label(body, text=self._short_line(self._offer_detail(offer)), bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(fill="x")
        bar = ttk.Progressbar(body, maximum=100, variable=percent, style="Market.Horizontal.TProgressbar")
        state = tk.Label(body, textvariable=label, bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w")
        self._download_rows[offer.id] = {
            "percent": percent,
            "label": label,
            "button": button,
            "bar": bar,
            "state": state,
            "offer": offer,
        }
        running = bool(self._downloads.get(offer.id, {}).get("running"))
        if ready and not running:
            button.configure(text=_ui("market.use", "Usar"), command=lambda item=offer: self._use_offer(item))
        else:
            state.pack(fill="x")
            label.set(_ui("market.missing", "sin descargar"))
            button.configure(
                text=_ui("market.download", "Descargar"),
                command=lambda item=offer: self._download_offer(item, status, percent, label, button, bar, state),
            )
            if offer.id in self._downloads:
                self._paint_download(offer.id)

    def _paint_download(self, offer_id: str) -> None:
        job = self._downloads.get(offer_id)
        row = self._download_rows.get(offer_id)
        if not job or not row:
            return
        try:
            if not row["button"].winfo_exists():
                return
            row["percent"].set(int(job.get("percent") or 0))
            row["label"].set(str(job.get("caption") or ""))
            if job.get("running"):
                if not row["state"].winfo_manager():
                    row["state"].pack(fill="x")
                if not row["bar"].winfo_manager():
                    row["bar"].pack(fill="x", pady=(2, 0))
                row["button"].configure(state="disabled", text=_ui("market.downloading", "Descargando"))
                return
            if row["bar"].winfo_manager():
                row["bar"].pack_forget()
            if job.get("error"):
                row["button"].configure(state="normal", text=_ui("market.download", "Descargar"))
                row["label"].set(str(job["error"]))
                return
            if job.get("done"):
                offer = row["offer"]
                row["label"].set("100 %")
                row["button"].configure(
                    state="normal",
                    text=_ui("market.use", "Usar"),
                    command=lambda item=offer: self._use_offer(item),
                )
        except tk.TclError:
            return

    def _download_offer(self, offer: Offer, status: tk.StringVar, percent: tk.IntVar, label: tk.StringVar, button: ttk.Button, bar: ttk.Progressbar, state: tk.Label | None = None) -> None:
        current = self._downloads.get(offer.id)
        if current and current.get("running"):
            self._paint_download(offer.id)
            return
        job = {"percent": 0, "caption": "0 %", "status": "", "running": True, "done": False, "error": ""}
        self._downloads[offer.id] = job
        self._download_rows[offer.id] = {
            "percent": percent,
            "label": label,
            "button": button,
            "bar": bar,
            "state": state,
            "offer": offer,
        }

        def show(value: int, caption: str = "") -> None:
            job["percent"] = value
            job["caption"] = caption or f"{value} %"
            self.ui.put(lambda offer_id=offer.id: self._paint_download(offer_id))

        def note(message: str) -> None:
            job["status"] = message

            def apply() -> None:
                try:
                    if self._alive("_market_win"):
                        self._market_status.set(message)
                except tk.TclError:
                    return

            self.ui.put(apply)

        def work() -> None:
            try:
                download(offer, note, show)
                job["running"] = False
                job["done"] = True
                job["percent"] = 100
                job["caption"] = "100 %"
                job["error"] = ""

                def done() -> None:
                    self._market_busy = any(item.get("running") for item in self._downloads.values())
                    self._paint_download(offer.id)
                    try:
                        if self._alive("_market_win"):
                            self._market_status.set(f"{offer.title} listo")
                    except tk.TclError:
                        pass
                    self._refresh_devices()

                self.ui.put(done)
            except Exception as exc:
                job["running"] = False
                job["done"] = False
                job["error"] = str(exc)[:180]

                def fail() -> None:
                    self._market_busy = any(item.get("running") for item in self._downloads.values())
                    self._paint_download(offer.id)
                    try:
                        if self._alive("_market_win"):
                            self._market_status.set(job["error"])
                    except tk.TclError:
                        pass

                self.ui.put(fail)

        try:
            self._market_busy = True
            self._paint_download(offer.id)
        except tk.TclError:
            job["running"] = False
            self._market_busy = False
            return
        note(f"descargando {offer.title}…")
        threading.Thread(target=work, daemon=True, name=f"download-{offer.id}").start()

    def _install_windows(self) -> None:
        def work() -> None:
            self.ui.put(lambda: self._note("instalo el reconocedor de Windows. Windows pedirá permiso."))
            message = install_windows_speech()

            def done() -> None:
                self._refresh_devices()
                if "windows" in self.hub.brain.recognizers:
                    self.hub.brain.settings.recognizer = "windows"
                    self.hub.brain.persist()
                    self._sync_ear()
                    self._note("Windows español está listo")
                else:
                    self._note(message.removeprefix("ERR:"))
                self._paint()

            self.ui.put(done)

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
            filename = offer.files[0][1].rsplit("/", 1)[-1] if offer.files else ""
            self.hub.brain.settings.local_llm = True
            self.hub.brain.settings.llm_file = filename
            self.hub.brain.persist()
            if self.hub.mind is not None:
                self.hub.mind.select(filename)
            self._note(f"modelo local: {offer.title}. Si no es un comando, el texto sigue tal cual.")
        self._refresh_market_marks()
        self._paint()

    def _password_dialog(self) -> None:
        title = _ui("dialog.admin", "Administrador")
        first = simpledialog.askstring(title, _ui("dialog.password_new", "Nueva contraseña:"), show="*", parent=self.root)
        if not first:
            return
        second = simpledialog.askstring(title, _ui("dialog.password_repeat", "Repite la contraseña:"), show="*", parent=self.root)
        if first != second:
            messagebox.showinfo(title, _ui("dialog.password_mismatch", "No coinciden."), parent=self.root)
            return
        self.hub.brain.auth.set_password(first)
        self._note("contraseña de administrador guardada. En el disco solo está el hash.")
        self._paint()

    def _open_about(self) -> None:
        if self._alive("_about_win"):
            self._about_win.deiconify()
            self._about_win.lift()
            return
        self._build_about()

    def _build_about(self) -> None:
        window = tk.Toplevel(self.root)
        window.title(_ui("about.title", "Acerca de"))
        window.configure(bg=BG)
        window.geometry("720x560")
        self._about_win = window
        book = ttk.Notebook(window, style="Market.TNotebook")
        book.pack(fill="both", expand=True, padx=12, pady=12)
        about = ttk.Frame(book)
        commands = ttk.Frame(book)
        book.add(about, text=_ui("about.title", "Acerca de"))
        book.add(commands, text=_ui("about.commands", "Comandos"))
        body = tk.Text(
            about, wrap="word", bg=FIELD, fg=INK, font=("Segoe UI", 12),
            relief="flat", padx=18, pady=16, insertbackground=INK,
        )
        body.pack(fill="both", expand=True)
        body.tag_configure("name", font=("Segoe UI", 16, "bold"), foreground=AMBER, spacing3=6)
        body.tag_configure("quiet", foreground=MUTED, spacing3=10)
        self._link_tag(body, "github", "https://github.com/antonio-castellon")
        self._link_tag(body, "site", "https://www.castellon.ch")
        body.insert("end", "Antonio Castellon\n", "name")
        body.insert("end", _version_line() + "\n", "quiet")
        body.insert("end", "Castellon.CH\n", "quiet")
        body.insert("end", "GitHub  ")
        body.insert("end", "antonio-castellon", "github")
        body.insert("end", "\nWeb  ")
        body.insert("end", "www.castellon.ch", "site")
        body.insert("end", "\n\n" + _ui("about.body", ""))
        body.bind("<Key>", lambda _event: "break")
        self._fill_commands(commands)
        window.protocol("WM_DELETE_WINDOW", window.destroy)

    def _fill_commands(self, parent: ttk.Frame) -> None:
        box = tk.Text(
            parent, wrap="word", bg=FIELD, fg=INK, font=("Segoe UI", 12),
            relief="flat", padx=18, pady=16, insertbackground=INK,
        )
        box.pack(fill="both", expand=True)
        box.tag_configure("title", font=("Segoe UI", 14, "bold"), foreground=AMBER, spacing1=14, spacing3=4)
        box.tag_configure("example", font=("Consolas", 12), foreground=TEAL, spacing3=8)
        box.insert("end", _ui("about.lead", "") + "\n")
        example_word = _ui("about.example", "Ejemplo")
        for title, body, example in help_topics():
            box.insert("end", title + "\n", "title")
            box.insert("end", body + "\n")
            box.insert("end", f"{example_word}: {example}\n", "example")
        box.configure(state="disabled")

    def _link_tag(self, text: tk.Text, tag: str, url: str) -> None:
        text.tag_configure(tag, foreground=TEAL, underline=True)
        text.tag_bind(tag, "<Button-1>", lambda _event, url=url: webbrowser.open(url))
        text.tag_bind(tag, "<Enter>", lambda _event: text.configure(cursor="hand2"))
        text.tag_bind(tag, "<Leave>", lambda _event: text.configure(cursor="arrow"))

    def _note(self, text: str) -> None:
        self.hub.brain.note(text)

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
            item = self.jobs.get()
            if item[0] == "stop":
                break
            kind = item[0]
            payload = item[1] if len(item) > 1 else ""
            embedding = item[2] if len(item) > 2 else None
            speaker_id = item[3] if len(item) > 3 else None
            heard_by = item[4] if len(item) > 4 else ""
            try:
                self._job(kind, payload, embedding, speaker_id, heard_by)
            except Exception as exc:
                self._write_crash(exc)

    def _write_crash(self, exc: Exception) -> None:
        import traceback
        from grok_assistant.paths import default_data_dir

        path = default_data_dir() / "crash.log"
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(traceback.format_exc())
                handle.write("\n")
        except OSError:
            return
        self.ui.put(lambda: self._note(f"fallo interno: {exc}"))

    def _job(self, kind: str, payload: str, embedding, speaker_id=None, heard_by: str = "") -> None:
        if kind == "note":
            self._note(payload)
            self._refresh()
            return
        if kind == "startup":
            self.say(self.hub.startup())
            self._refresh()
            return
        if kind == "tick":
            result = self.hub.tick(speaker=self.say)
            self._apply(result)
            self._refresh()
            return
        if kind == "rename":
            turn = self.hub.brain.rename_typed(payload)
            for line in turn.speak:
                self.say(line)
            self._note(f"nombre: {self.hub.brain.settings.wake_name}")
            self._refresh()
            return
        if kind == "capture":
            turn = self.hub.brain.start_capture(payload, speaker_id)
            for line in turn.speak:
                self.say(line)
            self._apply(turn)
            if self.hub.brain.enroll is None:
                self._resume_ears()
            self._refresh()
            return
        if kind == "speak":
            self.say(payload)
            self._refresh()
            return
        if kind == "phrase":
            self._hold_mic(True)
            try:
                result = self.hub.run(payload, speaker=self.say, vector=embedding, speaker_id=speaker_id)
                self._apply(result)
                if any(item[0] == "ask_password" for item in result.effects):
                    password = self._ask(_ui("dialog.admin", "Administrador"))
                    follow = self.hub.submit_password(password, speaker=self.say) if password else self.hub.cancel_password(speaker=self.say)
                    self._apply(follow)
            finally:
                self._hold_mic(False)
            if heard_by:
                self.hub.brain._step(heard_by)
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

    def _play_song(self, title: str) -> None:
        def status(message: str) -> None:
            self.ui.put(lambda message=message: self.say(message))

        trouble = self.music.play(title, self.hub.brain.settings.volume, status)
        if trouble:
            self.ui.put(lambda trouble=trouble: self.say(trouble))
            return
        self._music_note = False
        self.ui.put(lambda: self._note("la música suena. Sigo oyendo solo una voz registrada."))

    def _voice_name(self) -> str:
        voices = self.hub.brain.voices
        index = self.hub.brain.settings.voice_index
        if not voices:
            return ""
        return voices[min(index, len(voices) - 1)]

    def _apply(self, result) -> None:
        for effect in result.effects:
            kind = effect[0]
            if kind == "record_take":
                self._capture_phrase()
            elif kind == "score_prints":
                self._score_person_later(effect[1])
            elif kind == "play":
                title = effect[1]
                threading.Thread(target=lambda title=title: self._play_song(title), daemon=True).start()
            elif kind == "pause_music":
                self.music.pause()
            elif kind == "resume_music":
                self.music.resume()
            elif kind == "stop_music":
                self.music.stop()
            elif kind == "recognizer":
                self._sync_ear()

    def _capture_phrase(self) -> None:
        """The next phrase comes from the ear already on the microphone."""
        if not self._arm_take_mic():
            self.hub.brain.enroll = None
            self._close_print_modal()
            self.say("No oigo el micrófono. Lo dejo.")
            self._hold_mic(False)
            self._refresh()
            return
        decision, text, audio = self._wait_print_decision()
        self._take_open = False
        if decision == "salir":
            self._abort_print()
            return
        self._hold_mic(True)
        self._end_take()
        vector = None
        if audio is not None:
            if not self.voiceprint.ready():
                self.hub.brain.enroll = None
                self._close_print_modal()
                self.say("Falta el modelo de la huella.")
                self._hold_mic(False)
                self._refresh()
                return
            try:
                vector = self.voiceprint.embed(audio)
            except Exception as exc:
                self._write_crash(exc)
        turn = self.hub.brain.accept_take(audio, vector, text)
        self._refresh()
        if self.hub.brain.enroll is not None:
            self.ui.put(self._ensure_print_modal)
        else:
            self._close_print_modal()
        for line in turn.speak:
            self.say(line)
        self._apply(turn)
        if self.hub.brain.enroll is None:
            self._close_print_modal()
            self._hold_mic(False)

    def _arm_take_mic(self) -> bool:
        if self._ears_suspended:
            self._resume_ears()
        if self.dictation is None and self.kroko is None and self.offline is None:
            self._sync_ear()
        if self.dictation is None and self.kroko is None and self.offline is None:
            self.hub.brain.note("huella: el micrófono no está abierto")
            return False
        self._hold_mic(True)
        import time

        time.sleep(0.1)
        self._drop_queued_phrases()
        while True:
            try:
                self._take_box.get_nowait()
            except queue.Empty:
                break
        self._begin_take()
        return True

    def _begin_take(self) -> None:
        """Open the microphone and beep together. The tone does not delay the ear."""
        from grok_assistant.enroll_audio import play_tone

        brain = self.hub.brain
        brain.hearing = True
        brain._live_text = ""
        brain._live_open = False
        self._take_open = True
        self._set_capture(True)
        self._set_hold(True)
        self._hold_mic(False)
        threading.Thread(target=play_tone, args=(True,), daemon=True).start()
        self.ui.put(self._ensure_print_modal)
        self._refresh()

    def _end_take(self) -> None:
        """Close the long window and beep while the microphone is paused."""
        from grok_assistant.enroll_audio import play_tone

        self.hub.brain.hearing = False
        self._set_hold(False)
        self._set_capture(False)
        play_tone(False)
        self._refresh()

    def _set_capture(self, capture: bool) -> None:
        for ear in (self.kroko, self.offline):
            if ear is not None:
                ear.set_capture(capture)

    def _set_hold(self, hold: bool) -> None:
        for ear in (self.kroko, self.offline):
            if ear is not None and hasattr(ear, "set_hold"):
                ear.set_hold(hold)

    def _wait_print_decision(self) -> tuple[str, str, object]:
        """Seguir keeps this phrase. Reintentar records it again. Salir drops the session."""
        pending = []
        while True:
            try:
                pending.append(self._print_wait.get_nowait())
            except queue.Empty:
                break
        if "salir" in pending:
            return "salir", "", None
        pending_text, pending_audio = "", None
        while True:
            try:
                decision = self._print_wait.get(timeout=0.15)
            except queue.Empty:
                decision = ""
            while True:
                try:
                    text, audio = self._take_box.get_nowait()
                except queue.Empty:
                    break
                if audio is not None and time.monotonic() >= self._drop_take_audio:
                    pending_text, pending_audio = str(text or ""), audio
                    self.ui.put(lambda heard=pending_text: self._set_print_heard(heard))
            if decision == "salir":
                return "salir", "", None
            if decision == "reintentar":
                extra = []
                while True:
                    try:
                        extra.append(self._print_wait.get_nowait())
                    except queue.Empty:
                        break
                if "salir" in extra:
                    return "salir", "", None
                self._restart_print_listen()
                pending_text, pending_audio = "", None
                continue
            if decision != "seguir":
                continue
            if pending_audio is None:
                self._flush_open_ear()
                try:
                    text, audio = self._take_box.get(timeout=1.2)
                except queue.Empty:
                    text, audio = "", None
                if audio is not None:
                    pending_text, pending_audio = str(text or ""), audio
            if pending_audio is None:
                self.ui.put(lambda: self._set_print_hint(_ui("dialog.print_wait", "Aún no oigo. Di la frase y pulsa Seguir.")))
                continue
            return "seguir", pending_text, pending_audio

    def _abort_print(self) -> None:
        self._take_open = False
        self._set_hold(False)
        self._end_take()
        self._hold_mic(False)
        turn = self.hub.brain.discard_capture()
        self._close_print_modal()
        for line in turn.speak:
            self.say(line)
        self._refresh()

    def _ensure_print_modal(self) -> None:
        enroll = self.hub.brain.enroll
        if not isinstance(enroll, dict) or enroll.get("stage") != "takes":
            self._close_print_modal()
            return
        if self._print_win is None or not self._print_win.winfo_exists():
            win = tk.Toplevel(self.root)
            win.title(_ui("dialog.print_name", "Huella"))
            win.configure(bg=BG)
            win.resizable(False, False)
            win.protocol("WM_DELETE_WINDOW", self._print_leave)
            self._print_count = tk.StringVar(master=win)
            self._print_phrase = tk.StringVar(master=win)
            self._print_heard = tk.StringVar(master=win)
            self._print_hint = tk.StringVar(master=win)
            ttk.Label(win, textvariable=self._print_count, style="Muted.TLabel").pack(anchor="w", padx=18, pady=(16, 0))
            ttk.Label(win, text=_ui("dialog.print_say", "Di esta frase"), style="Muted.TLabel").pack(anchor="w", padx=18, pady=(10, 0))
            tk.Label(
                win, textvariable=self._print_phrase, bg=BG, fg=AMBER,
                font=("Segoe UI", 22, "bold"), wraplength=460, justify="left",
            ).pack(anchor="w", padx=18, pady=(8, 4))
            ttk.Label(win, text=_ui("dialog.print_heard", "Oído"), style="Muted.TLabel").pack(anchor="w", padx=18, pady=(12, 0))
            tk.Label(
                win, textvariable=self._print_heard, bg=FIELD, fg=INK, font=FONT,
                wraplength=460, justify="left", anchor="nw", padx=10, pady=8, height=2,
            ).pack(fill="x", padx=18, pady=(4, 0))
            ttk.Label(win, textvariable=self._print_hint, style="Muted.TLabel").pack(anchor="w", padx=18, pady=(8, 0))
            row = ttk.Frame(win)
            row.pack(fill="x", padx=18, pady=16)
            ttk.Button(row, text=_ui("dialog.print_retry", "Reintentar"), command=self._print_retry).pack(side="left")
            ttk.Button(row, text=_ui("dialog.print_next", "Seguir"), command=self._print_next).pack(side="left", padx=(12, 0))
            ttk.Button(row, text=_ui("dialog.print_leave", "Salir"), command=self._print_leave).pack(side="right")
            self._print_win = win
            self.root.deiconify()
            win.update_idletasks()
            win.geometry("520x320")
            win.grab_set()
            win.lift()
        self._fill_print_modal()

    def _fill_print_modal(self) -> None:
        enroll = self.hub.brain.enroll
        if self._print_win is None or not isinstance(enroll, dict):
            return
        index = int(enroll.get("take") or 0)
        phrases = self.hub.brain._phrases()
        total = len(phrases)
        phrase = phrases[index] if 0 <= index < total else ""
        count = _ui("dialog.print_count", "{n} de {total}").replace("{n}", str(index + 1)).replace("{total}", str(total))
        self._print_count.set(count)
        self._print_phrase.set(phrase)
        self._print_hint.set("")
        self._print_heard.set(self.hub.brain._live_text or "")

    def _set_print_heard(self, heard: str) -> None:
        if self._print_win is None or not self._print_win.winfo_exists():
            return
        self._print_heard.set(heard)
        if hasattr(self, "_print_hint"):
            self._print_hint.set("")

    def _set_print_hint(self, hint: str) -> None:
        if self._print_win is None or not self._print_win.winfo_exists():
            return
        self._print_hint.set(hint)

    def _print_next(self) -> None:
        self._print_wait.put("seguir")

    def _print_retry(self) -> None:
        self._print_wait.put("reintentar")

    def _print_leave(self) -> None:
        self._print_wait.put("salir")

    def _restart_print_listen(self) -> None:
        """Drop only this phrase and listen for it again. Earlier phrases stay."""
        from grok_assistant.enroll_audio import play_tone

        self._drop_take_audio = time.monotonic() + 0.35
        self._hold_mic(True)
        time.sleep(0.15)
        while True:
            try:
                self._take_box.get_nowait()
            except queue.Empty:
                break
        brain = self.hub.brain
        brain._live_text = ""
        brain._live_open = False
        self._set_capture(True)
        self._set_hold(True)
        self._hold_mic(False)
        threading.Thread(target=play_tone, args=(True,), daemon=True).start()
        self.ui.put(self._mark_print_retry)

    def _mark_print_retry(self) -> None:
        self._set_print_heard("")
        self._set_print_hint(_ui("dialog.print_again", "Otra vez. Habla después del pitido."))

    def _close_print_modal(self) -> None:
        def close() -> None:
            win = self._print_win
            self._print_win = None
            if win is not None and win.winfo_exists():
                try:
                    win.grab_release()
                except tk.TclError:
                    pass
                win.destroy()

        self.ui.put(close)

    def _flush_open_ear(self) -> None:
        """The wait ran out. Keep whatever sound the open ear already caught."""
        for ear in (self.kroko, self.offline):
            flush = getattr(ear, "request_flush", None)
            if flush is not None:
                flush()

    def _drop_queued_phrases(self) -> None:
        kept = []
        while True:
            try:
                item = self.jobs.get_nowait()
            except queue.Empty:
                break
            if item[0] != "phrase":
                kept.append(item)
        for item in kept:
            self.jobs.put(item)

    def _suspend_ears(self) -> None:
        self._ears_suspended = True
        ears = [self.dictation, self.kroko, self.offline]
        for ear in ears:
            if ear is not None:
                ear.stop()
        for ear in ears:
            thread = getattr(ear, "_thread", None) if ear is not None else None
            if thread is not None:
                thread.join(timeout=2)
        self.dictation = None
        self.kroko = None
        self.offline = None

    def _resume_ears(self) -> None:
        if not self._ears_suspended:
            return
        self._ears_suspended = False
        self._sync_ear()

    def _score_person_later(self, name: str) -> None:
        threading.Thread(target=self._score_named, args=(name, None), daemon=True).start()

    def _score_pending(self) -> None:
        self._score_named("", None)

    def _score_named(self, name: str, only_ear: str | None) -> None:
        from grok_assistant.ear_score import score_person

        book = self.hub.brain.speakers
        lines: list[str] = []
        with self._score_lock:
            ears = [ear for ear in self.hub.brain.recognizers if ear != "teclado"]
            if only_ear:
                pending = [(name, only_ear)] if book.raw_clips(name) else []
            elif name:
                pending = [
                    (name, ear)
                    for ear in ears
                    if book.raw_clips(name) and book.score_of(name, ear) is None
                ]
            else:
                pending = book.pending_scores(ears)
            for person, ear in pending:
                signature = tuple(clip["file"] for clip in book.raw_clips(person))
                try:
                    hits, total = score_person(book, person, ear)
                except Exception as exc:
                    self._write_crash(exc)
                    continue
                current = tuple(clip["file"] for clip in book.raw_clips(person))
                if current != signature:
                    scores = book.people.get(person, {}).get("scores")
                    if isinstance(scores, dict):
                        scores.pop(ear, None)
                        book.save()
                    continue
                if not total:
                    continue
                label = _ui(f"ear.{ear}", ear)
                percent = round(100 * hits / total)
                lines.append(f"{label} {hits} de {total}")
                self.ui.put(lambda person=person, label=label, percent=percent: self._note(f"{person} · {label}: {percent}%"))
        if lines and name:
            self.jobs.put(("speak", ". ".join(lines) + "."))
        if lines:
            self.ui.put(self._apply_best_ear)

    def _hold_mic(self, hold: bool) -> None:
        paused = hold or self.user_paused
        if self.dictation is not None:
            self.dictation.set_paused(paused)
        if self.kroko is not None:
            self.kroko.set_paused(paused)
        if self.offline is not None:
            self.offline.set_paused(paused)

    def _sync_ear(self) -> None:
        if self._ears_suspended:
            return
        kind = self.hub.brain.settings.recognizer
        want_windows = kind == "windows" and not self.user_paused
        want_stream = kind in STREAMING_KINDS and not self.user_paused
        if want_windows and self.dictation is None:
            ear = Dictation(self._heard, self.pause_file)
            if ear.start():
                self.dictation = ear
                self._note("Windows español está escuchando")
        if not want_windows and self.dictation is not None:
            self.dictation.stop()
            self.dictation = None
        if want_stream and (self.kroko is None or self.kroko.kind != kind):
            if self.kroko is not None:
                self.kroko.stop()
                self.kroko = None
            ear = KrokoEar(
                self._heard,
                self._kroko_status,
                wake_name=lambda: self.hub.brain.settings.wake_name,
                kind=kind,
                on_partial=self._preview,
            )
            if ear.start():
                self.kroko = ear
                if kind == "kroko":
                    self._note("cargo Kroko, el modelo tarda unos segundos")
                else:
                    self._note(f"cargo {RECOGNIZER_LABELS.get(kind, kind)}")
            else:
                self._note(ear.error or "ese oído no pudo escuchar")
        if not want_stream and self.kroko is not None:
            self.kroko.stop()
            self.kroko = None
        want_offline = kind in OFFLINE_KINDS and not self.user_paused
        if want_offline and (self.offline is None or self.offline.kind != kind):
            if self.offline is not None:
                self.offline.stop()
            ear = OfflineEar(kind, self._heard, self._kroko_status)
            if ear.start():
                self.offline = ear
                self._note(f"cargo {RECOGNIZER_LABELS[kind]}")
            else:
                self.offline = None
                self._note(ear.error or "ese oído no pudo escuchar")
        if not want_offline and self.offline is not None:
            self.offline.stop()
            self.offline = None

    def _kroko_status(self, text: str) -> None:
        self.ui.put(lambda text=text: self._note(text))

    def _preview(self, text: str, seq: int = 0) -> None:
        if time.monotonic() < self._drop_take_audio:
            return
        if seq and seq <= self._settled_seq:
            return
        heard = " ".join((text or "").split())
        if not heard:
            return
        self.ui.put(lambda heard=heard, seq=seq: self._show_preview(heard, seq))

    def _show_preview(self, heard: str, seq: int) -> None:
        if seq and seq <= self._settled_seq:
            return
        self.hub.brain.preview(heard)
        self._set_print_heard(heard)

    def _settle_preview(self) -> None:
        ear = self.kroko
        seq = getattr(ear, "_partial_seq", 0) if ear is not None else 0
        if seq > self._settled_seq:
            self._settled_seq = seq

    def _heard(self, text: str, audio=None) -> None:
        if self.user_paused:
            return
        self._settle_preview()
        enroll = self.hub.brain.enroll
        if isinstance(enroll, dict) and enroll.get("stage") == "takes":
            if self._take_open and time.monotonic() >= self._drop_take_audio:
                self._take_box.put((text or "", audio))
            return
        from grok_assistant.match import is_presence, words_norm

        norms = words_norm(text)
        embedding = None
        if audio is not None:
            try:
                embedding = self.voiceprint.embed(audio)
            except Exception as exc:
                self._write_crash(exc)
        allowed, who = self._mic_voice(embedding)
        if not allowed:
            return
        testing = self.hub.brain.test_mode
        # A "can you hear me" stays local. Test mode keeps the selected ear, so Whisper does not cover it.
        second = ""
        if not testing and audio is not None and not is_presence(norms, self.hub.brain.settings.wake_name):
            try:
                second = self.refiner.transcribe(audio)
            except Exception as exc:
                self._write_crash(exc)
                second = ""
        chosen = pick_transcript(text, second, testing)
        primary = " ".join((text or "").split())
        heard_by = ""
        if not testing:
            label = RECOGNIZER_LABELS.get(self.hub.brain.settings.recognizer, self.hub.brain.settings.recognizer)
            replaced = (
                bool(second)
                and chosen.casefold() == " ".join(second.split()).casefold()
                and chosen.casefold() != primary.casefold()
            )
            heard_by = f"{label} · relectura" if replaced else label
        self.jobs.put(("phrase", chosen, embedding, who, heard_by))

    def _mic_voice(self, embedding) -> tuple[bool, str | None]:
        brain = self.hub.brain
        if brain.test_mode or brain.enroll is not None or brain.naming is not None:
            return True, None
        if brain.pending and brain.pending[0] == "new_name":
            return True, None
        ear = brain.settings.recognizer
        who = brain.speakers.closest(embedding, ear) if embedding else None
        if not brain.embedder_ready:
            if self.music.loaded and not who:
                return False, None
            return True, who
        if not brain.speakers.has_prints(ear):
            return False, None
        if brain.speakers.locked and who != brain.speakers.locked:
            return False, None
        if not who:
            return False, None
        return True, who

    def _send(self, _event=None) -> None:
        text = self.entry.get().strip()
        self.entry.delete(0, "end")
        if text:
            self.jobs.put(("phrase", text))

    def _arm_refiner(self) -> None:
        if self.refiner.load():
            self.ui.put(lambda: self._note(f"fuera de la prueba, releo cada frase con {self.refiner.label()} para guardar los nombres en inglés"))

    def _arm_voiceprint(self) -> None:
        if self.voiceprint.ensure():
            self.hub.brain.embedder_ready = True
            self.ui.put(lambda: self._note("la huella de voz está lista"))

    def _poll_usage(self) -> None:
        def work() -> None:
            from grok_assistant.account_usage import fetch_account_percent

            percent = fetch_account_percent()

            def apply() -> None:
                self._usage_known = True
                self._usage_percent = percent
                self._show_usage()

            self.ui.put(apply)

        threading.Thread(target=work, daemon=True).start()
        self.root.after(60_000, self._poll_usage)

    def _pulse(self) -> None:
        if self._closing:
            return
        while True:
            try:
                job = self.ui.get_nowait()
            except queue.Empty:
                break
            try:
                job()
            except tk.TclError:
                continue
            except Exception as exc:
                self._write_crash(exc)
        self.jobs.put(("tick", ""))
        self._paint()
        delay = 120 if self.hub.brain.hearing else 400
        self.root.after(delay, self._pulse)

    def _refresh(self) -> None:
        self.ui.put(self._paint)

    def _draw_flow(self, snap: dict | None) -> None:
        canvas = getattr(self, "flow", None)
        if canvas is None:
            return
        if snap is None:
            snap = self._flow_snap
        if snap is None:
            return
        self._flow_snap = snap
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 80 or height < 80:
            return
        canvas.delete("all")
        ear = self.hub.brain.settings.recognizer
        kind = snap.get("banner_kind") or "wait"
        paused = kind == "pause"
        testing = kind == "test"
        talking = kind == "talk"
        keyboard = ear == "teclado"
        alive = not paused

        def clip(value: str, limit: int = 46) -> str:
            value = value or ""
            return value if len(value) <= limit else value[: limit - 1] + "…"

        def library_for_ear() -> str:
            if ear == "windows":
                return _ui("flow.lib_speech", "Windows Speech")
            if ear == "teclado":
                return _ui("flow.skip", "no entra")
            return "sherpa-onnx"

        voice_raw = snap.get("voice") or ""
        voice_name = voice_raw.split(". ", 1)[-1] if ". " in voice_raw else voice_raw
        try:
            from grok_assistant.speech import _piper_by_label

            piper = voice_name in _piper_by_label()
        except Exception:
            piper = False
        if piper:
            voice_lib = "Piper"
        elif os.name == "nt":
            voice_lib = _ui("flow.lib_speech", "Windows Speech")
        else:
            voice_lib = "espeak"
        local_name = snap.get("identifier") or ""
        if local_name == _ui("status.no_identifier", "sin identificador"):
            local_detail = _ui("flow.lib_none", "sin modelo")
        else:
            local_detail = clip(f"{local_name} · llama.cpp")

        pad = 16
        caption = _ui("flow.caption", "")
        if paused:
            caption = _ui("flow.pause", caption)
        elif testing:
            caption = _ui("flow.test", caption)
        canvas.create_text(pad, 8, anchor="nw", text=caption, fill=AMBER if paused or testing else MUTED, font=("Segoe UI", 11))
        top = 34
        avail = max(height - top - 8, 240)
        gap = 8
        box_h = max(46, min(64, int((avail - gap * 7) / 6.4)))
        inner = width - pad * 2
        half = (inner - 12) / 2

        def box(x, y, bw, bh, title, detail, on, size=12):
            canvas.create_rectangle(x, y, x + bw, y + bh, fill="#16302c" if on else FIELD, outline=TEAL if on else "#2c3844", width=2)
            canvas.create_text(x + bw / 2, y + bh * 0.34, text=title, fill=INK if on else MUTED, font=("Segoe UI", size, "bold"), width=bw - 14)
            canvas.create_text(x + bw / 2, y + bh * 0.70, text=detail, fill=TEAL if on else MUTED, font=("Segoe UI", max(9, size - 2)), width=bw - 14)

        def down(x, y1, y2, on):
            canvas.create_line(x, y1, x, y2, fill=AMBER if on else "#3a4656", width=2, arrow="last", arrowshape=(10, 12, 4))

        y = top
        mic_on = alive and not keyboard
        key_on = alive and keyboard
        box(pad, y, half, box_h, _ui("flow.mic", "Micrófono"), "sounddevice · campplus", mic_on)
        box(pad + half + 12, y, half, box_h, _ui("flow.keys", "Teclado"), _ui("flow.keys_note", "ya es texto"), key_on)
        y += box_h
        down(pad + half / 2, y, y + gap + 2, mic_on)
        down(pad + half + 12 + half / 2, y, y + gap + 2, key_on)
        y += gap
        stt_on = alive and not keyboard and not testing
        stt_detail = library_for_ear()
        if ear != "teclado":
            stt_detail = clip(f"{snap.get('recognizer') or ear} · {stt_detail}")
        box(pad, y, inner, box_h, _ui("flow.stt", "Motor escucha (STT)"), stt_detail, stt_on or (testing and not keyboard))
        y += box_h
        down(width / 2, y, y + gap + 2, alive)
        y += gap
        heard = clip(snap.get("last_heard") or "—")
        box(pad, y, inner, max(40, box_h - 8), _ui("flow.text", "Texto"), heard, alive)
        y += max(40, box_h - 8)
        down(width / 2, y, y + gap + 2, alive and not testing)
        y += gap
        ask_detail = _ui("flow.yes", "") if talking else _ui("flow.no", "")
        box(pad, y, inner, box_h, _ui("flow.ask", "¿Conversación abierta?"), ask_detail, alive and not testing)
        ask_bottom = y + box_h
        y = ask_bottom + gap
        col = (inner - 12) / 2
        local_on = alive and not testing and not talking
        grok_on = alive and talking
        has_local = local_name != _ui("status.no_identifier", "sin identificador")
        annotating = alive and not testing and talking and has_local
        if annotating:
            local_box = _ui("flow.note", "anota")
        elif talking:
            local_box = _ui("flow.skip", "no entra")
        else:
            local_box = local_detail
        box(pad, y, col, box_h, _ui("flow.local", "Modelo local"), local_box, local_on or annotating)
        box(pad + col + 12, y, col, box_h, _ui("flow.grok", "Grok"), clip(f"{snap.get('model') or 'grok'} · {_ui('flow.grok_note', 'solo texto')}"), grok_on)
        down(pad + col / 2, ask_bottom, y, local_on or annotating)
        down(pad + col + 12 + col / 2, ask_bottom, y, grok_on)
        y += box_h + gap
        chip_w = (col - 8) / 3
        chip_h = max(58, box_h)
        chips = (
            (_ui("flow.stay", "Se queda"), _ui("flow.stay_note", ""), local_on),
            (_ui("flow.command", "Orden"), _ui("flow.command_note", ""), local_on),
            (_ui("flow.open", "Abre"), _ui("flow.open_note", ""), local_on),
        )
        for index, (title, detail, on) in enumerate(chips):
            box(pad + index * (chip_w + 4), y, chip_w, chip_h, title, detail, on, size=10)
        abre_x = pad + 2 * (chip_w + 4) + chip_w
        grok_x = pad + col + 12
        grok_mid = (y - gap - box_h) + box_h * 0.55
        canvas.create_line(
            abre_x - 4, y + 16, grok_x + 10, grok_mid,
            fill=AMBER if local_on else "#3a4656", width=2, arrow="last", arrowshape=(10, 12, 4),
        )
        down(pad + col + 12 + col / 2, y - gap, y, grok_on)
        box(
            grok_x, y, col, chip_h,
            _ui("flow.voice", "Voz"), clip(f"{voice_name} · {voice_lib}"), grok_on,
        )

    def _paint(self) -> None:
        try:
            snap = self.hub.brain.snapshot()
        except tk.TclError:
            return
        self.status_var.set(snap["status"])
        self.state_var.set(snap.get("banner") or _ui("status.banner_wait", "ESPERA"))
        kind = snap.get("banner_kind") or "wait"
        self.state_label.configure(fg={"talk": GREEN, "hear": GREEN, "pause": AMBER, "test": AMBER}.get(kind, TEAL))
        self._refresh_market_marks()
        self.detail_var.set(
            f"{snap['model']}  ·  {snap['effort']}  ·  {snap['voice']}  ·  {snap['recognizer']}  ·  {snap['identifier']}  ·  {snap['session']}  ·  {snap['volume']}%"
        )
        self._draw_flow(snap)
        if self.tray_ok and self.tray is not None:
            self.tray.set_tip(f"Grok Assistant — {_version_line()} — {snap['status']}")
        if self.debug_text is None:
            return
        shown = self.hub.brain.logs[-500:]
        if shown == self._debug_cache:
            return
        self._debug_cache = list(shown)
        self.debug_text.configure(state="normal")
        self.debug_text.delete("1.0", "end")
        for line in shown:
            self._insert_log(line)
        self.debug_text.configure(state="disabled")
        self.debug_text.see("end")

    def _insert_log(self, line: str) -> None:
        parts = line.split("  ", 2)
        if len(parts) == 3 and parts[1] in {"·", "¦"}:
            stamp, kind, rest = parts
            self.debug_text.insert("end", stamp + " ", "time")
            if kind == "¦":
                self.debug_text.insert("end", "  ¦-- " + rest.strip() + "\n", "sigue")
            else:
                self.debug_text.insert("end", rest.strip() + "\n")
            return
        older = line.split("  ", 3)
        if len(older) == 4 and older[2].strip() in {"oí", "sigue"}:
            stamp, mode, kind, rest = older[0], older[1].strip(), older[2].strip(), older[3]
            self.debug_text.insert("end", stamp + "  ", "time")
            self.debug_text.insert("end", mode.ljust(18), "mode")
            self.debug_text.insert("end", "  " + kind.ljust(6), "oi" if kind == "oí" else "sigue")
            self.debug_text.insert("end", rest.strip() + "\n")
            return
        older = line.split("  ", 2)
        if len(older) == 3 and older[1].strip() in {"oí", "sigue"}:
            stamp, kind, rest = older[0], older[1].strip(), older[2]
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
        self.pause_button.configure(text=self._pause_caption(False))
        self.simple_pause.configure(text=self._pause_caption(True))
        self._note("escucha en pausa" if self.user_paused else "vuelvo a escuchar")
        self._paint()

    def _ask(self, title: str) -> str | None:
        event = threading.Event()
        box: dict[str, str | None] = {"value": None}

        def show() -> None:
            box["value"] = simpledialog.askstring(title, _ui("dialog.password", "Contraseña:"), show="*", parent=self.root)
            event.set()

        self.ui.put(show)
        event.wait(timeout=180)
        return box["value"]

    def _quit(self, _icon, _item) -> None:
        self._closing = True
        self.jobs.put(("stop", ""))
        if self.dictation is not None:
            self.dictation.stop()
        if self.kroko is not None:
            self.kroko.stop()
        if self.offline is not None:
            self.offline.stop()
        self.music.stop()
        if self.tray is not None:
            self.tray.stop()
        self.root.after(0, self.root.destroy)
