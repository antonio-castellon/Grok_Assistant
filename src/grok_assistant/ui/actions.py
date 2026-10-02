from __future__ import annotations

from grok_assistant.ui.deps import *  # noqa: F401,F403


class ActionMixin:
    """Menu commands, personality, about, and dialogs."""

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

    def _pick_identifier_file(self, filename: str) -> None:
        from grok_assistant.house.marketplace import offers

        for offer in offers():
            if offer.kind == "llm" and offer.files and offer.files[0][1].rsplit("/", 1)[-1] == filename:
                self._pick_identifier(offer)
                return

    def _ensure_identifier(self) -> None:
        if not self.hub.brain.settings.local_llm or self.hub.brain.settings.llm_file:
            return
        from grok_assistant.house.marketplace import offers

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

    def _toggle_test(self) -> None:
        # The same Escucha row turns the test on and off. It does not wait for a spoken "salir".
        self.jobs.put(("test", ""))

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
        window.configure(bg=look.bg)
        window.geometry("720x560")
        ttk.Label(window, text=_ui("dialog.commands_hint", "Un comando por línea: id = frase | frase"), style="Muted.TLabel").pack(anchor="w", padx=12, pady=8)
        box = tk.Text(window, wrap="word", bg=look.field, fg=look.ink, insertbackground=look.ink, font=look.mono, relief="flat", padx=10, pady=8)
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

        RoundButton(window, text=_ui("menu.apply", "Aplicar"), command=save, padx=18, pady=8).pack(anchor="e", padx=12, pady=(0, 12))

    def _edit_help(self) -> None:
        from grok_assistant.house.helptext import help_topics
        from grok_assistant.i18n import save_section

        window = tk.Toplevel(self.root)
        window.title(self.hub.brain.settings.language)
        window.configure(bg=look.bg)
        window.geometry("720x560")
        ttk.Label(
            window,
            text=_ui("dialog.help_hint", "Cada ayuda: título, luego example: ejemplo, luego el texto, y una línea ---"),
            style="Muted.TLabel",
        ).pack(anchor="w", padx=12, pady=8)
        box = tk.Text(window, wrap="word", bg=look.field, fg=look.ink, insertbackground=look.ink, font=look.font, relief="flat", padx=10, pady=8)
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

        RoundButton(window, text=_ui("menu.apply", "Aplicar"), command=save, padx=18, pady=8).pack(anchor="e", padx=12, pady=(0, 12))

    def _banter_set(self, key: str, enabled: bool | None = None, var=None) -> None:
        from grok_assistant.speaking.banter import KINDS, THEMES, apply_choice
        from grok_assistant.speaking.waits import STYLES

        head, item = key.split(":", 1)
        settings = self.hub.brain.settings
        if head == "banter-wait":
            allowed = STYLES
            current = list(settings.wait_styles)
            mix = item == "mix"
        elif head == "banter-kind":
            allowed = KINDS
            current = list(settings.line_kinds)
            mix = item == "mix"
        else:
            allowed = THEMES
            current = list(settings.line_themes)
            mix = False
        if enabled is None:
            enabled = (set(allowed) != set(current)) if mix else item not in current
        chosen = apply_choice(current, allowed, item, bool(enabled), mix=mix)
        if head == "banter-wait":
            settings.wait_styles = chosen
        elif head == "banter-kind":
            settings.line_kinds = chosen
        else:
            settings.line_themes = chosen
        if var is not None:
            var.set(set(allowed) <= set(chosen) if mix else item in chosen)
        self.hub.brain.persist()
        if head == "banter-wait":
            picked = ", ".join(_ui(f"wait.style.{name}", name) for name in STYLES if name in settings.wait_styles)
            self._note(f"{_ui('menu.banter_waits', 'Espera')}: {picked}.")
            return
        picked_kinds = ", ".join(_ui(f"banter.kind.{name}", name) for name in KINDS if name in settings.line_kinds)
        picked_themes = ", ".join(_ui(f"banter.theme.{name}", name) for name in THEMES if name in settings.line_themes)
        self._note(f"{_ui('menu.banter', 'Saludos')}: {picked_kinds}. {picked_themes}.")

    def _choose_person(self, person_id: str) -> None:
        from grok_assistant.house.personality import load_person, person_by_id

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
        from grok_assistant.house.personality import CULTURES, FORMALITY, TONES, TRAITS, VERBOSITY, persons

        window = tk.Toplevel(self.root)
        window.title(_ui("persona.title", "Personalidad"))
        window.configure(bg=look.bg)
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
        RoundButton(buttons, text=_ui("menu.restore", "Restaurar"), command=self._persona_restore, padx=18, pady=8).pack(side="right")
        RoundButton(buttons, text=_ui("menu.apply", "Aplicar"), command=self._persona_save, padx=18, pady=8).pack(side="right", padx=(0, 8))
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
                bg=look.bg, fg=look.ink, troughcolor=look.field, highlightthickness=0,
                activebackground=look.teal, length=640,
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
            inner, height=8, wrap="word", bg=look.field, fg=look.ink, insertbackground=look.ink,
            font=look.font, relief="flat", padx=10, pady=8,
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
        from grok_assistant.house.personality import load_person

        person_id = self._persona_ids.get(self._persona_choice.get(), "")
        self._persona_fill(load_person(person_id))

    def _persona_fill(self, raw) -> None:
        from grok_assistant.house.personality import normalize_personality, person_by_id

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
        from grok_assistant.house.personality import load_person, person_by_id

        person_id = self._persona_ids.get(self._persona_choice.get(), "")
        self._persona_fill(load_person(person_id, stock=True))
        self._persona_save(restored=True)

    def _persona_save(self, restored: bool = False) -> None:
        from grok_assistant.house.personality import normalize_personality, person_by_id

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
        window.configure(bg=look.bg)
        window.geometry("720x560")
        self._about_win = window
        book = RoundNotebook(window)
        book.pack(fill="both", expand=True, padx=12, pady=12)
        about = ttk.Frame(book)
        commands = ttk.Frame(book)
        license_page = ttk.Frame(book)
        book.add(about, text=_ui("about.title", "Acerca de"))
        book.add(commands, text=_ui("about.commands", "Comandos"))
        book.add(license_page, text=_ui("about.license_tab", "Licencia"))
        body = tk.Text(
            about, wrap="word", bg=look.field, fg=look.ink, font=("Segoe UI", 12),
            relief="flat", padx=18, pady=16, insertbackground=look.ink,
        )
        body.pack(fill="both", expand=True)
        body.tag_configure("name", font=("Segoe UI", 16, "bold"), foreground=look.amber, spacing3=6)
        body.tag_configure("quiet", foreground=look.muted, spacing3=10)
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
        body.insert("end", "\n\n" + _ui("about.experimental", "Esta aplicación es experimental."))
        body.bind("<Key>", lambda _event: "break")
        self._fill_commands(commands)
        self._fill_license(license_page)
        window.protocol("WM_DELETE_WINDOW", window.destroy)

    def _fill_license(self, parent: ttk.Frame) -> None:
        from grok_assistant.paths import license_text

        box = tk.Text(
            parent, wrap="word", bg=look.field, fg=look.ink, font=("Segoe UI", 12),
            relief="flat", padx=18, pady=16, insertbackground=look.ink,
        )
        box.pack(fill="both", expand=True)
        box.insert("end", license_text())
        box.bind("<Key>", lambda _event: "break")

    def _fill_commands(self, parent: ttk.Frame) -> None:
        box = tk.Text(
            parent, wrap="word", bg=look.field, fg=look.ink, font=("Segoe UI", 12),
            relief="flat", padx=18, pady=16, insertbackground=look.ink,
        )
        box.pack(fill="both", expand=True)
        box.tag_configure("title", font=("Segoe UI", 14, "bold"), foreground=look.amber, spacing1=14, spacing3=4)
        box.tag_configure("example", font=("Consolas", 12), foreground=look.teal, spacing3=8)
        box.insert("end", _ui("about.lead", "") + "\n")
        example_word = _ui("about.example", "Ejemplo")
        for title, body, example in help_topics():
            box.insert("end", title + "\n", "title")
            box.insert("end", body + "\n")
            box.insert("end", f"{example_word}: {example}\n", "example")
        box.configure(state="disabled")

    def _link_tag(self, text: tk.Text, tag: str, url: str) -> None:
        text.tag_configure(tag, foreground=look.teal, underline=True)
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
