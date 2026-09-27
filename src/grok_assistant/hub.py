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
        early = [item for item in turn.effects if item[0] != "shutdown"]
        late = [item for item in turn.effects if item[0] == "shutdown"]
        for effect in early:
            result.effects.append(effect)
            if self.on_effect:
                self.on_effect(effect)
        for line in turn.speak:
            result.spoken.append(line)
            if speaker and line:
                speaker(line)
        for effect in late:
            result.effects.append(effect)
            if self.on_effect:
                self.on_effect(effect)

    def _local_turn(self, turn: Turn) -> Turn | None:
        if turn.job is None or self.mind is None or not self.brain.settings.local_llm:
            return None
        try:
            data = self.mind.interpret(turn.job.text, self.brain.in_conversation)
        except Exception:
            self.brain._log("modelo local no respondió")
            return None
        if not data:
            return None
        accion = data.get("accion")
        self.brain._log(f"modelo local: {accion}")
        if turn.job.kind == "classify" or accion == "comando":
            self.brain.phase = ""
            return self.brain.finish_classify(data)
        if accion == "ignorar":
            self.brain.phase = ""
            self.brain._log("modelo local: se queda en casa")
            return Turn(speak=[], status=self.brain.status_label())
        if accion == "pregunta" and data.get("texto"):
            turn.job.text = data["texto"]
            self.brain._log(f"modelo local afina: {turn.job.text}")
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
            try:
                answer = self.cli.converse(
                    job.text,
                    model=self.brain.settings.model,
                    effort=job.effort,
                    session_id=session_id,
                    first=first,
                    agent_path=job.agent_path,
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
                )
            self.sent.append(("converse", job.text, job.effort, job.agent_name))
            return self.brain.finish_converse(answer)
        except GrokError as exc:
            return self.brain.finish_error(str(exc))

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
    return hub
