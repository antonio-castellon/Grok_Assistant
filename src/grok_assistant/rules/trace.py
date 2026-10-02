from __future__ import annotations

from grok_assistant.rules.common import *  # noqa: F401,F403


class TraceMixin:
    """The debug log and the flow snapshot notes."""

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

    def keep_heard(self, heard: str, samples, *, primary: str = "", second: str = "", heard_by: str = "", who: str | None = None) -> None:
        """Remember one closed phrase so a later trace can include its wav."""
        if samples is None:
            return
        try:
            import numpy as np

            audio = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        except (TypeError, ValueError):
            return
        if audio.size == 0:
            return
        if audio.size > 16000 * 30:
            audio = audio[-16000 * 30:]
        clips = getattr(self, "heard_clips", None)
        if clips is None:
            clips = []
            self.heard_clips = clips
        clips.append({
            "ts": self.wall(),
            "heard": " ".join((heard or "").split()),
            "primary": " ".join((primary or "").split()),
            "second": " ".join((second or "").split()),
            "heard_by": heard_by or "",
            "who": who or "",
            "audio": audio,
        })
        while len(clips) > 40:
            clips.pop(0)
        total = sum(item["audio"].size for item in clips)
        while clips and total > 16000 * 180:
            total -= clips.pop(0)["audio"].size

    def note_model(self, phrase: str, state: str, raw: str, parsed: dict | None) -> None:
        """The local model's own text, kept for a trace. The screen still shows the short line."""
        clean = None
        if isinstance(parsed, dict):
            clean = {
                "accion": " ".join(str(parsed.get("accion") or "").split()),
                "orden": " ".join(str(parsed.get("orden") or "").split()),
                "texto": " ".join(str(parsed.get("texto") or "").split()),
            }
        notes = getattr(self, "model_notes", None)
        if notes is None:
            notes = []
            self.model_notes = notes
        notes.append({
            "ts": self.wall(),
            "phrase": phrase,
            "state": state,
            "raw": raw or "",
            "parsed": clean,
        })
        if len(notes) > 80:
            del notes[:-80]
