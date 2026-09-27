"""Conversation rules. A phrase leaves the machine only inside a Job."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from grok_assistant.auth import AdminAuth
from grok_assistant.helptext import SCREEN_HELP, spoken_help
from grok_assistant.match import (
    Hit,
    Song,
    canonicalize,
    closer,
    display_order,
    is_exact_wake,
    is_test_word,
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
_ENROLL = ("hola grok", "estás ahí", "qué hora es", "pon una canción")
EXTRAS = (
    "Cuánto tiempo.",
    "Ya era hora.",
    "El micrófono preguntaba por ti.",
    "Se me había enfriado el silencio.",
    "Pensé que te había perdido por el pasillo.",
    "Menos mal.",
    "Llegas con la casa en calma.",
    "Ya estaba hablando solo, y se me da regular.",
)


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


def _next_step(decision: str, sent: bool, detail: str) -> str:
    if decision == "ignorar" and detail == "saludo":
        return "saludo. Abro la conversación. El saludo no sale de casa."
    if decision == "ignorar" and detail == "larga":
        return "la ignoro: es larga y no va dirigida al asistente."
    if decision == "ignorar" and detail == "canción larga":
        return "la ignoro: la canción pasa de dieciséis palabras."
    if decision == "ignorar" and detail == "otra voz":
        return "la ignoro: no es la voz que tengo abierta."
    if decision == "ignorar" and detail == "prueba":
        return "modo prueba. Lo anoto y no hago nada."
    if decision == "ignorar" and not sent:
        extra = f" ({detail})" if detail else ""
        return f"la ignoro. Se queda en el cuaderno de casa.{extra}"
    if decision == "conversacion":
        extra = f" {detail}." if detail else ""
        return f"es una pregunta. Envío solo el texto a Grok.{extra}"
    if decision == "comando":
        where = "Lo envío a clasificar." if sent else "Lo hago aquí."
        bit = f" {detail}." if detail else ""
        return f"es una orden.{bit} {where}"
    if decision == "respuesta":
        return detail or "respuesta de Grok"
    return f"{decision} {detail}".strip()


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

    def set_devices(self, voices: list[str], recognizers: list[str]) -> None:
        if voices:
            self.voices = list(voices)
        if recognizers:
            self.recognizers = list(recognizers)
        if self.settings.recognizer not in self.recognizers:
            self.settings.recognizer = self.recognizers[0]
            self.persist()
        if self.settings.voice_index >= len(self.voices):
            self.settings.voice_index = 0
            self.persist()

    def startup_line(self) -> str:
        line = self.hellos[self.settings.hello_index % len(self.hellos)]
        self.settings.hello_index += 1
        self.last_spoken = line
        self.persist()
        return line

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
            return "modo pausa"
        if self.test_mode:
            return "modo prueba"
        if self.phase:
            return self.phase
        if self.in_conversation:
            return "modo conversación"
        return "modo escucha"

    def identifier_label(self) -> str:
        from grok_assistant.marketplace import offers

        ready = [offer for offer in offers() if offer.kind == "llm" and offer.ready()]
        if not self.settings.local_llm or not ready:
            return "sin identificador"
        wanted = self.settings.llm_file
        for offer in ready:
            filename = offer.files[0][1].rsplit("/", 1)[-1]
            if filename == wanted:
                return offer.title
        return ready[0].title

    def status_label(self) -> str:
        return self.mode_label()

    def snapshot(self) -> dict:
        session = self.sessions.current()
        voice_no = self.settings.voice_index + 1
        voice_name = self.voices[self.settings.voice_index] if self.voices else ""
        return {
            "status": self.status_label(),
            "model": self.settings.model,
            "effort": "alto" if self.effort_now == "high" else "bajo",
            "voice": f"{voice_no}. {voice_name}",
            "recognizer": self.settings.recognizer,
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
        self.sessions.roll(self.wall())
        pairs = tokenize(heard)
        norms = [norm for _, norm in pairs]
        if self.test_mode:
            return self._test(heard, norms)
        if not norms:
            self._record(heard, "ignorar", False)
            return Turn()
        if not self._voice_allowed(speaker_id):
            self._record(heard, "ignorar", False, "otra voz")
            self.last_heard = heard
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
            if not is_cmd and self._is_wake(norms):
                return self._wake(heard, norms, speaker_id)
            if song.too_long:
                self._record(heard, "ignorar", False, "canción larga")
                self.last_heard = heard
                return Turn()
            if song.matched and not song.title and not song.too_long:
                self._touch()
                self._record(heard, "comando", False, "pon cancion")
                self.last_heard = heard
                return self._said(["¿Qué canción?"])
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
                if self.settings.local_llm:
                    return self._review(heard)
                self._record(heard, "ignorar", False)
                self.last_heard = heard
                return Turn()
            self._touch()
            return self._order(heard, body, len(norms))

        if not is_cmd and self._is_wake(norms):
            return self._wake(heard, norms, speaker_id)
        kind = closer([norm for _, norm in body] if is_cmd else norms)
        if kind and not (is_cmd and ("sesion" in norms or "agente" in norms)):
            self._touch()
            self._record(heard, "ignorar", False, "adios")
            return self._goodbye(kind)
        if song.matched and not song.title and not song.too_long:
            self._touch()
            self._record(heard, "comando", False, "pon cancion")
            self.last_heard = heard
            return self._said(["¿Qué canción?"])
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
        self._touch()
        return self._cloud(heard)

    def finish_classify(self, data: dict) -> Turn:
        self.phase = ""
        accion = str((data or {}).get("accion") or "")
        orden = str((data or {}).get("orden") or "")
        hit = canonicalize(orden) if accion == "comando" else None
        if hit is None:
            return self._said(["No conozco ese comando."])
        self.pending = ("yesno", hit)
        self._log(f"a confirmar: {display_order(hit)}")
        return self._said([f"Has dicho: {display_order(hit)}. ¿Sí o no?"])

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
            self._log(f"Grok responde: {speech}")
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
                self._log(f"orden desconocida: {raw}")
                continue
            if hit.confirm or (hit.admin and not self.is_admin()):
                self.pending = ("yesno", hit)
                spoken.append(f"Has dicho: {display_order(hit)}. ¿Sí o no?")
                break
            follow = self._run(hit)
            spoken.extend(follow.speak)
            effects.extend(follow.effects)
        if speech and len(speech.split()) >= 28 and not commands and not self.detail_used:
            spoken.append("¿Quieres que te lo cuente con más detalle?")
            self.pending = ("detail", self.last_question)
        return Turn(speak=spoken, effects=effects, status=self.status_label())

    def finish_error(self, message: str) -> Turn:
        self.phase = ""
        self.effort_now = "low"
        self._log(f"error: {message}".replace("\n", " ")[:240])
        return self._said(["Ahora mismo no llego a la nube."])

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
        self.phase = "Buscando en la nube"
        self.effort_now = "high"
        return Turn(
            speak=[self._next_wait()],
            job=self._converse_job(question, "high"),
            status="Buscando en la nube",
        )

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
        if self.identifier_ready:
            return is_exact_wake(norms, self.settings.wake_name, heard)
        return is_wake(norms, self.settings.wake_name, heard)

    def _name_take(self, heard: str, norms: list[str]) -> Turn:
        self._record(heard, "ignorar", False, "nombre")
        self.last_heard = heard
        if norms == ["salir"]:
            self.naming = None
            return self._said(["Dejo el nombre como estaba."])
        stage = self.naming["stage"]
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
            return self._said(["Sí, aquí estoy."], status="Conversación")
        return self._said(["Hola."], status="Conversación")

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
        extra = EXTRAS[self.settings.extra_index % len(EXTRAS)]
        self.settings.extra_index += 1
        self.persist()
        return f"Hola, {name}. {extra}"

    def _goodbye(self, kind: str) -> Turn:
        self.in_conversation = False
        self.opener = None
        self.detail_used = False
        if self.pending and self.pending[0] in {"detail", "yesno"}:
            self.pending = None
        said = {"denada": "De nada.", "vale": "Vale."}.get(kind, "Adiós.")
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
        self.phase = "Buscando en la nube"
        self.effort_now = "low"
        return Turn(speak=[self._next_wait()], job=self._converse_job(heard, "low"), status="Buscando en la nube")

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
            text = " ".join(raw for raw, _ in body)
            self._record(heard, "comando", True, "a clasificar")
            self.phase = "Interpretando … buscando en la nube"
            return Turn(speak=[], job=Job("classify", text), status=self.phase)
        hit = parse_order(body)
        if hit is None:
            text = " ".join(raw for raw, _ in body)
            self._record(heard, "comando", True, "a clasificar")
            self.last_heard = heard
            self.phase = "Interpretando … buscando en la nube"
            return Turn(speak=[], job=Job("classify", text), status=self.phase)
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
        if hit.strict == "apagar":
            return "¿Apago el equipo? ¿Sí o no?"
        if hit.strict == "crear sesion":
            return f"¿Creo la sesión {hit.arg}? ¿Sí o no?"
        if hit.strict == "borrar sesion":
            return f"¿Borro la sesión {hit.arg}? ¿Sí o no?"
        if hit.strict == "borra":
            return f"¿Borro a {hit.arg}? ¿Sí o no?"
        return f"Has dicho: {display_order(hit)}. ¿Sí o no?"

    def _run(self, hit: Hit) -> Turn:
        name = hit.strict
        if name == "subir volumen":
            self.settings.volume = min(100, int(self.settings.volume) + 5)
            self.persist()
            return self._said([f"Volumen al {self.settings.volume} por ciento."], effects=[("volume", self.settings.volume)])
        if name == "bajar volumen":
            self.settings.volume = max(0, int(self.settings.volume) - 5)
            self.persist()
            return self._said([f"Volumen al {self.settings.volume} por ciento."], effects=[("volume", self.settings.volume)])
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
            return self._said([f"Pongo {hit.arg}."], effects=[("play", hit.arg)])
        if name == "pausa musica":
            return self._said(["Pauso."], effects=[("pause_music",)])
        if name == "seguir musica":
            return self._said(["Sigo."], effects=[("resume_music",)])
        if name == "para la musica":
            return self._said(["Paro la música."], effects=[("stop_music",)])
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
            return self._said(["¿Cómo quieres llamarme? Di solo el nombre."])
        if name == "identifica mi voz":
            self.enroll = {"stage": "name", "target": None, "take": 0, "vectors": []}
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
        if name == "apagar":
            return self._said(["Apago."], effects=[("shutdown",)])
        return self._said(["No conozco ese comando."])

    def _enter_test(self, heard: str) -> Turn:
        self.test_mode = True
        self._record(heard, "comando", False, "prueba")
        return self._said(
            ["Modo prueba. Anoto lo que oigo y no hago nada. Para salir, di salir, o desactívalo en el menú."],
            status="Prueba",
        )

    def _leave_test(self, heard: str) -> Turn:
        self.test_mode = False
        self._record(heard, "comando", False, "salir de la prueba")
        return self._said(["Salgo de la prueba. Vuelvo a escuchar."])

    def _test(self, heard: str, norms: list[str]) -> Turn:
        bare = [word for word in norms if word != "comando"]
        if bare == ["salir"] or bare == ["salir", "de", "la", "prueba"]:
            return self._leave_test(heard)
        self._record(heard, "ignorar", False, "prueba")
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
            voice_match = self.speakers.closest(vector) if vector else None
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
                return self._prompt_take()
            self.enroll["stage"] = "name"
            return self._said(["Di otro nombre."])
        if stage == "takes":
            if vector:
                self.enroll["vectors"].append(vector)
            self.enroll["take"] += 1
            heard_show = heard
            prompt = _ENROLL[(self.enroll["take"] - 1) // 3]
            if self.enroll["take"] >= 12:
                return self._finish_enroll(prompt, heard_show)
            follow = self._prompt_take()
            follow.effects.insert(0, ("enroll", prompt, heard_show))
            return follow
        self.enroll = None
        return self._said(["Vale."])

    def _prompt_take(self) -> Turn:
        index = self.enroll["take"]
        phrase = _ENROLL[index // 3]
        said = phrase if index % 3 == 0 else f"Otra vez. {phrase}"
        return self._said([said], effects=[("enroll", phrase, "")])

    def _finish_enroll(self, prompt: str, heard_show: str) -> Turn:
        vectors = [item for item in self.enroll["vectors"] if item]
        name = self.enroll["target"] or self.enroll["spoken"]
        lock = self.embedder_ready and len(vectors) == 12
        stored = self.speakers.add(name, vectors, lock=lock)
        self.enroll = None
        if lock:
            line = f"Listo, {stored}. A partir de ahora te oigo a ti."
        else:
            line = f"Te dejo apuntado, {stored}. Sin el modelo de voz no cierro la puerta."
        return self._said([line], effects=[("enroll", prompt, heard_show)])

    def _next_wait(self) -> str:
        line = self.waits[self.settings.wait_index % len(self.waits)]
        self.settings.wait_index += 1
        self.persist()
        return line

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
            self._log_line("oí", heard)
        self._log_line("sigue", _next_step(decision, sent, detail))
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]

    def note(self, line: str) -> None:
        self._log(line)

    def _log(self, line: str) -> None:
        self._log_line("sigue", line)

    def _log_line(self, kind: str, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.logs.append(f"{stamp}  {self.mode_label()}  {kind}  {text}")
