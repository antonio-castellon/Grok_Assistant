from __future__ import annotations

from grok_assistant.ui.deps import *  # noqa: F401,F403


class MenuMixin:
    """The window bar and the tray menu."""

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
            "bg": look.panel,
            "fg": look.ink,
            "activebackground": look.button_active,
            "activeforeground": look.ink,
            "font": ("Segoe UI", 11),
            "selectcolor": look.select,
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
        self.menu_banter_waits = tk.Menu(self.menu_banter, postcommand=self._fill_banter_waits, **kw)
        self.menu_talk = tk.Menu(bar, **kw)
        self.menu_musica = tk.Menu(bar, **kw)
        self.menu_people = tk.Menu(bar, postcommand=self._fill_people, **kw)
        self.menu_prints = tk.Menu(self.menu_people, postcommand=self._fill_prints, **kw)
        self.menu_settings = tk.Menu(bar, postcommand=self._fill_settings, **kw)
        self.menu_language = tk.Menu(self.menu_settings, postcommand=self._fill_language, **kw)
        self.menu_theme = tk.Menu(self.menu_settings, postcommand=self._fill_theme, **kw)
        self.menu_microphone = tk.Menu(self.menu_settings, postcommand=self._fill_microphone, **kw)
        self.menu_output = tk.Menu(self.menu_settings, postcommand=self._fill_output, **kw)
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
        self.menu_banter.add_cascade(label=text("menu.banter_waits", "Espera"), menu=self.menu_banter_waits)
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
        menu.add_cascade(label=_ui("menu.theme", "Aspecto"), menu=self.menu_theme)
        menu.add_cascade(label=_ui("menu.microphone", "Micrófono"), menu=self.menu_microphone)
        menu.add_cascade(label=_ui("menu.output", "Altavoz"), menu=self.menu_output)
        menu.add_command(label=_ui("menu.market", "Voice market"), command=self._open_market)
        menu.add_separator()
        if enabled():
            menu.add_command(label=_used(True) + _ui("menu.startup_off", "Desactivar arranque con Windows"), command=self._toggle_startup)
        else:
            menu.add_command(label=_ui("menu.startup_on", "Activar arranque con Windows"), command=self._toggle_startup)
        menu.add_separator()
        menu.add_command(label=_ui("menu.admin_mode", "Modo administrador"), command=lambda: self._command("modo administrador"))
        menu.add_command(label=_ui("menu.password", "Contraseña…"), command=self._password_dialog)
        menu.add_separator()
        files = bool(self.hub.brain.settings.grok_files)
        menu.add_command(
            label=_used(not files) + _ui("menu.files_off", "Grok solo busca en internet"),
            command=lambda: self.jobs.put(("files", "0")),
        )
        menu.add_command(
            label=_used(files) + _ui("menu.files_on", "Grok puede cambiar archivos de esta máquina"),
            command=lambda: self.jobs.put(("files", "1")),
        )

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
        from grok_assistant.listening.listen import RECOGNIZER_LABELS

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
        from grok_assistant.house.marketplace import offers

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
        from grok_assistant.house.marketplace import offers

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
                    ("sub", text("menu.banter_waits", "Espera"), self._wait_rows()),
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
                ("sub", text("menu.theme", "Aspecto"), self._theme_rows()),
                ("sub", text("menu.microphone", "Micrófono"), self._microphone_rows()),
                ("sub", text("menu.output", "Altavoz"), self._output_rows()),
                ("cmd", text("menu.market", "Voice market"), "market", False),
                ("sep",),
                ("cmd", _ui("menu.startup_off", "Desactivar arranque con Windows") if self._startup_on() else _ui("menu.startup_on", "Activar arranque con Windows"), "startup", self._startup_on()),
                ("sep",),
                ("cmd", _ui("menu.admin_mode", "Modo administrador"), "admin", False),
                ("cmd", _ui("menu.password", "Contraseña…"), "password", False),
                ("sep",),
                ("cmd", _ui("menu.files_off", "Grok solo busca en internet"), "files-off", not brain.settings.grok_files),
                ("cmd", _ui("menu.files_on", "Grok puede cambiar archivos de esta máquina"), "files-on", bool(brain.settings.grok_files)),
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
        elif key.startswith("theme:"):
            self._apply_theme(key.split(":", 1)[1])
        elif key == "mic-default":
            self._pick_microphone("")
        elif key.startswith("mic:"):
            self._pick_microphone(key.split(":", 1)[1])
        elif key == "out-default":
            self._pick_output("")
        elif key.startswith("out:"):
            self._pick_output(key.split(":", 1)[1])
        elif key == "files-off":
            self.jobs.put(("files", "0"))
        elif key == "files-on":
            self.jobs.put(("files", "1"))
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

    def _fill_persona(self) -> None:
        from grok_assistant.house.personality import persons

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

    def _fill_theme(self) -> None:
        menu = self.menu_theme
        menu.delete(0, "end")
        current = self.hub.brain.settings.theme
        for item in available():
            menu.add_command(
                label=_used(item.id == current) + item.name,
                command=lambda picked=item.id: self._apply_theme(picked),
            )

    def _theme_rows(self) -> list:
        current = self.hub.brain.settings.theme
        return [("cmd", item.name, f"theme:{item.id}", item.id == current) for item in available()]

    def _microphone_names(self) -> tuple[str, list[str]]:
        from grok_assistant.listening.devices import listed_inputs, normalize_microphone

        current = normalize_microphone(self.hub.brain.settings.microphone)
        mics = listed_inputs() or []
        names = [mic["name"] for mic in mics]
        if current not in names:
            current = ""
        return current, names

    def _fill_microphone(self) -> None:
        menu = self.menu_microphone
        menu.delete(0, "end")
        current, names = self._microphone_names()
        menu.add_command(
            label=_used(current == "") + _ui("menu.microphone_default", "Predeterminado"),
            command=lambda: self._pick_microphone(""),
        )
        if not names:
            menu.add_command(label=_ui("menu.microphone_none", "No hay micrófonos"), state="disabled")
            return
        menu.add_separator()
        for name in names:
            menu.add_command(
                label=_used(name == current) + name,
                command=lambda picked=name: self._pick_microphone(picked),
            )

    def _microphone_rows(self) -> list:
        current, names = self._microphone_names()
        rows = [("cmd", _ui("menu.microphone_default", "Predeterminado"), "mic-default", current == "")]
        if not names:
            rows.append(("cmd", _ui("menu.microphone_none", "No hay micrófonos"), "noop", False))
            return rows
        rows.append(("sep",))
        for name in names:
            rows.append(("cmd", name, f"mic:{name}", name == current))
        return rows

    def _pick_microphone(self, name: str) -> None:
        from grok_assistant.listening.devices import normalize_microphone

        chosen = normalize_microphone(name)
        if chosen == normalize_microphone(self.hub.brain.settings.microphone):
            return
        self.hub.brain.settings.microphone = chosen
        self.hub.brain.persist()
        self._sync_ear()
        shown = chosen or _ui("menu.microphone_default", "Predeterminado")
        self._note(f"micrófono: {shown}")
        if hasattr(self, "_paint"):
            self._paint()

    def _output_names(self) -> tuple[str, list[str]]:
        from grok_assistant.listening.devices import listed_outputs, normalize_device

        current = normalize_device(self.hub.brain.settings.output)
        speakers = listed_outputs() or []
        names = [row["name"] for row in speakers]
        if current not in names:
            current = ""
        return current, names

    def _fill_output(self) -> None:
        menu = self.menu_output
        menu.delete(0, "end")
        current, names = self._output_names()
        menu.add_command(
            label=_used(current == "") + _ui("menu.output_default", "Predeterminado"),
            command=lambda: self._pick_output(""),
        )
        if not names:
            menu.add_command(label=_ui("menu.output_none", "No hay altavoces"), state="disabled")
            return
        menu.add_separator()
        for name in names:
            menu.add_command(
                label=_used(name == current) + name,
                command=lambda picked=name: self._pick_output(picked),
            )

    def _output_rows(self) -> list:
        current, names = self._output_names()
        rows = [("cmd", _ui("menu.output_default", "Predeterminado"), "out-default", current == "")]
        if not names:
            rows.append(("cmd", _ui("menu.output_none", "No hay altavoces"), "noop", False))
            return rows
        rows.append(("sep",))
        for name in names:
            rows.append(("cmd", name, f"out:{name}", name == current))
        return rows

    def _pick_output(self, name: str) -> None:
        from grok_assistant.listening.devices import normalize_device

        chosen = normalize_device(name)
        if chosen == normalize_device(self.hub.brain.settings.output):
            return
        self.hub.brain.settings.output = chosen
        self.hub.brain.persist()
        shown = chosen or _ui("menu.output_default", "Predeterminado")
        self._note(f"altavoz: {shown}")
        if hasattr(self, "_paint"):
            self._paint()

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

    def _banter_kind_rows(self) -> list:
        from grok_assistant.speaking.banter import KINDS

        selected = set(self.hub.brain.settings.line_kinds)
        rows = [
            ("cmd", _ui(f"banter.kind.{kind}", kind), f"banter-kind:{kind}", kind in selected)
            for kind in KINDS
        ]
        rows.append(("sep",))
        rows.append(("cmd", _ui("banter.kind.mix", "Mezcla de todo"), "banter-kind:mix", set(KINDS) <= selected))
        return rows

    def _banter_theme_rows(self) -> list:
        from grok_assistant.speaking.banter import THEMES

        selected = set(self.hub.brain.settings.line_themes)
        return [
            ("cmd", _ui(f"banter.theme.{theme}", theme), f"banter-theme:{theme}", theme in selected)
            for theme in THEMES
        ]

    def _wait_rows(self) -> list:
        from grok_assistant.speaking.waits import STYLES

        selected = set(self.hub.brain.settings.wait_styles)
        rows = [
            ("cmd", _ui(f"wait.style.{style}", style), f"banter-wait:{style}", style in selected)
            for style in STYLES
        ]
        rows.append(("sep",))
        rows.append(("cmd", _ui("wait.style.mix", "Mezcla de todo"), "banter-wait:mix", set(STYLES) <= selected))
        return rows

    def _fill_banter_kinds(self) -> None:
        self._fill_checks(self.menu_banter_kinds, self._banter_kind_rows())

    def _fill_banter_themes(self) -> None:
        self._fill_checks(self.menu_banter_themes, self._banter_theme_rows())

    def _fill_banter_waits(self) -> None:
        self._fill_checks(self.menu_banter_waits, self._wait_rows())

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

    def _persona_items(self) -> list:
        from grok_assistant.house.personality import persons

        current = str(self.hub.brain.settings.personality.get("profile") or "")
        rows = [("cmd", _ui("persona.none", "Sin persona — la voz de siempre"), "persona:", not current)]
        for person in persons():
            rows.append(("cmd", f"{person.name} — {person.label}", f"persona:{person.id}", person.id == current))
        rows.append(("sep",))
        rows.append(("cmd", _ui("persona.adjust", "Ajustar rasgos y comportamiento…"), "persona-edit", False))
        return rows
