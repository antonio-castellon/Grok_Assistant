"""Runs one heard phrase: local bookkeeping first, cloud only if a Job exists."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from grok_assistant.notebook.auth import AdminAuth
from grok_assistant.rules.brain import Brain, Turn
from grok_assistant.cloud.grok_cli import GrokCLI, GrokError
from grok_assistant.mind.local_llm import LocalMind
from grok_assistant.paths import default_account_agents_dir, default_agents_dir, default_data_dir, load_lines, speakers_file
from grok_assistant.notebook.settings import Settings
from grok_assistant.notebook.store import AgentBook, SessionStore, SpeakerBook

_ROOM_RULES = """\
# Voz

Esto es una sesión del asistente de voz, no un proyecto de código.
Responde en español hablado, corto, sin markdown.
No edites archivos. No ejecutes el shell.
"""

_ROOM_RULES_ON = """\
# Voz

Esto es una sesión del asistente de voz, no un proyecto de código.
Responde en español hablado, corto, sin markdown.
Puedes leer y cambiar archivos si la persona lo pide.
No ejecutes el shell. No instales programas. No borres una carpeta entera.
Una ruta relativa queda en esta carpeta.
"""


def write_room_rules(folder: Path, files: bool) -> None:
    text = _ROOM_RULES_ON if files else _ROOM_RULES
    (folder / "AGENTS.md").write_text(text, encoding="utf-8")


@dataclass
class Result:
    spoken: list[str] = field(default_factory=list)
    effects: list[tuple] = field(default_factory=list)
    sent: list[tuple] = field(default_factory=list)


def _intent_line(data: dict | None, heard: str = "") -> str:
    """One debug line: what the local model returned."""
    if not data:
        return "LLM: sin respuesta"
    accion = " ".join(str(data.get("accion") or "").split()) or "vacío"
    if accion == "ilegible":
        return "LLM: ilegible"
    bits = [accion]
    orden = " ".join(str(data.get("orden") or "").split())
    texto = " ".join(str(data.get("texto") or "").split())
    heard_fold = " ".join(heard.split()).casefold()
    if orden:
        bits.append(orden)
    if texto and texto.casefold() not in {orden.casefold(), heard_fold}:
        bits.append(texto)
    return "LLM: " + " · ".join(bits)


class Hub:
    def __init__(self, brain: Brain, cli: GrokCLI | None, data_dir: Path):
        self.brain = brain
        self.cli = cli
        self.data_dir = data_dir
        self.on_effect = None
        self.mind = None
        self.sent: list[tuple] = []

    def startup(self) -> str:
        return self.brain.startup_line()

    def run(self, text: str, speaker=None, **kwargs) -> Result:
        self.brain.identifier_ready = self._identifier_ready()
        self.brain.mark_busy()
        try:
            turn = self.brain.handle(text, **kwargs)
            return self._play(turn, speaker)
        finally:
            self.brain.mark_idle()

    def set_grok_files(self, allow: bool, speaker=None) -> Result:
        self.brain.mark_busy()
        try:
            return self._play(self.brain.set_grok_files(allow), speaker)
        finally:
            self.brain.mark_idle()

    def submit_password(self, password: str, speaker=None) -> Result:
        self.brain.mark_busy()
        try:
            return self._play(self.brain.submit_password(password), speaker)
        finally:
            self.brain.mark_idle()

    def cancel_password(self, speaker=None) -> Result:
        return self._play(self.brain.cancel_password(), speaker)

    def tick(self, speaker=None) -> Result:
        return self._play(self.brain.tick(), speaker)

    def _play(self, turn: Turn, speaker) -> Result:
        result = Result()
        local = self._local_turn(turn)
        if local is not None:
            turn = local
        self._emit(turn, speaker, result)
        if turn.job:
            follow = self._cloud(turn)
            self._emit(follow, speaker, result)
        return result

    def _emit(self, turn: Turn, speaker, result: Result) -> None:
        for effect in turn.effects:
            result.effects.append(effect)
            if self.on_effect:
                self.on_effect(effect)
        for line in turn.speak:
            result.spoken.append(line)
            if speaker and line:
                speaker(line)

    def _local_turn(self, turn: Turn) -> Turn | None:
        if turn.job is None or self.mind is None or not self.brain.settings.local_llm:
            return None
        if turn.job.kind == "converse":
            self._note_open(turn)
            return None
        original = turn.job.text
        ready = self.mind.available() if hasattr(self.mind, "available") else True
        if not ready:
            if turn.job.kind == "review" and self.brain.in_conversation:
                self.brain._log("LLM: sin modelo")
                return self._pass_through(turn, original)
            if turn.job.kind == "review":
                self.brain._log("LLM: sin modelo")
                return Turn(status=self.brain.status_label())
            return None
        data = self._ask_model(original, self.brain.in_conversation)
        if data and data.get("accion") == "saludo":
            from grok_assistant.rules.match import tokenize

            self.brain.phase = ""
            self.brain._log(_intent_line(data, original))
            norms = [norm for _, norm in tokenize(original)]
            return self.brain._wake(original, norms, None, logged=False)
        if data and data.get("accion") == "comando":
            from grok_assistant.rules.match import canonicalize

            hit = canonicalize(str(data.get("orden") or ""))
            if hit is not None:
                self.brain.phase = ""
                self.brain._log(_intent_line(data, original))
                return self.brain.perform(hit)
        close = self._close_kind(original, data)
        if close:
            self.brain.phase = ""
            self.brain._log(_intent_line(data, original))
            return self.brain._goodbye(close)
        from grok_assistant.rules.match import blank_phrase

        self.brain.phase = ""
        stays = not self.brain.in_conversation or blank_phrase(original)
        self.brain._log(_intent_line(data, original))
        if stays:
            return Turn(status=self.brain.status_label())
        return self._pass_through(turn, original)

    def _note_open(self, turn: Turn) -> None:
        """Write the local reading under a phrase that still goes to Grok."""
        original = turn.job.text if turn.job is not None else ""
        ready = self.mind.available() if hasattr(self.mind, "available") else True
        if not ready:
            self.brain._log("LLM: sin modelo")
            return
        data = self._ask_model(original, True)
        self.brain._log(_intent_line(data, original))

    def _ask_model(self, phrase: str, in_conversation: bool) -> dict | None:
        state = "abierta" if in_conversation else "cerrada"
        try:
            self.mind.wake_name = self.brain.settings.wake_name
            data = self.mind.interpret(phrase, in_conversation)
        except Exception:
            data = None
        raw = ""
        if isinstance(data, dict):
            raw = str(data.pop("_raw", "") or "")
        self.brain.note_model(phrase, state, raw, data if isinstance(data, dict) else None)
        return data if isinstance(data, dict) else None

    def _identifier_ready(self) -> bool:
        if not self.brain.settings.local_llm or self.mind is None:
            return False
        if hasattr(self.mind, "available"):
            return bool(self.mind.available())
        return True

    def _close_kind(self, original: str, data: dict | None) -> str | None:
        from grok_assistant.rules.match import blank_phrase, closer, tokenize

        heard = closer([norm for _, norm in tokenize(original)])
        if heard:
            return heard
        if not data or data.get("accion") != "cierre":
            return None
        orden = str(data.get("orden") or "").lower()
        if "gracias" in orden:
            return "denada"
        if orden in {"vale", "ok"}:
            return "vale"
        return "adios"

    def _pass_through(self, turn: Turn, original: str) -> None:
        from grok_assistant.rules.match import blank_phrase

        if not self.brain.in_conversation or blank_phrase(original):
            return Turn(status=self.brain.status_label())
        turn.job.kind = "converse"
        turn.job.text = original
        turn.speak = [self.brain._next_wait()]
        return None

    def _cloud(self, turn: Turn) -> Turn:
        job = turn.job
        if job is None:
            return Turn()
        if self.cli is None:
            return self.brain.finish_error("no encuentro el comando grok")
        files = bool(self.brain.settings.grok_files)
        write_room_rules(self.data_dir, files)
        try:
            if job.kind == "classify":
                data = self.cli.classify(job.text, self.brain.settings.model)
                self.sent.append(("classify", job.text))
                return self.brain.finish_classify(data)
            session_id, first = self._slot(job)
            spoken = self._spoken_rules(job)
            try:
                answer = self.cli.converse(
                    job.text,
                    model=self.brain.settings.model,
                    effort=job.effort,
                    session_id=session_id,
                    first=first,
                    agent_path=job.agent_path,
                    system=spoken,
                    files=files,
                )
            except GrokError:
                if first:
                    raise
                session_id = self._reset_slot(job)
                answer = self.cli.converse(
                    job.text,
                    model=self.brain.settings.model,
                    effort=job.effort,
                    session_id=session_id,
                    first=True,
                    agent_path=job.agent_path,
                    system=spoken,
                    files=files,
                )
            self.sent.append(("converse", job.text, job.effort, job.agent_name))
            return self.brain.finish_converse(answer)
        except GrokError as exc:
            return self.brain.finish_error(str(exc))

    def _spoken_rules(self, job) -> str:
        from grok_assistant.i18n import agent_rules, reply_rules
        from grok_assistant.house.personality import voice_prompt
        from grok_assistant.cloud.prompts import AGENT_RULES, spoken_agent_rules, voice_rules

        files = bool(self.brain.settings.grok_files)
        if job.agent_path:
            base = spoken_agent_rules(agent_rules() or AGENT_RULES, files)
        else:
            language = reply_rules()
            voice = voice_rules(files)
            base = f"{language}\n{voice}" if language else voice
        return voice_prompt(self.brain.settings.personality, base)

    def _slot(self, job) -> tuple[str, bool]:
        if job.slot == "agent" and job.agent_name:
            existing = self.brain.agents.grok_id(job.agent_name, mint=False)
            if existing:
                return existing, False
            return self.brain.agents.grok_id(job.agent_name, mint=True), True
        existing = self.brain.sessions.grok_id(mint=False)
        if existing:
            return existing, False
        return self.brain.sessions.grok_id(mint=True), True

    def _reset_slot(self, job) -> str:
        if job.slot == "agent" and job.agent_name:
            return self.brain.agents.reset_grok_id(job.agent_name)
        return self.brain.sessions.reset_grok_id()


def build(data_dir: Path | None = None, agents_dir: Path | None = None, cli: GrokCLI | None = None, clock=None, wall=None, account_dir: Path | None = None) -> Hub:
    data = data_dir or default_data_dir()
    data.mkdir(parents=True, exist_ok=True)
    config_path = data / "config.json"
    settings = Settings.load(config_path)
    from grok_assistant.i18n import activate

    activate(getattr(settings, "language", "es"))

    def persist() -> None:
        settings.save(config_path)

    brain = Brain(
        settings,
        SessionStore(data / "sessions.json"),
        SpeakerBook(speakers_file() if data_dir is None else data / "speakers.json"),
        AgentBook(
            agents_dir or default_agents_dir(),
            data / "agents_state.json",
            default_account_agents_dir() if account_dir is None else account_dir,
            data / "account-agents",
        ),
        AdminAuth(data / "admin.json"),
        load_lines("hellos-es.txt"),
        ["Un momento."],
        clock=clock,
        wall=wall,
        persist=persist,
    )
    brain.room_dir = data
    write_room_rules(data, bool(settings.grok_files))
    if cli is None:
        binary = GrokCLI.find()
        cli = GrokCLI(binary, data) if binary else None
    elif getattr(cli, "cwd", None) is None:
        pass
    hub = Hub(brain, cli, data)
    hub.mind = LocalMind(data)
    hub.mind.selected = settings.llm_file
    return hub
