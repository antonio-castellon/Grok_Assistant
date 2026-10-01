from __future__ import annotations

from grok_assistant.rules.common import *  # noqa: F401,F403


class StatusMixin:
    """Labels, the corner banner, and the idle clock."""

    def set_devices(self, voices: list[str], recognizers: list[str]) -> None:
        previous = ""
        if self.voices and 0 <= self.settings.voice_index < len(self.voices):
            previous = self.voices[self.settings.voice_index]
        if voices:
            self.voices = list(voices)
        if recognizers:
            self.recognizers = list(recognizers)
        if self.settings.recognizer not in self.recognizers:
            self.settings.recognizer = self.recognizers[0]
            self.persist()
        if previous and previous not in {"Predeterminada", ""} and previous in self.voices:
            chosen = self.voices.index(previous)
        elif previous and previous not in {"Predeterminada", ""}:
            chosen = 0
        else:
            chosen = self.settings.voice_index
        if chosen >= len(self.voices):
            chosen = 0
        if chosen != self.settings.voice_index:
            self.settings.voice_index = chosen
            self.persist()

    def _banter_lines(self) -> list[str]:
        from grok_assistant.speaking.banter import pool

        found = pool(self.settings.language, self.settings.line_kinds, self.settings.line_themes)
        return found or self.hellos or ["Hola."]

    def _take_banter(self, index_name: str) -> str:
        lines = self._banter_lines()
        index = getattr(self.settings, index_name) % len(lines)
        line = lines[index]
        if line == self.last_spoken and len(lines) > 1:
            index = (index + 1) % len(lines)
            line = lines[index]
        setattr(self.settings, index_name, index + 1)
        self.last_spoken = line
        self.persist()
        return line

    def startup_line(self) -> str:
        return self._take_banter("hello_index")

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def mark_busy(self) -> None:
        self.busy = True

    def mark_idle(self) -> None:
        self.busy = False
        if self._armed:
            self.last_activity = self.clock()
            self._armed = False

    def is_admin(self) -> bool:
        return self.admin_until is not None and self.clock() < self.admin_until

    def mode_label(self) -> str:
        if self.paused:
            return text("status.pause", "modo pausa")
        if self.test_mode:
            return text("status.test", "modo prueba")
        if self.phase:
            return self.phase
        if self.in_conversation:
            return text("status.talk", "modo conversación")
        return text("status.listen", "modo escucha")

    def identifier_label(self) -> str:
        from grok_assistant.house.marketplace import offers

        ready = [offer for offer in offers() if offer.kind == "llm" and offer.ready()]
        if not self.settings.local_llm or not ready:
            return text("status.no_identifier", "sin identificador")
        wanted = self.settings.llm_file
        for offer in ready:
            filename = offer.files[0][1].rsplit("/", 1)[-1]
            if filename == wanted:
                return offer.title
        return ready[0].title

    def status_label(self) -> str:
        return self.mode_label()

    def banner_label(self) -> str:
        if self.paused:
            return text("status.banner_pause", "EN PAUSA")
        if self.hearing:
            return self._live_text or text("status.banner_hear", "OYENDO")
        if self.test_mode:
            return text("status.banner_test", "PRUEBA")
        if self.in_conversation:
            return text("status.banner_talk", "EN CONVERSACIÓN")
        return text("status.banner_wait", "ESPERA")

    def snapshot(self) -> dict:
        session = self.sessions.current()
        voice_no = self.settings.voice_index + 1
        voice_name = self.voices[self.settings.voice_index] if self.voices else ""
        return {
            "status": self.status_label(),
            "banner": self.banner_label(),
            "banner_kind": (
                "pause" if self.paused
                else "hear" if self.hearing
                else "test" if self.test_mode
                else "talk" if self.in_conversation
                else "wait"
            ),
            "model": self.settings.model,
            "effort": text("status.effort_high", "alto") if self.effort_now == "high" else text("status.effort_low", "bajo"),
            "voice": f"{voice_no}. {voice_name}",
            "recognizer": text(f"ear.{self.settings.recognizer}", self.settings.recognizer),
            "identifier": self.identifier_label(),
            "session": session.name,
            "shared": session.shared,
            "volume": self.settings.volume,
            "last_heard": self.last_heard,
            "last_spoken": self.last_spoken,
            "agent": self.agents.active or "",
            "admin": self.is_admin(),
            "help": SCREEN_HELP,
            "paused": self.paused,
        }

    def tick(self) -> Turn:
        spoken: list[str] = []
        if self.admin_until is not None and self.clock() >= self.admin_until:
            self.admin_until = None
            if self.pending and self.pending[0] == "leave_admin":
                self.pending = None
            spoken.append("Se acabó el modo administrador.")
        self.sessions.roll(self.wall(), self.settings.shared_days)
        if (
            self.in_conversation
            and self.settings.talk_mode != "abierta"
            and not self.busy
            and not self.test_mode
            and self.enroll is None
            and self.clock() - self.last_activity >= 60
        ):
            self.in_conversation = False
            self.opener = None
            self.detail_used = False
            if self.pending and self.pending[0] in {"detail", "yesno"}:
                self.pending = None
        if spoken:
            self.last_spoken = spoken[-1]
        return Turn(speak=spoken, status=self.status_label())
