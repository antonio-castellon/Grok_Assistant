from __future__ import annotations

from grok_assistant.ui.deps import *  # noqa: F401,F403


class EarMixin:
    """The microphone and the live line."""

    def _release_ear(self, ear) -> None:
        if ear is None:
            return
        ear.stop()
        join = getattr(ear, "join", None)
        if callable(join):
            join(1.5)
        thread = getattr(ear, "_thread", None)
        if thread is not None and thread.is_alive():
            thread.join(1.5)

    def _hearing_device(self) -> str:
        from grok_assistant.listening.devices import listed_inputs, resolve_microphone

        saved = self.hub.brain.settings.microphone
        mics = listed_inputs()
        name, _index = resolve_microphone(saved, mics)
        if mics is not None and name != saved:
            self.hub.brain.settings.microphone = name
            self.hub.brain.persist()
        return name

    def _sync_ear(self) -> None:
        if self._ears_suspended:
            return
        kind = self.hub.brain.settings.recognizer
        device = self._hearing_device()
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
        if want_stream and (self.kroko is None or self.kroko.kind != kind or getattr(self.kroko, "device", None) != device):
            if self.kroko is not None:
                self._release_ear(self.kroko)
                self.kroko = None
            ear = KrokoEar(
                self._heard,
                self._kroko_status,
                wake_name=lambda: self.hub.brain.settings.wake_name,
                kind=kind,
                on_partial=self._preview,
                talk_mode=lambda: self.hub.brain.settings.talk_mode,
                device=device,
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
            self._release_ear(self.kroko)
            self.kroko = None
        want_offline = kind in OFFLINE_KINDS and not self.user_paused
        if want_offline and (self.offline is None or self.offline.kind != kind or getattr(self.offline, "device", None) != device):
            if self.offline is not None:
                self._release_ear(self.offline)
            ear = OfflineEar(
                kind,
                self._heard,
                self._kroko_status,
                silence=self._phrase_silence,
                device=device,
                on_partial=self._preview,
            )
            if ear.start():
                self.offline = ear
                self._note(f"cargo {RECOGNIZER_LABELS[kind]}")
            else:
                self.offline = None
                self._note(ear.error or "ese oído no pudo escuchar")
        if not want_offline and self.offline is not None:
            self._release_ear(self.offline)
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
        """Keep the capture thread free. The reading is accepted in order, later."""
        self._heard_box.put((text, audio))

    def _heard_worker(self) -> None:
        while True:
            text, audio = self._heard_box.get()
            try:
                self._accept_heard(text, audio)
            except Exception as exc:
                self._write_crash(exc)

    def _accept_heard(self, text: str, audio=None) -> None:
        if self.user_paused:
            return
        self._settle_preview()
        enroll = self.hub.brain.enroll
        if isinstance(enroll, dict) and enroll.get("stage") == "takes":
            if self._take_open and time.monotonic() >= self._drop_take_audio:
                self._take_box.put((text or "", audio))
            return
        from grok_assistant.rules.match import is_presence, words_norm

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
        try:
            self.hub.brain.keep_heard(chosen, audio, primary=primary, second=second, heard_by=heard_by, who=who)
        except Exception as exc:
            self._write_crash(exc)
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

    def _arm_refiner(self) -> None:
        if self.refiner.load():
            self.ui.put(lambda: self._note(f"fuera de la prueba, releo cada frase con {self.refiner.label()} para guardar los nombres en inglés"))

    def _arm_voiceprint(self) -> None:
        if self.voiceprint.ensure():
            self.hub.brain.embedder_ready = True
            self.ui.put(lambda: self._note("la huella de voz está lista"))
