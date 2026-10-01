"""Names the window methods use. Loaded once, when the window starts."""

from __future__ import annotations

import os
import queue
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from grok_assistant.house.helptext import help_topics
from grok_assistant.house.marketplace import Offer, download, offers, offers_for
from grok_assistant.house.music import Music
from grok_assistant.listening.kroko_ear import STREAMING_KINDS, KrokoEar
from grok_assistant.listening.listen import (
    EAR_LANG,
    RECOGNIZER_LABELS,
    Dictation,
    discover_recognizers,
    eligible_ears,
    highest_accuracy,
    install_windows_speech,
    preferred_recognizer,
    with_accuracy,
)
from grok_assistant.listening.offline_ear import OFFLINE_KINDS, OfflineEar
from grok_assistant.listening.refine import Refiner, pick_transcript
from grok_assistant.listening.voiceprint import VoicePrint
from grok_assistant.paths import bundle_root
from grok_assistant.rules.hub import Hub, build
from grok_assistant.speaking.speech import Speaker
from grok_assistant.ui.chrome import _agent_label, _outside_clause, _ui, _used, _version_line, look
from grok_assistant.ui.round import RoundButton, RoundNotebook
from grok_assistant.ui.theme import apply_saved, available, theme_by_id
from grok_assistant.ui.win_tray import WinTray

__all__ = [name for name in globals() if not name.startswith("__")]
