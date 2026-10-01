"""Conversation rules. A phrase leaves the machine only inside a Job."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from grok_assistant.auth import AdminAuth
from grok_assistant.enroll_audio import PHRASES, one_voice
from grok_assistant.helptext import SCREEN_HELP, spoken_help
from grok_assistant.i18n import say, text
from grok_assistant.match import (
    Hit,
    Song,
    canonicalize,
    closer,
    display_order,
    blank_phrase,
    is_presence,
    noise_phrase,
    is_test_word,
    thin_phrase,
    is_wake,
    is_yes,
    parse_order,
    song_of,
    strip_comando,
    tokenize,
    wake_is_presence,
)
from grok_assistant.store import SHARED, AgentBook, SessionStore, SpeakerBook

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_COMANDO = re.compile(r"^\s*COMANDO:\s*(.+?)\s*$", re.IGNORECASE)


def _ear_label(kind: str) -> str:
    from grok_assistant.listen import RECOGNIZER_LABELS

    return RECOGNIZER_LABELS.get(kind, kind)


def _blank_enroll() -> dict:
    return {
        "stage": "name",
        "target": None,
        "spoken": "",
        "take": 0,
        "vectors": [],
        "clips": [],
        "misses": 0,
    }


@dataclass
class Job:
    kind: str
    text: str
    effort: str = "low"
    agent_name: str | None = None
    agent_path: str | None = None
    slot: str = "session"


@dataclass
class Turn:
    speak: list[str] = field(default_factory=list)
    effects: list[tuple] = field(default_factory=list)
    job: Job | None = None
    status: str | None = None


def split_commands(answer: str) -> tuple[list[str], str]:
    commands: list[str] = []
    kept: list[str] = []
    for line in (answer or "").splitlines() or [""]:
        matched = _COMANDO.match(line)
        if matched:
            commands.append(matched.group(1).strip())
        else:
            kept.append(line)
    return commands, "\n".join(kept).strip()


def for_speech(text: str) -> str:
    text = _ANSI.sub("", text or "")
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip().replace("**", "").replace("`", "")
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        if stripped.startswith(("- ", "* ")):
            stripped = stripped[2:].strip()
        if stripped:
            lines.append(stripped)
    return " ".join(lines).strip()


class Brain:
    def __init__(
        self,
        settings,
        sessions: SessionStore,
        speakers: SpeakerBook,
        agents: AgentBook,
        auth: AdminAuth,
        hellos: list[str],
        waits: list[str],
        *,
        clock=None,
        wall=None,
        persist=None,
        embedder_ready: bool = False,
    ):
        self.settings = settings
        self.sessions = sessions
        self.speakers = speakers
        self.agents = agents
        self.auth = auth
        self.hellos = hellos or ["Hola."]
        self.waits = waits or ["Un momento."]
        self.clock = clock or time.monotonic
        self.wall = wall or time.time
        self.persist = persist or (lambda: None)
        self.embedder_ready = embedder_ready
        self.voices = ["Predeterminada"]
        self.recognizers = ["teclado"]
        self.in_conversation = False
        self.test_mode = False
        self.paused = False
        self.busy = False
        self.admin_until = None
        self.pending = None
        self.enroll = None
        self.naming = None
        self.identifier_ready = False
        self.opener = None
        self.detail_used = False
        self.last_question = ""
        self.last_heard = ""
        self.last_spoken = ""
        self.last_activity = self.clock()
        self._armed = False
        self.phase = ""
        self.effort_now = "low"
        self.logs: list[str] = []
        self._flow_heard = ""
        self.hearing = False
        self._live_open = False
        self._live_text = ""

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
        from grok_assistant.banter import pool

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
        from grok_assistant.marketplace import offers

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
        if (
            self.in_conversation
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
        self.sessions.roll(self.wall())
        pairs = tokenize(heard)
        norms = [norm for _, norm in pairs]
        if self.test_mode:
            return self._test(heard, norms)
        if not speaker_id and vector and self.embedder_ready:
            speaker_id = self.speakers.closest(vector, self.settings.recognizer)
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
        if not self.speakers.has_prints(self.settings.recognizer):
            return True
        if self.speakers.locked:
            return speaker_id != self.speakers.locked
        return not speaker_id

    def _voice_allowed(self, speaker_id: str | None) -> bool:
        if not self.embedder_ready:
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

    def _wake_question(self, heard: str, norms: list[str], pairs: list[tuple[str, str]], speaker_id: str | None) -> Turn | None:
        from grok_assistant.match import wake_split

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
            self.sessions.close_to_shared()
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
        return self._said([say("unknown", "No conozco ese comando.")])

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
        phrase = PHRASES[self.enroll["take"]]
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

    def _prompt_take(self) -> Turn:
        index = self.enroll["take"]
        phrase = PHRASES[index]
        total = len(PHRASES)
        if index == 0:
            said = (
                f"Grabaré {total} frases una sola vez. Guardo el sonido en crudo, sin comprobar las palabras. "
                f"El sonido vale para todos los motores. "
                f"Habla después del pitido, y espera el segundo pitido. "
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
        if not kept:
            self.enroll = None
            return self._said(["Estas tomas no son una sola voz. No guardo a otra persona."])
        kept_clips = [clips[index] for index in kept]
        kept_vectors = [vectors[index] for index in kept]
        stored = self.speakers.store_recording(name, kept_clips, kept_vectors, True)
        self.enroll = None
        kept_n = len(kept_vectors)
        total = len(PHRASES)
        detail = f" Guardo {kept_n} de {total}." if kept_n < total else ""
        return self._said(
            [f"Listo, {stored}.{detail} El sonido queda guardado y vale para todos los motores. Valoro cada uno."],
            effects=[("score_prints", stored)],
        )

    def _next_wait(self) -> str:
        return self._take_banter("wait_index")

    def _said(self, lines: list[str], effects: list[tuple] | None = None, status: str | None = None) -> Turn:
        if lines:
            self.last_spoken = lines[-1]
        return Turn(speak=list(lines), effects=list(effects or []), status=status or self.status_label())

    def _touch(self) -> None:
        self._armed = True

    def _record(self, heard: str, decision: str, sent: bool, detail: str = "") -> None:
        self.sessions.append({
            "ts": self.wall(),
            "heard": heard,
            "decision": decision,
            "sent": sent,
            "detail": detail,
        })
        if heard:
            self._flow(heard)
        if decision == "comando" and detail:
            self._step(f"orden: {detail}")

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

    def preview(self, text: str) -> None:
        """Replace one line while the person is still speaking."""
        heard = " ".join((text or "").split())
        if not heard or heard == self._live_text:
            return
        self._live_text = heard
        self.last_heard = heard
        stamp = time.strftime("%H:%M:%S")
        line = f"{stamp}  ·  {heard}"
        if self._live_open and self.logs and "  ·  " in self.logs[-1]:
            self.logs[-1] = line
            return
        self.logs.append(line)
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
        self._live_open = True

    def note(self, line: str) -> None:
        self._write_log(line, branch=False)

    def _log(self, line: str) -> None:
        self._step(line)

    def _flow(self, heard: str) -> None:
        if not heard:
            return
        if self._live_open and self.logs and "  ·  " in self.logs[-1]:
            stamp = self.logs[-1].split("  ·  ", 1)[0]
            self.logs[-1] = f"{stamp}  ·  {heard}"
            self._flow_heard = heard
            self.last_heard = heard
            self._live_text = heard
            self._live_open = False
            return
        self._live_open = False
        if heard == self._flow_heard:
            return
        self._flow_heard = heard
        self._write_log(heard, branch=False)

    def _step(self, text: str) -> None:
        self._write_log(text, branch=True)

    def _write_log(self, text: str, branch: bool) -> None:
        stamp = time.strftime("%H:%M:%S")
        kind = "¦" if branch else "·"
        self.logs.append(f"{stamp}  {kind}  {text}")
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
