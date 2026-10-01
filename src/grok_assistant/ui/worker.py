from __future__ import annotations

from grok_assistant.ui.deps import *  # noqa: F401,F403


class WorkerMixin:
    """The queue that speaks, logs, and applies effects."""

    def _worker(self) -> None:
        while True:
            item = self.jobs.get()
            if item[0] == "stop":
                break
            kind = item[0]
            payload = item[1] if len(item) > 1 else ""
            embedding = item[2] if len(item) > 2 else None
            speaker_id = item[3] if len(item) > 3 else None
            heard_by = item[4] if len(item) > 4 else ""
            try:
                self._job(kind, payload, embedding, speaker_id, heard_by)
            except Exception as exc:
                self._write_crash(exc)

    def _write_crash(self, exc: Exception) -> None:
        import traceback
        from grok_assistant.paths import default_data_dir

        path = default_data_dir() / "crash.log"
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(traceback.format_exc())
                handle.write("\n")
        except OSError:
            return
        self.ui.put(lambda: self._note(f"fallo interno: {exc}"))

    def _job(self, kind: str, payload: str, embedding, speaker_id=None, heard_by: str = "") -> None:
        if kind == "note":
            self._note(payload)
            self._refresh()
            return
        if kind == "startup":
            self.say(self.hub.startup())
            self._refresh()
            return
        if kind == "tick":
            result = self.hub.tick(speaker=self.say)
            self._apply(result)
            self._refresh()
            return
        if kind == "rename":
            turn = self.hub.brain.rename_typed(payload)
            for line in turn.speak:
                self.say(line)
            self._note(f"nombre: {self.hub.brain.settings.wake_name}")
            self._refresh()
            return
        if kind == "capture":
            turn = self.hub.brain.start_capture(payload, speaker_id)
            for line in turn.speak:
                self.say(line)
            self._apply(turn)
            if self.hub.brain.enroll is None:
                self._resume_ears()
            self._refresh()
            return
        if kind == "speak":
            self.say(payload)
            self._refresh()
            return
        if kind == "files":
            result = self.hub.set_grok_files(payload == "1", speaker=self.say)
            self._apply(result)
            if any(item[0] == "ask_password" for item in result.effects):
                password = self._ask(_ui("dialog.admin", "Administrador"))
                follow = self.hub.submit_password(password, speaker=self.say) if password else self.hub.cancel_password(speaker=self.say)
                self._apply(follow)
            self._refresh()
            return
        if kind == "phrase":
            self._hold_mic(True)
            try:
                result = self.hub.run(payload, speaker=self.say, vector=embedding, speaker_id=speaker_id)
                self._apply(result)
                if any(item[0] == "ask_password" for item in result.effects):
                    password = self._ask(_ui("dialog.admin", "Administrador"))
                    follow = self.hub.submit_password(password, speaker=self.say) if password else self.hub.cancel_password(speaker=self.say)
                    self._apply(follow)
            finally:
                self._hold_mic(False)
            if heard_by:
                self.hub.brain._step(heard_by)
            self._refresh()

    def say(self, text: str) -> None:
        if not text:
            return
        self.music.hold_for_speech()
        try:
            voice = self._voice_name()
            ok = self.speaker.say(text, None if voice == "Predeterminada" else voice, self.hub.brain.settings.volume)
            if not ok:
                self._note(f"no pude decir: {text}")
        finally:
            self.music.release_after_speech()

    def _play_song(self, title: str) -> None:
        def status(message: str) -> None:
            self.ui.put(lambda message=message: self.say(message))

        trouble = self.music.play(title, self.hub.brain.settings.volume, status)
        if trouble:
            self.ui.put(lambda trouble=trouble: self.say(trouble))
            return
        self._music_note = False
        self.ui.put(lambda: self._note("la música suena. Sigo oyendo solo una voz registrada."))

    def _voice_name(self) -> str:
        voices = self.hub.brain.voices
        index = self.hub.brain.settings.voice_index
        if not voices:
            return ""
        return voices[min(index, len(voices) - 1)]

    def _apply(self, result) -> None:
        for effect in result.effects:
            kind = effect[0]
            if kind == "record_take":
                self._capture_phrase()
            elif kind == "score_prints":
                self._score_person_later(effect[1])
            elif kind == "play":
                title = effect[1]
                threading.Thread(target=lambda title=title: self._play_song(title), daemon=True).start()
            elif kind == "pause_music":
                self.music.pause()
            elif kind == "resume_music":
                self.music.resume()
            elif kind == "stop_music":
                self.music.stop()
            elif kind == "recognizer":
                self._sync_ear()

    def _send(self, _event=None) -> None:
        text = self.entry.get().strip()
        self.entry.delete(0, "end")
        if text:
            self.jobs.put(("phrase", text))

    def _poll_usage(self) -> None:
        def work() -> None:
            from grok_assistant.cloud.account_usage import fetch_account_percent

            percent = fetch_account_percent()

            def apply() -> None:
                self._usage_known = True
                self._usage_percent = percent
                self._show_usage()

            self.ui.put(apply)

        threading.Thread(target=work, daemon=True).start()
        self.root.after(60_000, self._poll_usage)

    def _pulse(self) -> None:
        if self._closing:
            return
        while True:
            try:
                job = self.ui.get_nowait()
            except queue.Empty:
                break
            try:
                job()
            except tk.TclError:
                continue
            except Exception as exc:
                self._write_crash(exc)
        self.jobs.put(("tick", ""))
        self._paint()
        delay = 120 if self.hub.brain.hearing else 400
        self.root.after(delay, self._pulse)

    def _refresh(self) -> None:
        self.ui.put(self._paint)

    def _paint(self) -> None:
        try:
            snap = self.hub.brain.snapshot()
        except tk.TclError:
            return
        self.status_var.set(snap["status"])
        self.state_var.set(snap.get("banner") or _ui("status.banner_wait", "ESPERA"))
        kind = snap.get("banner_kind") or "wait"
        self.state_label.configure(fg={"talk": look.green, "hear": look.green, "pause": look.amber, "test": look.amber}.get(kind, look.teal))
        self._refresh_market_marks()
        self.detail_var.set(
            f"{snap['model']}  ·  {snap['effort']}  ·  {snap['voice']}  ·  {snap['recognizer']}  ·  {snap['identifier']}  ·  {snap['session']}  ·  {snap['volume']}%"
        )
        self._draw_flow(snap)
        if self.tray_ok and self.tray is not None:
            self.tray.set_tip(f"Grok Assistant — {_version_line()} — {snap['status']}")
        if self.debug_text is None:
            return
        shown = self.hub.brain.logs[-500:]
        if shown == self._debug_cache:
            return
        self._debug_cache = list(shown)
        self.debug_text.configure(state="normal")
        self.debug_text.delete("1.0", "end")
        for line in shown:
            self._insert_log(line)
        self.debug_text.configure(state="disabled")
        self.debug_text.see("end")

    def _insert_log(self, line: str) -> None:
        parts = line.split("  ", 2)
        if len(parts) == 3 and parts[1] in {"·", "¦"}:
            stamp, kind, rest = parts
            self.debug_text.insert("end", stamp + " ", "time")
            if kind == "¦":
                self.debug_text.insert("end", "  ¦-- " + rest.strip() + "\n", "sigue")
            else:
                self.debug_text.insert("end", rest.strip() + "\n")
            return
        older = line.split("  ", 3)
        if len(older) == 4 and older[2].strip() in {"oí", "sigue"}:
            stamp, mode, kind, rest = older[0], older[1].strip(), older[2].strip(), older[3]
            self.debug_text.insert("end", stamp + "  ", "time")
            self.debug_text.insert("end", mode.ljust(18), "mode")
            self.debug_text.insert("end", "  " + kind.ljust(6), "oi" if kind == "oí" else "sigue")
            self.debug_text.insert("end", rest.strip() + "\n")
            return
        older = line.split("  ", 2)
        if len(older) == 3 and older[1].strip() in {"oí", "sigue"}:
            stamp, kind, rest = older[0], older[1].strip(), older[2]
            self.debug_text.insert("end", stamp + "  ", "time")
            self.debug_text.insert("end", kind.ljust(6), "oi" if kind == "oí" else "sigue")
            self.debug_text.insert("end", rest.strip() + "\n")
            return
        self.debug_text.insert("end", line + "\n")

    def _clear_view(self) -> None:
        self.view_from = len(self.hub.brain.logs)
        self._paint()

    def _toggle_from_ui(self) -> None:
        self.user_paused = not self.user_paused
        self.hub.brain.set_paused(self.user_paused)
        self._sync_ear()
        self.pause_button.configure(text=self._pause_caption(False))
        self.simple_pause.configure(text=self._pause_caption(True))
        self._note("escucha en pausa" if self.user_paused else "vuelvo a escuchar")
        self._paint()
