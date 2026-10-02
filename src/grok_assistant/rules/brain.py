"""The house rules, split by what they decide."""

from __future__ import annotations

import time

from grok_assistant.rules.common import Job, Turn
from grok_assistant.rules.orders import OrderMixin
from grok_assistant.rules.prints import PrintMixin
from grok_assistant.rules.status import StatusMixin
from grok_assistant.rules.talk import TalkMixin
from grok_assistant.rules.trace import TraceMixin

__all__ = ["Brain", "Job", "Turn"]


class Brain(TraceMixin, PrintMixin, OrderMixin, TalkMixin, StatusMixin):
    """One heard phrase, decided here before any cloud call."""

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
        self.room_dir = None
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
        self.heard_clips: list[dict] = []
        self.model_notes: list[dict] = []
        self._flow_heard = ""
        self.hearing = False
        self.sessions.roll(self.wall(), self.settings.shared_days)
        self._live_open = False
        self._live_text = ""
