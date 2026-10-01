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
