from __future__ import annotations

import re

from grok_assistant.ui.deps import *  # noqa: F401,F403


class WindowMixin:
    """The main window and the Simple tab."""

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
        self._heard_box: queue.Queue = queue.Queue()
        self._mic_held = False
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
        self._update_offer = None
        voices = self.speaker.list_voices() or ["Predeterminada"]
        self.models = [self.hub.brain.settings.model]
        self.hub.brain.set_devices(voices, discover_recognizers())
        chosen = preferred_recognizer(self.hub.brain.settings.recognizer, self.hub.brain.recognizers)
        if chosen != self.hub.brain.settings.recognizer:
            self.hub.brain.settings.recognizer = chosen
            self.hub.brain.persist()
        self._choose_best_ear(False)
        apply_saved(self.hub.brain.settings.theme)
        self._style()
        self._build_window()

    def start(self) -> None:
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=self._heard_worker, daemon=True).start()
        threading.Thread(target=self._warm_mind, daemon=True).start()
        threading.Thread(target=self.hub.brain.agents.refresh_account, daemon=True).start()
        self.jobs.put(("startup", ""))
        self._start_tray()
        self._paint_tray_colors()
        self._sync_ear()
        self._ensure_identifier()
        self._poll_usage()
        threading.Thread(target=self._arm_voiceprint, daemon=True).start()
        threading.Thread(target=self._arm_refiner, daemon=True).start()
        threading.Thread(target=self._score_pending, daemon=True).start()
        threading.Thread(target=self._warm_piper, daemon=True).start()
        threading.Thread(target=self._check_updates, daemon=True).start()
        self._note("ventana lista")
        self._announce_combined()
        self.root.after(200, self._pulse)

    def _warm_mind(self) -> None:
        mind = self.hub.mind
        if mind is None or not self.hub.brain.settings.local_llm:
            return
        try:
            ready = mind.warm()
        except Exception:
            return
        if ready:
            self.ui.put(lambda: self._note("el modelo local ya está en memoria"))

    def _check_updates(self) -> None:
        try:
            from grok_assistant.house.updates import find_update

            offer = find_update()
        except Exception:
            return
        if not offer:
            return

        def show() -> None:
            self._update_offer = offer
            self._place_update_button()

        self.ui.put(show)

    def _place_update_button(self) -> None:
        button = getattr(self, "update_button", None)
        if button is None:
            return
        try:
            if not int(button.winfo_exists()):
                return
        except tk.TclError:
            return
        if not self._update_offer:
            try:
                button.pack_forget()
            except tk.TclError:
                pass
            return
        button.configure(text=_ui("window.update", "Actualizar"))
        if not button.winfo_ismapped():
            button.pack(side="right", padx=(0, 12), pady=6)

    def _confirm_update(self) -> None:
        offer = self._update_offer
        if not offer:
            return
        body = _ui(
            "dialog.update_body",
            "Hay una versión más nueva ({tag}). El programa se cerrará, se sustituirá y volverá a abrirse.",
        ).replace("{tag}", str(offer.get("tag") or ""))
        if not messagebox.askyesno(_ui("dialog.update_title", "Actualizar"), body, parent=self.root):
            return
        self.update_button.configure(state="disabled", text=_ui("window.updating", "Actualizando…"))

        def work() -> None:
            from grok_assistant.house.updates import apply_update

            try:
                ok = apply_update(offer)
            except Exception:
                ok = False
            if ok:
                self.ui.put(lambda: self._quit(None, None))
                return

            def fail() -> None:
                try:
                    self.update_button.configure(state="normal", text=_ui("window.update", "Actualizar"))
                except tk.TclError:
                    return
                messagebox.showerror(
                    _ui("dialog.update_title", "Actualizar"),
                    _ui("dialog.update_fail", "No se pudo actualizar."),
                    parent=self.root,
                )

            self.ui.put(fail)

        threading.Thread(target=work, daemon=True).start()

    def _style(self) -> None:
        self.root.configure(bg=look.bg)
        style = ttk.Style(self.root)
        try:
            if style.theme_use() != "clam":
                style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=look.bg, foreground=look.ink, font=look.font)
        style.configure("TFrame", background=look.bg)
        style.configure("Panel.TFrame", background=look.panel)
        style.configure("TLabel", background=look.bg, foreground=look.ink, font=look.font)
        style.configure("Muted.TLabel", background=look.bg, foreground=look.muted, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=look.bg, foreground=look.amber, font=look.font_bold)
        style.configure("TButton", background=look.button, foreground=look.ink, font=look.font, padding=(12, 6), borderwidth=0)
        style.map("TButton", background=[("active", look.button_active)])
        style.configure("Compact.TButton", background=look.button, foreground=look.ink, font=("Segoe UI", 10), padding=(10, 2), borderwidth=0)
        style.map("Compact.TButton", background=[("active", look.button_active)])
        style.configure("TEntry", fieldbackground=look.field, foreground=look.ink, insertcolor=look.ink, font=look.font)
        style.configure(
            "Simple.TCombobox",
            fieldbackground=look.field,
            background=look.panel,
            foreground=look.ink,
            arrowcolor=look.ink,
            borderwidth=0,
            padding=8,
            font=("Segoe UI", 16),
        )
        style.map(
            "Simple.TCombobox",
            fieldbackground=[("readonly", look.field)],
            foreground=[("readonly", look.ink)],
            selectbackground=[("readonly", look.field)],
            selectforeground=[("readonly", look.ink)],
        )
        style.configure("Market.TNotebook", background=look.bg, borderwidth=0)
        style.configure("Market.TNotebook.Tab", background=look.panel, foreground=look.ink, padding=(14, 8), font=("Segoe UI", 11))
        style.map("Market.TNotebook.Tab", background=[("selected", look.button_active)], foreground=[("selected", look.ink)])
        style.configure(
            "Market.Horizontal.TProgressbar",
            troughcolor=look.field,
            background=look.teal,
            bordercolor=look.field,
            lightcolor=look.teal,
            darkcolor=look.teal,
        )

    def _paint_tray_colors(self) -> None:
        if self.tray is None:
            return
        self.tray.set_palette(theme_by_id(self.hub.brain.settings.theme).menu_refs())

    def _apply_theme(self, theme_id: str) -> None:
        item = theme_by_id(theme_id)
        if item.id == self.hub.brain.settings.theme and look.id == item.id:
            return
        self.hub.brain.settings.theme = item.id
        self.hub.brain.persist()
        apply_saved(item.id)
        if self.tray is not None:
            self.tray.set_palette(item.menu_refs())
        self._note(f"aspecto {item.name}")
        self.root.after(0, self._restyle)

    def _restyle(self) -> None:
        for attr in ("_persona_win", "_about_win", "_market_win", "_print_win"):
            self._drop_window(attr)
        self._debug_cache = []
        self.debug_text = None
        self.flow = None
        # The menu bar is one of the children. Detach it, then destroy once.
        try:
            self.root.configure(menu="")
        except tk.TclError:
            pass
        for child in list(self.root.winfo_children()):
            try:
                child.destroy()
            except tk.TclError:
                pass
        self._style()
        self._build_window(place=False)
        self._paint()

    def _paint_detail(self, *_args) -> None:
        widget = getattr(self, "detail_label", None)
        if widget is None:
            return
        try:
            if not int(widget.winfo_exists()):
                return
        except tk.TclError:
            return
        raw = self.detail_var.get()
        widget.delete("1.0", "end")
        cursor = 0
        for match in re.finditer(r"\[([^\]]*)\]", raw):
            widget.insert("end", raw[cursor:match.start()])
            widget.insert("end", "[")
            widget.insert("end", match.group(1), "value")
            widget.insert("end", "]")
            cursor = match.end()
        if cursor < len(raw):
            widget.insert("end", raw[cursor:])

    def _build_window(self, place: bool = True) -> None:
        self.root.title("Grok Assistant")
        if place:
            self.root.geometry("980x760")
        self.root.minsize(720, 560)
        icon = bundle_root() / "docs" / "img" / "grok.ico"
        if icon.exists():
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass
        self.root.protocol("WM_DELETE_WINDOW", self._hide)

        self.chrome = tk.Frame(self.root, bg=look.panel)
        self.chrome.pack(fill="x")
        head = tk.Frame(self.chrome, bg=look.panel)
        head.pack(fill="x", padx=18, pady=(10, 0))
        corner = tk.Frame(head, bg=look.panel)
        corner.pack(side="right", anchor="n")
        left = tk.Frame(head, bg=look.panel)
        left.pack(side="left", fill="both", expand=True)
        self.detail_label = tk.Text(
            left, height=3, width=1, wrap="word", bg=look.panel, fg=look.muted,
            font=("Segoe UI", 11), relief="flat", borderwidth=0, highlightthickness=0,
            padx=0, pady=0, cursor="arrow", takefocus=0, insertwidth=0,
        )
        self.detail_label.pack(anchor="nw", fill="x")
        self.detail_label.tag_configure("value", font=("Segoe UI", 11, "bold"), foreground=look.ink)
        self.detail_label.bind("<Key>", lambda _event: "break")
        if not getattr(self, "_detail_traced", False):
            self.detail_var.trace_add("write", self._paint_detail)
            self._detail_traced = True
        self._paint_detail()
        self.state_var = tk.StringVar(value=_ui("status.banner_wait", "ESPERA"))
        self.state_label = tk.Label(
            corner, textvariable=self.state_var, bg=look.panel, fg=look.teal, font=("Segoe UI", 26, "bold"),
        )
        self.state_label.pack(anchor="e")
        self.usage_label = tk.Label(corner, textvariable=self.usage_var, bg=look.panel, fg=look.muted, font=("Segoe UI", 12, "bold"))
        self.usage_label.pack(anchor="e")

        self.footer = tk.Frame(self.root, bg=look.panel, height=46)
        self.footer.pack(side="bottom", fill="x")
        self.footer.pack_propagate(False)
        self.version_label = tk.Label(
            self.footer, text=_version_line(), bg=look.panel, fg=look.ink,
            font=("Segoe UI", 12), anchor="w",
        )
        self.version_label.pack(fill="both", padx=18)
        self.update_button = RoundButton(
            self.footer, text=_ui("window.update", "Actualizar"), command=self._confirm_update,
            bg=look.button, fg=look.ink, activebackground=look.button_active, activeforeground=look.ink,
            font=("Segoe UI", 11), padx=16, pady=4,
        )
        self._place_update_button()

        self.pages = RoundNotebook(self.root, bar_parent=self.chrome)
        self.pages.pack(fill="both", expand=True, padx=18, pady=(8, 8))
        self.page_simple = tk.Frame(self.pages, bg=look.bg, highlightthickness=0, bd=0)
        self.page_debug = tk.Frame(self.pages, bg=look.bg, highlightthickness=0, bd=0)
        self.page_flow = tk.Frame(self.pages, bg=look.bg, highlightthickness=0, bd=0)
        self.pages.add(self.page_simple, text=_ui("window.tab_simple", "Simple"))
        self.pages.add(self.page_debug, text=_ui("window.tab_debug", "Depuración"))
        self.pages.add(self.page_flow, text=_ui("window.tab_flow", "Flujo"))
        self.pages.select(self.page_simple)

        simple = tk.Frame(self.page_simple, bg=look.bg)
        simple.pack(expand=True)
        mode_row = tk.Frame(simple, bg=look.bg)
        mode_row.pack(pady=(0, 10))
        self.talk_label = tk.Label(
            mode_row, text="", bg=look.bg, fg=look.muted, font=("Segoe UI", 14),
        )
        self.talk_label.pack(anchor="center")
        self.talk_mode_box = ttk.Combobox(
            mode_row, state="readonly", width=26, style="Simple.TCombobox", font=("Segoe UI", 16),
        )
        self.talk_mode_box.pack(pady=(8, 0))
        self.talk_mode_box.bind("<<ComboboxSelected>>", self._pick_talk_mode)
        row = tk.Frame(simple, bg=look.bg)
        row.pack()
        big = {"font": ("Segoe UI", 28, "bold"), "padx": 48, "pady": 28}
        self.simple_pause = RoundButton(
            row, text=_ui("window.big_pause", "Pausar"), command=self._toggle_from_ui,
            bg=look.pause, fg=look.teal, activebackground=look.pause_active, activeforeground=look.teal, **big,
        )
        self.simple_pause.pack(side="left", padx=14)
        self.simple_quit = RoundButton(
            row, text=_ui("window.big_quit", "Salir"), command=lambda: self._quit(None, None),
            bg=look.quit, fg=look.amber, activebackground=look.quit_active, activeforeground=look.amber, **big,
        )
        self.simple_quit.pack(side="left", padx=14)
        self.talk_hint = tk.Label(
            simple, text="", wraplength=680, justify="center",
            bg=look.bg, fg=look.ink, font=("Segoe UI", 13),
        )
        self.talk_hint.pack(pady=(14, 4))
        settings_row = tk.Frame(simple, bg=look.bg)
        settings_row.pack(pady=(8, 0))
        # One row per band: a caption that wraps must not drop its spinbox.
        settings_row.columnconfigure(0, weight=1, uniform="pair")
        settings_row.columnconfigure(1, weight=1, uniform="pair")
        self.shared_label = tk.Label(
            settings_row, text="", bg=look.bg, fg=look.muted, font=("Segoe UI", 13),
            wraplength=300, justify="center",
        )
        self.shared_label.grid(row=0, column=0, sticky="s", padx=22)
        days_row = tk.Frame(settings_row, bg=look.bg)
        days_row.grid(row=1, column=0, pady=(6, 0))
        self.shared_days_var = tk.StringVar(value=str(self.hub.brain.settings.shared_days))
        self.shared_days_box = tk.Spinbox(
            days_row, from_=1, to=365, width=4, textvariable=self.shared_days_var,
            command=self._pick_shared_days, justify="center",
            font=("Segoe UI", 18), bg=look.field, fg=look.ink, buttonbackground=look.panel,
            insertbackground=look.ink, relief="flat", highlightthickness=1, highlightbackground=look.teal,
        )
        self.shared_days_box.pack(side="left")
        self.shared_days_box.bind("<FocusOut>", lambda _event: self._pick_shared_days())
        self.shared_days_box.bind("<Return>", lambda _event: self._pick_shared_days())
        self.shared_unit = tk.Label(days_row, text="", bg=look.bg, fg=look.ink, font=("Segoe UI", 16))
        self.shared_unit.pack(side="left", padx=(10, 0))
        self.days_hint = tk.Label(
            settings_row, text="", wraplength=300, justify="center",
            bg=look.bg, fg=look.muted, font=("Segoe UI", 12),
        )
        self.days_hint.grid(row=2, column=0, sticky="n", padx=22, pady=(8, 0))
        self.quiet_label = tk.Label(
            settings_row, text="", bg=look.bg, fg=look.muted, font=("Segoe UI", 13),
            wraplength=300, justify="center",
        )
        self.quiet_label.grid(row=0, column=1, sticky="s", padx=22)
        quiet_row = tk.Frame(settings_row, bg=look.bg)
        quiet_row.grid(row=1, column=1, pady=(6, 0))
        from grok_assistant.notebook.settings import format_quiet_minutes

        self.quiet_minutes_var = tk.StringVar(value=format_quiet_minutes(self.hub.brain.settings.quiet_minutes))
        self.quiet_minutes_box = tk.Spinbox(
            quiet_row, from_=0.1, to=60, increment=0.1, width=5, textvariable=self.quiet_minutes_var,
            command=self._pick_quiet_minutes, justify="center",
            font=("Segoe UI", 18), bg=look.field, fg=look.ink, buttonbackground=look.panel,
            insertbackground=look.ink, relief="flat", highlightthickness=1, highlightbackground=look.teal,
        )
        self.quiet_minutes_box.pack(side="left")
        self.quiet_minutes_box.bind("<FocusOut>", lambda _event: self._pick_quiet_minutes())
        self.quiet_minutes_box.bind("<Return>", lambda _event: self._pick_quiet_minutes())
        self.quiet_unit = tk.Label(quiet_row, text="", bg=look.bg, fg=look.ink, font=("Segoe UI", 16))
        self.quiet_unit.pack(side="left", padx=(10, 0))
        self.quiet_hint = tk.Label(
            settings_row, text="", wraplength=300, justify="center",
            bg=look.bg, fg=look.muted, font=("Segoe UI", 12),
        )
        self.quiet_hint.grid(row=2, column=1, sticky="n", padx=22, pady=(8, 0))
        self._paint_simple()

        self.debug_label = ttk.Label(self.page_debug, text=_ui("window.debug", "Depuración — lo que oye y lo que hace después"), style="Muted.TLabel")
        self.debug_label.pack(anchor="w", padx=12, pady=(12, 4))
        log_wrap = tk.Frame(self.page_debug, bg=look.panel, padx=1, pady=1)
        log_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.debug_text = tk.Text(
            log_wrap, height=18, wrap="word", bg=look.field, fg=look.ink, insertbackground=look.ink,
            font=look.mono, relief="flat", padx=12, pady=10, borderwidth=0,
        )
        self.debug_text.pack(fill="both", expand=True)
        self.debug_text.tag_configure("time", foreground=look.time)
        self.debug_text.tag_configure("mode", foreground=look.mode_ink)
        self.debug_text.tag_configure("oi", foreground=look.amber)
        self.debug_text.tag_configure("sigue", foreground=look.teal)
        self.debug_text.configure(state="disabled")

        bar = ttk.Frame(self.page_debug)
        bar.pack(fill="x", padx=12, pady=(0, 8))
        self.entry = ttk.Entry(bar)
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry.bind("<Return>", self._send)
        self.send_button = RoundButton(bar, text=_ui("window.send", "Enviar"), command=self._send, padx=18, pady=8)
        self.send_button.pack(side="left", padx=(8, 0))

        actions = ttk.Frame(self.page_debug)
        actions.pack(fill="x", padx=12, pady=(0, 12))
        self.pause_button = RoundButton(actions, text=_ui("menu.pause", "Pausar escucha"), command=self._toggle_from_ui, padx=18, pady=8)
        self.pause_button.pack(side="left")
        self.clear_button = RoundButton(actions, text=_ui("window.clear", "Limpiar registro"), command=self._clear_view, padx=18, pady=8)
        self.clear_button.pack(side="left", padx=8)
        self.trace_button = RoundButton(
            actions, text=_ui("window.trace", "Guardar traza"), command=self._save_trace, padx=18, pady=8,
        )
        self.trace_button.pack(side="left", padx=(8, 0))
        self.trace_hint = ttk.Label(
            actions, text=_ui("window.trace_hint", "Audio oído, modelo local y decisiones"), style="Muted.TLabel",
        )
        self.trace_hint.pack(side="left", padx=(12, 0))
        self.quit_button = RoundButton(actions, text=_ui("menu.quit", "Salir"), command=lambda: self._quit(None, None), padx=18, pady=8)
        self.quit_button.pack(side="right")

        self.flow = tk.Canvas(self.page_flow, bg=look.bg, highlightthickness=0)
        self.flow.pack(fill="both", expand=True)
        self._flow_snap = None
        self.flow.bind("<Configure>", lambda _event: self._draw_flow(None))
        self._build_menus()

    def _talk_choices(self) -> list[tuple[str, str]]:
        return [
            ("seguida", _ui("window.mode_seguida", "Pregunta seguida")),
            ("saludo", _ui("window.mode_saludo", "Primero el saludo")),
            ("abierta", _ui("window.mode_abierta", "Charla abierta")),
        ]

    def _paint_simple(self) -> None:
        if not hasattr(self, "talk_mode_box"):
            return
        choices = self._talk_choices()
        self._talk_ids = {label: mode for mode, label in choices}
        self.talk_label.configure(text=_ui("window.talk_label", "Forma de hablar"))
        self.talk_mode_box.configure(values=[label for _mode, label in choices])
        current = self.hub.brain.settings.talk_mode
        shown = next((label for mode, label in choices if mode == current), choices[0][1])
        self._painting_simple = True
        try:
            self.talk_mode_box.set(shown)
        finally:
            self._painting_simple = False
        name = " ".join(str(self.hub.brain.settings.wake_name or "Grok").split()) or "Grok"
        banner = _ui("status.banner_talk", "EN CONVERSACIÓN")
        hint_key = {
            "seguida": "window.hint_seguida",
            "saludo": "window.hint_saludo",
            "abierta": "window.hint_abierta",
        }.get(current, "window.hint_seguida")
        fallback = {
            "seguida": "Di «Hola {name}» y la pregunta en la misma frase. Por ejemplo: «Hola {name}, ¿qué hora es?». Al callar, responde. Es la forma más rápida.",
            "saludo": "Di «Hola {name}» y espera a que conteste. Luego haz la pregunta, sin repetir el nombre. Si paras un momento después del nombre, el micrófono sigue por si la pregunta viene detrás.",
            "abierta": "Di «Hola {name}» para abrir. Mientras la esquina diga {banner}, pregunta cuando quieras, sin el nombre. Se cierra con gracias, vale u ok, o cuando el silencio llega a los minutos de abajo.",
        }[current if current in {"seguida", "saludo", "abierta"} else "seguida"]
        self.talk_hint.configure(text=_ui(hint_key, fallback).replace("{name}", name).replace("{banner}", banner))
        self.shared_label.configure(text=_ui("window.shared_label", "Días que se recuerdan las conversaciones"))
        self.shared_unit.configure(text=_ui("window.shared_unit", "días"))
        self.days_hint.configure(text=_ui(
            "window.hint_days",
            "El cuaderno guarda como máximo estos días hacia atrás. Entra el día nuevo y sale el más antiguo. Una sesión con nombre no caduca.",
        ))
        self.quiet_label.configure(text=_ui("window.quiet_label", "Minutos de silencio para cerrar"))
        self.quiet_unit.configure(text=_ui("window.quiet_unit", "min"))
        self.quiet_hint.configure(text=_ui(
            "window.hint_quiet",
            "Si nadie habla durante estos minutos, la charla se cierra sola. Gracias, vale u ok gracias también la cierran.",
        ))
        shown_days = str(self.hub.brain.settings.shared_days)
        try:
            editing = self.shared_days_box.focus_get() is self.shared_days_box
        except tk.TclError:
            editing = False
        if not editing and self.shared_days_var.get() != shown_days:
            self.shared_days_var.set(shown_days)
        from grok_assistant.notebook.settings import format_quiet_minutes

        shown_quiet = format_quiet_minutes(self.hub.brain.settings.quiet_minutes)
        try:
            editing_quiet = self.quiet_minutes_box.focus_get() is self.quiet_minutes_box
        except tk.TclError:
            editing_quiet = False
        if not editing_quiet and self.quiet_minutes_var.get() != shown_quiet:
            self.quiet_minutes_var.set(shown_quiet)

    def _pick_talk_mode(self, _event=None) -> None:
        if getattr(self, "_painting_simple", False):
            return
        mode = self._talk_ids.get(self.talk_mode_box.get(), "seguida")
        if self.hub.brain.settings.talk_mode != mode:
            self.hub.brain.settings.talk_mode = mode
            self.hub.brain.persist()
        self._paint_simple()
        self._draw_flow(None)

    def _phrase_silence(self) -> float:
        from grok_assistant.rules.match import GREETING_QUIET, PHRASE_QUIET

        brain = self.hub.brain
        if brain.settings.talk_mode == "saludo" and not brain.in_conversation:
            return GREETING_QUIET
        return PHRASE_QUIET

    def _pick_shared_days(self) -> None:
        from grok_assistant.notebook.settings import normalize_shared_days

        days = normalize_shared_days(self.shared_days_var.get())
        if self.shared_days_var.get() != str(days):
            self.shared_days_var.set(str(days))
        settings = self.hub.brain.settings
        if settings.shared_days != days:
            settings.shared_days = days
            self.hub.brain.persist()
        self.hub.brain.sessions.roll(self.hub.brain.wall(), days)

    def _pick_quiet_minutes(self) -> None:
        from grok_assistant.notebook.settings import format_quiet_minutes, normalize_quiet_minutes

        minutes = normalize_quiet_minutes(self.quiet_minutes_var.get())
        shown = format_quiet_minutes(minutes)
        if self.quiet_minutes_var.get() != shown:
            self.quiet_minutes_var.set(shown)
        settings = self.hub.brain.settings
        if settings.quiet_minutes != minutes:
            settings.quiet_minutes = minutes
            self.hub.brain.persist()

    def _save_trace(self) -> None:
        from grok_assistant.house.tracepack import save_trace

        try:
            path = save_trace(self.hub.brain, self.hub.sent, self.hub.data_dir)
        except Exception:
            self.hub.brain.note(_ui("window.trace_failed", "No pude guardar la traza."))
        else:
            shown = _ui("window.trace_saved", "Traza guardada: {path}").replace("{path}", str(path))
            self.hub.brain.note(shown)
            self._show_trace(path)
        if hasattr(self, "_refresh"):
            self._refresh()

    def _show_trace(self, path) -> None:
        import subprocess

        if os.name != "nt":
            return
        try:
            subprocess.Popen(["explorer", f"/select,{path}"])
        except OSError:
            return

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
        self.trace_button.configure(text=_ui("window.trace", "Guardar traza"))
        self.trace_hint.configure(text=_ui("window.trace_hint", "Audio oído, modelo local y decisiones"))
        self.clear_button.configure(text=_ui("window.clear", "Limpiar registro"))
        quit_label = _ui("menu.quit", "Salir")
        self.quit_button.configure(text=quit_label)
        self.simple_quit.configure(text=_ui("window.big_quit", "Salir"))
        if getattr(self, "update_button", None) is not None:
            self.update_button.configure(text=_ui("window.update", "Actualizar"))
        self.pause_button.configure(text=self._pause_caption(False))
        self.simple_pause.configure(text=self._pause_caption(True))
        self._paint_simple()
        self._draw_flow(None)
        self._show_usage()

    def _show_usage(self) -> None:
        try:
            if not self._usage_known:
                self.usage_var.set(_ui("window.account", "cuenta {n}%").replace("{n}", "…"))
                self.usage_label.configure(fg=look.muted)
                return
            percent = self._usage_percent
            if percent is None:
                self.usage_var.set(_ui("window.no_account", "sin cuenta"))
                self.usage_label.configure(fg=look.muted)
                return
            self.usage_var.set(_ui("window.account", "cuenta {n}%").replace("{n}", str(percent)))
            if percent >= 90:
                color = look.danger
            elif percent >= 70:
                color = look.amber
            else:
                color = look.teal
            self.usage_label.configure(fg=color)
        except tk.TclError:
            return
