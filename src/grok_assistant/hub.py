"""Runs one heard phrase: local bookkeeping first, cloud only if a Job exists."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from grok_assistant.auth import AdminAuth
from grok_assistant.brain import Brain, Turn
from grok_assistant.grok_cli import GrokCLI, GrokError
from grok_assistant.local_llm import LocalMind
from grok_assistant.paths import default_agents_dir, default_data_dir, load_lines
from grok_assistant.settings import Settings
from grok_assistant.store import AgentBook, SessionStore, SpeakerBook

_ROOM_RULES = """\
# Voz

Esto es una sesión del asistente de voz, no un proyecto de código.
Responde en español hablado, corto, sin markdown.
No edites archivos. No ejecutes el shell.
"""


@dataclass
class Result:
    spoken: list[str] = field(default_factory=list)
    effects: list[tuple] = field(default_factory=list)
    sent: list[tuple] = field(default_factory=list)


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
            return None
        original = turn.job.text
        ready = self.mind.available() if hasattr(self.mind, "available") else True
        if not ready:
            if turn.job.kind == "review" and self.brain.in_conversation:
                return self._pass_through(turn, original)
            if turn.job.kind == "review":
                return Turn(status=self.brain.status_label())
            return None
        try:
            data = self.mind.interpret(original, self.brain.in_conversation)
        except Exception:
            self.brain._log("LLM: sin respuesta")
            data = None
        if data and data.get("accion") == "saludo":
            from grok_assistant.match import tokenize

            self.brain.phase = ""
            self.brain._log("LLM: saludo")
            norms = [norm for _, norm in tokenize(original)]
            return self.brain._wake(original, norms, None, logged=False)
        if data and data.get("accion") == "comando":
            from grok_assistant.match import canonicalize

            hit = canonicalize(str(data.get("orden") or ""))
            if hit is not None:
                self.brain.phase = ""
                self.brain._log(f"LLM: {hit.strict}")
                return self.brain.perform(hit)
        close = self._close_kind(original, data)
        if close:
            self.brain.phase = ""
            self.brain._log("LLM: cierre")
            return self.brain._goodbye(close)
        from grok_assistant.match import blank_phrase

        self.brain.phase = ""
        if not self.brain.in_conversation or blank_phrase(original):
            self.brain._log("LLM: se queda")
            return Turn(status=self.brain.status_label())
        self.brain._log(f"LLM: {original}")
        return self._pass_through(turn, original)

    def _identifier_ready(self) -> bool:
        if not self.brain.settings.local_llm or self.mind is None:
            return False
        if hasattr(self.mind, "available"):
            return bool(self.mind.available())
        return True

    def _close_kind(self, original: str, data: dict | None) -> str | None:
        from grok_assistant.match import blank_phrase, closer, tokenize

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
        from grok_assistant.match import blank_phrase

        if not self.brain.in_conversation or blank_phrase(original):
            self.brain._log("LLM: se queda")
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
                )
            self.sent.append(("converse", job.text, job.effort, job.agent_name))
            return self.brain.finish_converse(answer)
        except GrokError as exc:
            return self.brain.finish_error(str(exc))

    def _spoken_rules(self, job) -> str:
        from grok_assistant.i18n import agent_rules, reply_rules
        from grok_assistant.personality import voice_prompt
        from grok_assistant.prompts import AGENT_RULES, VOICE_SYSTEM

        if job.agent_path:
            base = agent_rules() or AGENT_RULES
        else:
            language = reply_rules()
            base = f"{language}\n{VOICE_SYSTEM}" if language else VOICE_SYSTEM
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


def build(data_dir: Path | None = None, agents_dir: Path | None = None, cli: GrokCLI | None = None, clock=None, wall=None) -> Hub:
    data = data_dir or default_data_dir()
    data.mkdir(parents=True, exist_ok=True)
    rules = data / "AGENTS.md"
    if not rules.exists():
        rules.write_text(_ROOM_RULES, encoding="utf-8")
    config_path = data / "config.json"
    settings = Settings.load(config_path)
    from grok_assistant.i18n import activate

    activate(getattr(settings, "language", "es"))

    def persist() -> None:
        settings.save(config_path)

    brain = Brain(
        settings,
        SessionStore(data / "sessions.json"),
        SpeakerBook(data / "speakers.json"),
        AgentBook(agents_dir or default_agents_dir(), data / "agents_state.json"),
        AdminAuth(data / "admin.json"),
        load_lines("hellos-es.txt"),
        load_lines("waits-es.txt"),
        clock=clock,
        wall=wall,
        persist=persist,
    )
    if cli is None:
        binary = GrokCLI.find()
        cli = GrokCLI(binary, data) if binary else None
    elif getattr(cli, "cwd", None) is None:
        pass
    hub = Hub(brain, cli, data)
    hub.mind = LocalMind(data)
    hub.mind.selected = settings.llm_file
    return hub
