from __future__ import annotations

from grok_assistant.ui.deps import *  # noqa: F401,F403


class MarketMixin:
    """The voice, ear, and model shop."""

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
        if offer.kind == "kws":
            return settings.wake_gate == "fonema" and offer.ready()
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

    def _show_market_action(self, offer: Offer, button: RoundButton, chip: RoundButton) -> None:
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
        from grok_assistant.house.marketplace import fetch_piper_index, piper_cached

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
        from grok_assistant.house.marketplace import extra_piper_offers

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
        window.configure(bg=look.bg)
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
        book = RoundNotebook(window)
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
            rows = [offer for offer in catalog if offer.kind == kind or (kind == "stt" and offer.kind == "kws")]
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
        from grok_assistant.house.marketplace import piper_cached

        head = tk.Frame(parent, bg=look.bg)
        head.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(
            head,
            text=_ui("market.more", "Más voces del catálogo Piper (rhasspy/piper-voices)."),
            bg=look.bg, fg=look.muted, font=("Segoe UI", 10), anchor="w",
        ).pack(fill="x")
        link = tk.Label(
            head,
            text="huggingface.co/rhasspy/piper-voices",
            bg=look.bg, fg=look.teal, cursor="hand2", font=("Segoe UI", 10, "underline"), anchor="w",
        )
        link.pack(fill="x")
        link.bind("<Button-1>", lambda _event: webbrowser.open("https://huggingface.co/rhasspy/piper-voices"))
        self._market_loading = tk.StringVar(value="" if piper_cached() else _ui("market.loading", "Busco más voces en el catálogo Piper…"))
        tk.Label(head, textvariable=self._market_loading, bg=look.bg, fg=look.muted, font=("Segoe UI", 10), anchor="w").pack(fill="x")

    def _scroll_page(self, page: ttk.Frame) -> tuple[tk.Canvas, ttk.Frame]:
        canvas = tk.Canvas(page, bg=look.bg, highlightthickness=0)
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
        row = tk.Frame(parent, bg=look.bg)
        row.pack(fill="x", padx=4, pady=1)
        ready = offer.ready()
        percent = tk.IntVar(value=100 if ready else 0)
        label = tk.StringVar(value="")
        side = tk.Frame(row, bg=look.bg)
        side.pack(side="right", padx=(6, 8))
        tk.Label(side, text=offer.size, bg=look.bg, fg=look.muted, font=("Segoe UI", 9), width=16, anchor="e").pack(side="left", padx=(0, 6))
        chip = RoundButton(
            side, text=_ui("market.used", "EN USO"),
            bg=look.green, fg=look.chip_ink, activebackground=look.green, activeforeground=look.chip_ink,
            font=("Segoe UI", 10, "bold"), width=12, padx=8, pady=4, hover=False,
        )
        button = RoundButton(side, width=12, padx=12, pady=5, font=("Segoe UI", 10))
        self._market_marks.append((offer, button, chip))
        if ready and self._offer_used(offer):
            chip.pack(side="left")
        else:
            button.pack(side="left")
        body = tk.Frame(row, bg=look.bg)
        body.pack(side="left", fill="x", expand=True, padx=(2, 4))
        tk.Label(body, text=self._offer_title(offer), bg=look.bg, fg=look.ink, font=("Segoe UI", 11), anchor="w").pack(fill="x")
        tk.Label(body, text=self._short_line(self._offer_detail(offer)), bg=look.bg, fg=look.muted, font=("Segoe UI", 9), anchor="w").pack(fill="x")
        bar = ttk.Progressbar(body, maximum=100, variable=percent, style="Market.Horizontal.TProgressbar")
        state = tk.Label(body, textvariable=label, bg=look.bg, fg=look.muted, font=("Segoe UI", 9), anchor="w")
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

    def _download_offer(self, offer: Offer, status: tk.StringVar, percent: tk.IntVar, label: tk.StringVar, button: RoundButton, bar: ttk.Progressbar, state: tk.Label | None = None) -> None:
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
        elif offer.kind == "kws":
            self.hub.brain.settings.wake_gate = "fonema"
            self.hub.brain.persist()
            self._sync_ear()
            if hasattr(self, "_paint_simple"):
                self._paint_simple()
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
