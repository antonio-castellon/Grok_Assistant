from __future__ import annotations

from grok_assistant.rules.common import *  # noqa: F401,F403


class OrderMixin:
    """Local commands: volume, music, sessions, agents."""

    def _converse_job(self, text: str, effort: str) -> Job:
        if self.agents.active:
            record = self.agents.resolve(self.agents.active)
            if record is None:
                self.agents.close()
            else:
                return Job("converse", text, effort, record.name, str(record.path), "agent")
        return Job("converse", text, effort, slot="session")

    def _review(self, heard: str) -> Turn:
        self._record(heard, "ignorar", False, "revisa el modelo local")
        self.last_heard = heard
        return Turn(job=Job("review", heard), status=self.status_label())

    def perform(self, hit: Hit) -> Turn:
        if hit.confirm:
            self.pending = ("yesno", hit)
            return self._said([self._confirm(hit)])
        if hit.admin and not self.is_admin():
            if not self.auth.is_set:
                return self._said(["Primero elige una contraseña de administrador en el menú."])
            self.pending = ("password", hit)
            return Turn(speak=["Hace falta el modo administrador."], effects=[("ask_password",)], status=self.status_label())
        return self._run(hit)

    def _order(self, heard: str, body: list[tuple[str, str]], full_len: int) -> Turn:
        norms = [norm for _, norm in body]
        if ("agente" in norms or "agentes" in norms) and full_len > 8:
            phrase = " ".join(raw for raw, _ in body)
            self._record(heard, "comando", True, "a clasificar")
            self.phase = text("status.interpret", "Interpretando … buscando en la nube")
            return Turn(speak=[], job=Job("classify", phrase), status=self.phase)
        hit = parse_order(body)
        if hit is None:
            phrase = " ".join(raw for raw, _ in body)
            self._record(heard, "comando", True, "a clasificar")
            self.last_heard = heard
            self.phase = text("status.interpret", "Interpretando … buscando en la nube")
            return Turn(speak=[], job=Job("classify", phrase), status=self.phase)
        self.last_heard = heard
        if hit.strict == "prueba":
            return self._enter_test(heard)
        if self._arg_missing(hit):
            self._record(heard, "comando", False, hit.strict)
            return self._said([self._missing(hit)])
        if hit.confirm:
            self.pending = ("yesno", hit)
            self._record(heard, "comando", False, f"{display_order(hit)} (a confirmar)")
            return self._said([self._confirm(hit)])
        if hit.admin and not self.is_admin():
            self._record(heard, "comando", False, hit.strict)
            if not self.auth.is_set:
                return self._said(["Primero elige una contraseña de administrador en el menú."])
            self.pending = ("password", hit)
            return Turn(
                speak=["Hace falta el modo administrador."],
                effects=[("ask_password",)],
                status=self.status_label(),
            )
        self._record(heard, "comando", False, display_order(hit))
        return self._run(hit)

    def _arg_missing(self, hit: Hit) -> bool:
        needs = {"crear sesion", "abrir sesion", "borrar sesion", "crear agente", "abrir agente", "borra", "voz"}
        return hit.strict in needs and not hit.arg

    def _missing(self, hit: Hit) -> str:
        if hit.strict == "borra":
            return "¿A quién borro?"
        if "agente" in hit.strict:
            return "Dime el nombre del agente."
        if hit.strict == "voz":
            return "Dime el número de la voz."
        return "Dime el nombre."

    def _confirm(self, hit: Hit) -> str:
        if hit.strict == "crear sesion":
            return f"¿Creo la sesión {hit.arg}? ¿Sí o no?"
        if hit.strict == "borrar sesion":
            return f"¿Borro la sesión {hit.arg}? ¿Sí o no?"
        if hit.strict == "borra":
            return f"¿Borro a {hit.arg}? ¿Sí o no?"
        return say("confirm", "Has dicho: {order}. ¿Sí o no?", order=display_order(hit))

    def _run(self, hit: Hit) -> Turn:
        name = hit.strict
        if name == "subir volumen":
            self.settings.volume = min(100, int(self.settings.volume) + 5)
            self.persist()
            return self._said([say("volume", "Volumen al {n} por ciento.", n=self.settings.volume)], effects=[("volume", self.settings.volume)])
        if name == "bajar volumen":
            self.settings.volume = max(0, int(self.settings.volume) - 5)
            self.persist()
            return self._said([say("volume", "Volumen al {n} por ciento.", n=self.settings.volume)], effects=[("volume", self.settings.volume)])
        if name == "otra voz":
            if len(self.voices) <= 1:
                return self._said(["Solo tengo una voz."])
            self.settings.voice_index = (self.settings.voice_index + 1) % len(self.voices)
            self.persist()
            n = self.settings.voice_index + 1
            return self._said([f"Voz {n}, {self.voices[self.settings.voice_index]}."])
        if name == "voz":
            number = int(hit.arg)
            if number < 1 or number > len(self.voices):
                return self._said(["Ese número de voz no está."])
            self.settings.voice_index = number - 1
            self.persist()
            return self._said([f"Voz {number}, {self.voices[number - 1]}."])
        if name == "otro reconocedor":
            if len(self.recognizers) <= 1:
                return self._said(["Solo tengo el teclado."])
            try:
                index = self.recognizers.index(self.settings.recognizer)
            except ValueError:
                index = 0
            self.settings.recognizer = self.recognizers[(index + 1) % len(self.recognizers)]
            self.persist()
            return self._said(
                [f"Reconocedor {self.settings.recognizer}."],
                effects=[("recognizer", self.settings.recognizer)],
            )
        if name == "reconocedor":
            if hit.arg not in self.recognizers:
                return self._said(["Ese reconocedor no está instalado."])
            self.settings.recognizer = hit.arg
            self.persist()
            return self._said([f"Reconocedor {hit.arg}."], effects=[("recognizer", hit.arg)])
        if name == "pon cancion":
            return self._said([say("play", "Pongo {title}.", title=hit.arg)], effects=[("play", hit.arg)])
        if name == "pausa musica":
            return self._said([say("pause", "Pauso.")], effects=[("pause_music",)])
        if name == "seguir musica":
            return self._said([say("resume", "Sigo.")], effects=[("resume_music",)])
        if name == "para la musica":
            return self._said([say("stop_music", "Paro la música.")], effects=[("stop_music",)])
        if name == "listar sesiones":
            names = self.sessions.names()
            return self._said(["Tengo " + ", ".join(names) + "."])
        if name == "crear sesion":
            if self.sessions.resolve(hit.arg):
                return self._said(["Esa sesión ya está."])
            made = self.sessions.create(hit.arg)
            if not made:
                return self._said(["No puedo crear esa sesión."])
            return self._said([f"Sesión {made} creada."])
        if name == "abrir sesion":
            opened = self.sessions.open(hit.arg)
            if not opened:
                return self._said(["No tengo esa sesión."])
            return self._said([f"Sesión {opened}."])
        if name == "cerrar sesion":
            self.sessions.close_to_shared(self.wall(), self.settings.shared_days)
            self.in_conversation = False
            self.opener = None
            self.detail_used = False
            return self._said(["Sesión compartida."], status="Escuchando")
        if name == "borrar sesion":
            if hit.arg.casefold() == SHARED:
                return self._said(["No borro la compartida."])
            deleted = self.sessions.delete(hit.arg)
            if not deleted:
                return self._said(["No tengo esa sesión."])
            return self._said([f"Sesión {deleted} borrada."])
        if name == "listar agentes":
            found = [record.name for record in self.agents.list()]
            if not found:
                return self._said(["No hay agentes."])
            return self._said(["Tengo " + ", ".join(found) + "."])
        if name == "abrir agente":
            opened = self.agents.open(hit.arg)
            if not opened:
                return self._said(["No tengo ese agente."])
            return self._said([f"Agente {opened.name}."])
        if name == "crear agente":
            if self.agents.resolve(hit.arg):
                return self._said(["Ese agente ya está."])
            made = self.agents.create(hit.arg)
            return self._said([f"Agente {made.name} creado."])
        if name == "cerrar agente":
            if not self.agents.active:
                return self._said(["No había ningún agente."])
            self.agents.close()
            return self._said(["Cierro el agente."])
        if name == "ayuda":
            return self._said([spoken_help()])
        if name == "cambiar nombre":
            self.naming = {"stage": "choose", "name": "", "heard": []}
            return self._said(["¿Cómo quieres llamarme? Dilo, o escríbelo en la caja."])
        if name == "identifica mi voz":
            self.enroll = _blank_enroll()
            return self._said(["¿Cómo te llamas?"], effects=[("enroll", "¿Cómo te llamas?", "")])
        if name == "lista las personas":
            found = self.speakers.names()
            if not found:
                return self._said(["Todavía no hay nadie."])
            return self._said(["Tengo a " + ", ".join(found) + "."])
        if name == "borra":
            deleted = self.speakers.delete(hit.arg)
            if not deleted:
                return self._said(["No tengo a esa persona."])
            extra = " Ya oigo a todo el mundo." if self.speakers.locked is None else ""
            return self._said([f"Borro a {deleted}.{extra}"])
        if name == "modo administrador":
            return self._said(["Modo administrador."])
        if name == "grok solo web":
            self.settings.grok_files = False
            self.persist()
            self._remember_room()
            return self._said([say("files_off", "Grok solo consulta la web. No cambia archivos.")])
        if name == "grok puede editar":
            self.settings.grok_files = True
            self.persist()
            self._remember_room()
            return self._said([say("files_on", "Grok puede cambiar archivos. Sigue sin usar el shell.")])
        return self._said([say("unknown", "No conozco ese comando.")])

    def set_grok_files(self, allow: bool) -> Turn:
        hit = Hit("grok puede editar" if allow else "grok solo web", admin=True)
        return self._on_yes(hit)

    def _remember_room(self) -> None:
        folder = getattr(self, "room_dir", None)
        if folder is None:
            return
        from grok_assistant.rules.hub import write_room_rules

        write_room_rules(folder, bool(self.settings.grok_files))
