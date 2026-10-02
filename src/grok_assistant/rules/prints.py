from __future__ import annotations

from grok_assistant.rules.common import *  # noqa: F401,F403


class PrintMixin:
    """Voice-print enrollment and test mode."""

    def _enter_test(self, heard: str) -> Turn:
        self.test_mode = True
        self._record(heard, "comando", False, "prueba")
        return self._said(
            [say("test_enter", "Modo prueba. Anoto lo que oigo y no hago nada. Para salir, di salir, o desactívalo en el menú.")],
            status="Prueba",
        )

    def _leave_test(self, heard: str) -> Turn:
        self.test_mode = False
        self._record(heard, "comando", False, "salir de la prueba")
        return self._said([say("test_leave", "Salgo de la prueba. Vuelvo a escuchar.")])

    def _test(self, heard: str, norms: list[str]) -> Turn:
        bare = [word for word in norms if word != "comando"]
        if bare == ["salir"] or bare == ["salir", "de", "la", "prueba"]:
            return self._leave_test(heard)
        self._record(heard, "ignorar", False, "prueba")
        self._step(_ear_label(self.settings.recognizer))
        self.last_heard = heard
        return Turn(status="Prueba")

    def _enroll_phrase(self, heard: str, norms: list[str], vector) -> Turn:
        self._record(heard, "ignorar", False, "huella")
        if norms == ["salir"]:
            self.enroll = None
            return self._said(["Vale."])
        stage = self.enroll["stage"]
        if stage == "name":
            name = heard.strip()
            if not name:
                return self._said(["Di otro nombre."])
            self.enroll["spoken"] = name
            voice_match = self.speakers.closest(vector, self.settings.recognizer) if vector else None
            named = self.speakers.resolve(name)
            who = named or voice_match
            if who:
                self.enroll["target"] = who
                self.enroll["stage"] = "confirm_replace"
                return self._said([f"{name}. Esta voz ya la tengo como {who}. ¿Repito la identificación?"])
            self.enroll["stage"] = "confirm_new"
            return self._said([f"{name}. No tengo a {name}. ¿Lo guardo como otra persona?"])
        if stage in {"confirm_new", "confirm_replace"}:
            if is_yes(norms):
                self.enroll["stage"] = "takes"
                self.enroll["take"] = 0
                self.enroll["clips"] = []
                self.enroll["vectors"] = []
                self.enroll["misses"] = 0
                return self._prompt_take()
            self.enroll["stage"] = "name"
            return self._said(["Di otro nombre."])
        if stage == "takes":
            return self._said(["No he cogido la huella. Repite."])
        self.enroll = None
        return self._said(["Vale."])

    def accept_take(self, samples, vector, heard: str = "") -> Turn:
        """One phrase of the shared recording. The microphone audio is kept raw."""
        if not self.enroll or self.enroll.get("stage") != "takes":
            return Turn()
        heard = " ".join((heard or "").split())
        label = _ear_label(self.settings.recognizer)
        phrase = self._phrases()[self.enroll["take"]]
        if heard:
            self._flow_heard = ""
            self._flow(heard)
            self._step(label)
        if samples is None:
            self.note(f"huella: silencio · {label}")
        elif not heard:
            self.note(f"huella: sonido guardado · {label}")
        if samples is None or not vector:
            self.enroll["misses"] = int(self.enroll.get("misses") or 0) + 1
            if self.enroll["misses"] >= 3:
                self.enroll = None
                if heard:
                    return self._said([f"He oído: {heard}. No he cogido la huella. Lo dejo."])
                return self._said(["No oigo el micrófono. Lo dejo."])
            if heard:
                return self._said(
                    [f"He oído: {heard}. No he cogido la huella. Repite."],
                    effects=[("record_take", phrase)],
                )
            return self._said(["No he cogido la huella. Repite."], effects=[("record_take", phrase)])
        self.enroll["misses"] = 0
        self.enroll["clips"].append({"phrase": phrase, "samples": samples})
        self.enroll["vectors"].append(list(vector))
        self.enroll["take"] += 1
        total = len(PHRASES)
        self._step(f"huella: {self.enroll['take']} de {total}")
        if self.enroll["take"] >= total:
            return self._finish_enroll()
        return self._prompt_take()

    def _phrases(self) -> tuple[str, ...]:
        return enroll_phrases(self.settings.wake_name)

    def _prompt_take(self) -> Turn:
        index = self.enroll["take"]
        phrase = self._phrases()[index]
        total = len(PHRASES)
        if index == 0:
            said = (
                f"Grabaré {total} frases una sola vez. La frase sale en la ventana. "
                f"Reintentar repite esta. Seguir pasa a la siguiente. Salir tira lo grabado. "
                f"Habla después del pitido. "
                f"1 de {total}. {phrase}"
            )
        else:
            said = f"{index + 1} de {total}. {phrase}"
        return self._said([said], effects=[("record_take", phrase)])

    def _finish_enroll(self) -> Turn:
        vectors = list(self.enroll["vectors"])
        clips = list(self.enroll["clips"])
        name = self.enroll["target"] or self.enroll["spoken"]
        kept = one_voice(vectors)
        total = len(clips)
        if kept:
            kept_vectors = [vectors[index] for index in kept]
            stored = self.speakers.store_recording(name, clips, kept_vectors, True)
            self.enroll = None
            detail = f" La huella usa {len(kept_vectors)} de {total}." if len(kept_vectors) < total else ""
            self.note(f"huella guardada: {total} wav. {stored}.{detail}")
            return self._said(
                [f"Listo, {stored}.{detail} El sonido queda guardado y vale para todos los motores. Valoro cada uno."],
                effects=[("score_prints", stored)],
            )
        stored = self.speakers.store_recording(name, clips, [], False, replace_print=False)
        self.enroll = None
        self.note(f"huella: {total} wav guardados. Los vectores no son una sola voz, no cambio la huella.")
        return self._said(
            [
                f"Listo, {stored}. Guardo el sonido de las {total} frases. "
                "Los vectores no son una sola voz, así que no cambio la huella de la persona. Valoro cada motor."
            ],
            effects=[("score_prints", stored)],
        )

    def _next_wait(self) -> str:
        from grok_assistant.speaking.waits import pick

        line, index = pick(
            self.settings.language,
            self.settings.wait_styles,
            self.settings.wait_index,
            self.last_spoken,
        )
        self.settings.wait_index = index
        self.last_spoken = line
        self.persist()
        return line

    def discard_capture(self) -> Turn:
        """Leave the recording. Nothing from this session is written."""
        if not self.enroll:
            return Turn()
        self.enroll = None
        self.hearing = False
        self.note("huella: salgo, no guardo los audios")
        return self._said(["Salgo. No guardo los audios de esta huella."])

    def start_capture(self, name: str, ear: str | None = None) -> Turn:
        """Record the phrases once. Every listener is built from that sound."""
        del ear
        clean = " ".join((name or "").split())
        if not clean:
            self.enroll = _blank_enroll()
            return self._said(["¿Cómo te llamas?"], effects=[("enroll", "¿Cómo te llamas?", "")])
        found = self.speakers.resolve(clean) or clean
        self.enroll = _blank_enroll()
        self.enroll["stage"] = "takes"
        self.enroll["target"] = found
        self.enroll["spoken"] = found
        return self._prompt_take()
