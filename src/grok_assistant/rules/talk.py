from __future__ import annotations

from grok_assistant.rules.common import *  # noqa: F401,F403


class TalkMixin:
    """Wake, conversation, and what is allowed to leave the house."""

    def handle(
        self,
        text: str,
        *,
        speaker_id: str | None = None,
        unknown_print: bool = False,
        vector: list[float] | None = None,
    ) -> Turn:
        heard = " ".join((text or "").split())
        if not heard or self.paused:
            return Turn()
        if noise_phrase(heard) and not self.test_mode:
            self._record(heard, "ignorar", False, "ruido")
            self.last_heard = heard
            return Turn()
        self.sessions.roll(self.wall(), self.settings.shared_days)
        pairs = tokenize(heard)
        norms = [norm for _, norm in pairs]
        if self.test_mode:
            return self._test(heard, norms)
        if not speaker_id and vector and self.embedder_ready:
            speaker_id = self.speakers.closest(
                vector, self.settings.recognizer, microphone=self.settings.microphone
            )
        self._turn_speaker = speaker_id
        if self._silent_stranger(speaker_id, vector):
            return Turn()
        if not norms:
            self._record(heard, "ignorar", False)
            return Turn()
        if not self._voice_allowed(speaker_id):
            return Turn()
        if self.naming is not None:
            return self._name_take(heard, norms)
        if self.pending or self.enroll is not None:
            return self._pending(heard, norms, pairs, vector)
        if unknown_print and not self.speakers.locked and self._is_wake(norms) and not strip_comando(norms)[0]:
            self.pending = ("new_name", vector)
            self._record(heard, "ignorar", False, "saludo")
            self.last_heard = heard
            self._touch()
            return self._said(["Hola, ¿cómo te llamas?"], status="Conversación")

        is_cmd, _rest = strip_comando(norms)
        body = pairs[1:] if is_cmd else pairs
        song = song_of(body)

        if not self.in_conversation:
            if not is_cmd and is_presence(norms, self.settings.wake_name):
                return self._presence(heard)
            if not is_cmd:
                woken = self._wake_question(heard, norms, pairs, speaker_id)
                if woken is not None:
                    return woken
                slipped = self._slipped_greeting(heard, speaker_id)
                if slipped is not None:
                    return slipped
            if song.too_long:
                self._record(heard, "ignorar", False, "canción larga")
                self.last_heard = heard
                return Turn()
            if song.matched and not song.title and not song.too_long:
                self._touch()
                self._record(heard, "comando", False, "pon cancion")
                self.last_heard = heard
                return self._said([say("what_song", "¿Qué canción?")])
            if song.title and len(norms) <= 16:
                self._touch()
                return self._song(heard, song)
            if len(norms) > 6 and not self.settings.local_llm:
                self._record(heard, "ignorar", False, "larga")
                self.last_heard = heard
                return Turn()
            if not is_cmd:
                if is_test_word(norms):
                    return self._enter_test(heard)
                if thin_phrase(heard):
                    self._record(heard, "ignorar", False, "corto")
                    self.last_heard = heard
                    return Turn()
                if self.settings.local_llm:
                    return self._review(heard)
                self._record(heard, "ignorar", False)
                self.last_heard = heard
                return Turn()
            self._touch()
            return self._order(heard, body, len(norms))

        if not is_cmd and is_presence(norms, self.settings.wake_name):
            return self._presence(heard)
        if not is_cmd:
            woken = self._wake_question(heard, norms, pairs, speaker_id)
            if woken is not None:
                return woken
            slipped = self._slipped_greeting(heard, speaker_id)
            if slipped is not None:
                return slipped
        kind = closer([norm for _, norm in body] if is_cmd else norms)
        if kind and not (is_cmd and ("sesion" in norms or "agente" in norms)):
            self._touch()
            self._record(heard, "ignorar", False, "adios")
            return self._goodbye(kind)
        if song.matched and not song.title and not song.too_long:
            self._touch()
            self._record(heard, "comando", False, "pon cancion")
            self.last_heard = heard
            return self._said([say("what_song", "¿Qué canción?")])
        if song.title and len(norms) <= 16:
            self._touch()
            return self._song(heard, song)
        if song.too_long:
            self._touch()
            return self._cloud(heard)
        if is_cmd:
            self._touch()
            return self._order(heard, body, len(norms))
        if is_test_word(norms):
            self._touch()
            return self._enter_test(heard)
        if blank_phrase(heard):
            self._record(heard, "ignorar", False, "corto")
            self.last_heard = heard
            return Turn()
        self._touch()
        return self._cloud(heard)

    def finish_classify(self, data: dict) -> Turn:
        self.phase = ""
        accion = str((data or {}).get("accion") or "")
        orden = str((data or {}).get("orden") or "")
        hit = canonicalize(orden) if accion == "comando" else None
        if hit is None:
            return self._said([say("unknown", "No conozco ese comando.")])
        self.pending = ("yesno", hit)
        self._step(f"Grok: {display_order(hit)}")
        return self._said([say("confirm", "Has dicho: {order}. ¿Sí o no?", order=display_order(hit))])

    def finish_converse(self, answer: str) -> Turn:
        self.phase = ""
        self.effort_now = "low"
        commands, speech = split_commands(answer)
        speech = for_speech(speech)
        spoken: list[str] = []
        effects: list[tuple] = []
        if speech:
            spoken.append(speech)
            self.last_spoken = speech
            self._step(f"Grok: {' '.join(speech.split())}")
            self.sessions.append({
                "ts": self.wall(),
                "heard": "",
                "decision": "respuesta",
                "sent": False,
                "detail": speech,
            })
        for raw in commands:
            hit = canonicalize(raw)
            if hit is None:
                self._step(f"Grok: {raw}")
                continue
            if hit.confirm or (hit.admin and not self.is_admin()):
                self.pending = ("yesno", hit)
                spoken.append(say("confirm", "Has dicho: {order}. ¿Sí o no?", order=display_order(hit)))
                break
            follow = self._run(hit)
            spoken.extend(follow.speak)
            effects.extend(follow.effects)
        if speech and len(speech.split()) >= 28 and not commands and not self.detail_used:
            spoken.append(say("more_detail", "¿Quieres que te lo cuente con más detalle?"))
            self.pending = ("detail", self.last_question)
        return Turn(speak=spoken, effects=effects, status=self.status_label())

    def finish_error(self, message: str) -> Turn:
        self.phase = ""
        self.effort_now = "low"
        self._step("Grok: " + " ".join(message.split())[:180])
        return self._said([say("cloud_down", "Ahora mismo no llego a la nube.")])

    def submit_password(self, password: str) -> Turn:
        if not self.pending or self.pending[0] != "password":
            return self._said(["No había nada esperando la contraseña."])
        if not self.auth.verify(password):
            self.pending = None
            return self._said(["Contraseña incorrecta."])
        _tag, hit = self.pending
        self.pending = None
        self.admin_until = self.clock() + 300
        follow = self._run(hit)
        if hit.strict in {"crear agente", "borra"}:
            follow.speak.append("¿Sales del modo administrador?")
            self.pending = ("leave_admin",)
        return follow

    def cancel_password(self) -> Turn:
        if self.pending and self.pending[0] == "password":
            self.pending = None
        return self._said(["Vale."])

    def _pending(self, heard: str, norms: list[str], pairs, vector) -> Turn:
        self.last_heard = heard
        self._touch()
        if self.enroll is not None:
            return self._enroll_phrase(heard, norms, vector)
        kind = self.pending[0]
        if kind == "yesno":
            self._record(heard, "comando", False, "respuesta")
            if is_yes(norms):
                return self._on_yes(self.pending[1])
            self.pending = None
            return self._said(["Vale."])
        if kind == "detail":
            self._record(heard, "ignorar", False, "detalle")
            if is_yes(norms):
                return self._detail_yes()
            self.pending = None
            return self._said(["Vale."])
        if kind == "leave_admin":
            self._record(heard, "ignorar", False, "admin")
            self.pending = None
            if is_yes(norms):
                self.admin_until = None
                return self._said(["Vale."])
            return self._said(["Vale."])
        if kind == "new_name":
            self._record(heard, "ignorar", False, "nombre")
            if norms == ["salir"]:
                self.pending = None
                return self._said(["Vale."])
            stored = self.speakers.add(heard, [vector] if vector else [], lock=False)
            self.pending = None
            self.in_conversation = True
            self.opener = stored
            self.detail_used = False
            return self._said([f"Hola, {stored}."], status="Conversación")
        if kind == "password":
            self._record(heard, "ignorar", False, "esperando contraseña")
            return Turn(status=self.status_label())
        self.pending = None
        return Turn()

    def _on_yes(self, hit: Hit) -> Turn:
        self.pending = None
        if hit.admin and not self.is_admin():
            if not self.auth.is_set:
                return self._said(["Primero elige una contraseña de administrador en el menú."])
            self.pending = ("password", hit)
            return Turn(speak=["Hace falta el modo administrador."], effects=[("ask_password",)], status=self.status_label())
        follow = self._run(hit)
        if hit.strict in {"crear agente", "borra"} and self.is_admin():
            follow.speak.append("¿Sales del modo administrador?")
            self.pending = ("leave_admin",)
        return follow

    def _detail_yes(self) -> Turn:
        question = self.pending[1]
        self.pending = None
        self.detail_used = True
        self.last_question = question
        self._record(question, "conversacion", True, "más detalle")
        self.phase = text("status.search", "Buscando en la nube")
        self.effort_now = "high"
        return Turn(
            speak=[self._next_wait()],
            job=self._converse_job(question, "high"),
            status=self.phase,
        )

    def _silent_stranger(self, speaker_id: str | None, vector: list[float] | None) -> bool:
        """Microphone audio with no saved print stays out of the log and the local model."""
        if self.enroll is not None or self.naming is not None:
            return False
        if self.pending and self.pending[0] == "new_name":
            return False
        if not self.embedder_ready:
            return False
        if vector is None and not speaker_id:
            return False
        if not self.speakers.has_prints(self.settings.recognizer, microphone=self.settings.microphone):
            return True
        if self.speakers.locked:
            return speaker_id != self.speakers.locked
        return not speaker_id

    def _voice_allowed(self, speaker_id: str | None) -> bool:
        """A locked print filters other voices. A click or a typed line has no print."""
        if not self.embedder_ready or not speaker_id:
            return True
        if self.speakers.locked:
            return speaker_id == self.speakers.locked
        if self.in_conversation and self.opener and speaker_id and speaker_id != self.opener:
            return False
        return True

    def _is_wake(self, norms: list[str]) -> bool:
        heard = self.settings.wake_heard or []
        # One changed letter ("Ola Grok") is still the greeting. The small model was dropping it.
        return is_wake(norms, self.settings.wake_name, heard)

    def _slipped_greeting(self, heard: str, speaker_id: str | None) -> Turn | None:
        """«Hola miren» is a greeting to Miguel. The line says so, without the prompt echo."""
        from grok_assistant.rules.match import near_greeting, tokenize

        fixed = near_greeting(heard, self.settings.wake_name)
        if not fixed:
            return None
        self._record(heard, "ignorar", False, "saludo")
        self.last_heard = heard
        if self.settings.local_llm:
            self._log(f"LLM: saludo · {fixed}")
        norms = [norm for _, norm in tokenize(heard)]
        return self._wake(heard, norms, speaker_id, logged=False)

    def hear_phoneme(self, text: str, speaker_id: str | None = None) -> Turn | None:
        """The keyword already matched. None keeps the chat closed.

        A tail after the name, or real words the engine kept, goes to ``_cloud``.
        A greeting, an empty reading, or a thin phrase uses ``_wake``.
        """
        if not self._voice_allowed(speaker_id):
            return None
        heard = " ".join((text or "").split())
        self._turn_speaker = speaker_id
        pairs = tokenize(heard) if heard else []
        norms = [norm for _, norm in pairs]
        if norms:
            woken = self._wake_question(heard, norms, pairs, speaker_id)
            if woken is not None:
                return woken
        if not heard or thin_phrase(heard):
            return self._wake(heard, norms, speaker_id)
        self.in_conversation = True
        self.detail_used = False
        self.last_heard = heard
        self._touch()
        self.opener = speaker_id
        return self._cloud(heard)

    def _wake_question(self, heard: str, norms: list[str], pairs: list[tuple[str, str]], speaker_id: str | None) -> Turn | None:
        from grok_assistant.rules.match import wake_split

        rest = wake_split(norms, self.settings.wake_name, self.settings.wake_heard or [])
        if rest is None:
            return None
        if not rest:
            return self._wake(heard, norms, speaker_id)
        question = " ".join(raw for raw, _norm in pairs[len(norms) - len(rest):]).strip()
        if not question:
            return self._wake(heard, norms, speaker_id)
        self._record(heard, "conversacion", True, "pregunta tras el saludo")
        self.in_conversation = True
        self.detail_used = False
        self.last_heard = heard
        self._touch()
        self.opener = speaker_id
        return self._cloud(question)

    def rename_typed(self, name: str) -> Turn:
        """The written name is kept as typed. Speech is only for later mishearings."""
        clean = " ".join((name or "").split())
        if not clean or not tokenize(clean):
            return self._said(["Dime un nombre."])
        self.settings.wake_name = clean
        self.settings.wake_heard = []
        self.persist()
        self.naming = {"stage": "train_offer", "name": clean, "heard": [], "kept": True}
        return self._said([
            f"A partir de ahora me llamo {clean}.",
            "Si el oído lo deforma, di sí y lo repites seis veces.",
        ])

    def _name_take(self, heard: str, norms: list[str]) -> Turn:
        self._record(heard, "ignorar", False, "nombre")
        self.last_heard = heard
        if norms == ["salir"]:
            kept = bool(self.naming.get("kept"))
            chosen = self.settings.wake_name
            self.naming = None
            if kept:
                return self._said([f"Me sigo llamando {chosen}."])
            return self._said(["Dejo el nombre como estaba."])
        stage = self.naming["stage"]
        if stage == "train_offer":
            if is_yes(norms):
                self.naming["stage"] = "repeat"
                self.naming["heard"] = []
                return self._said([f"Di «{self.naming['name']}» seis veces. Primera."])
            chosen = self.settings.wake_name
            self.naming = None
            return self._said([f"Me sigo llamando {chosen}."])
        if stage == "choose":
            self.naming["name"] = heard.strip()
            self.naming["stage"] = "confirm"
            return self._said([f"He oído: {heard}. Si ese es el nombre, di sí."])
        if stage == "confirm":
            if is_yes(norms):
                self.naming["stage"] = "repeat"
                self.naming["heard"] = []
                return self._said([f"Di «{self.naming['name']}» seis veces. Primera."])
            self.naming["stage"] = "choose"
            return self._said([f"He oído: {heard}. Dilo otra vez."])
        self.naming["heard"].append(heard)
        count = len(self.naming["heard"])
        if count >= 6:
            self.settings.wake_name = self.naming["name"]
            self.settings.wake_heard = list(self.naming["heard"])
            self.persist()
            chosen = self.settings.wake_name
            self.naming = None
            return self._said([f"He oído: {heard}. 6 de 6. A partir de ahora me llamo {chosen}."])
        return self._said([f"He oído: {heard}. {count} de 6. Otra vez."])

    def _open_chat(self) -> Turn:
        """Open the chat without the wake name. Silence or a thanks line closes it."""
        self.in_conversation = True
        self.detail_used = False
        self.opener = getattr(self, "_turn_speaker", None)
        self._touch()
        return self._said([say("chat_open", "Dime.")], status="Conversación")

    def _presence(self, heard: str) -> Turn:
        self._record(heard, "ignorar", False, "presencia")
        self.last_heard = heard
        self.in_conversation = True
        self.detail_used = False
        self._touch()
        return self._said([say("presence", "Sí, te escucho.")], status="Conversación")

    def _wake(self, heard: str, norms: list[str], speaker_id: str | None, logged: bool = True) -> Turn:
        if logged:
            self._record(heard, "ignorar", False, "saludo")
        self.last_heard = heard
        self.in_conversation = True
        self.detail_used = False
        self._touch()
        if speaker_id and speaker_id in self.speakers.people:
            self.opener = speaker_id
            return self._said([self._greet_known(speaker_id)], status="Conversación")
        self.opener = speaker_id
        if wake_is_presence(norms, self.settings.wake_name):
            return self._said([say("here", "Sí, aquí estoy.")], status="Conversación")
        return self._said([say("hello", "Hola.")], status="Conversación")

    def _greet_known(self, name: str) -> str:
        person = self.speakers.people.get(name) or {}
        last = person.get("last")
        now = self.wall()
        gap = None if last is None else now - float(last)
        slot = self.speakers.people.setdefault(name, {"prints": [], "last": None})
        slot["last"] = now
        self.speakers.save()
        if gap is not None and gap < 3600:
            return "Dime."
        if gap is not None and gap < 5 * 3600:
            return f"Hola de nuevo, {name}."
        extra = self._take_banter("extra_index")
        hello = say("hello", "Hola.").rstrip(".")
        return f"{hello}, {name}. {extra}"

    def _goodbye(self, kind: str) -> Turn:
        self.in_conversation = False
        self.opener = None
        self.detail_used = False
        if self.pending and self.pending[0] in {"detail", "yesno"}:
            self.pending = None
        said = {"denada": say("thanks", "De nada."), "vale": say("ok", "Vale.")}.get(kind, say("bye", "Adiós."))
        return self._said([said], status="Escuchando")

    def _song(self, heard: str, song: Song) -> Turn:
        self._record(heard, "comando", False, f"pon cancion {song.title}")
        self.last_heard = heard
        return self._run(Hit("pon cancion", song.title))

    def _cloud(self, heard: str) -> Turn:
        self.in_conversation = True
        self.last_question = heard
        self.last_heard = heard
        self._record(heard, "conversacion", True)
        self.phase = text("status.search", "Buscando en la nube")
        self.effort_now = "low"
        return Turn(speak=[self._next_wait()], job=self._converse_job(heard, "low"), status=self.phase)
