from __future__ import annotations

from grok_assistant.ui.deps import *  # noqa: F401,F403


class PrintMixin:
    """Recording a voice print."""

    def _capture_phrase(self) -> None:
        """The next phrase comes from the ear already on the microphone."""
        if not self._arm_take_mic():
            self.hub.brain.enroll = None
            self._close_print_modal()
            self.say("No oigo el micrófono. Lo dejo.")
            self._hold_mic(False)
            self._refresh()
            return
        decision, text, audio = self._wait_print_decision()
        self._take_open = False
        if decision == "salir":
            self._abort_print()
            return
        self._hold_mic(True)
        self._end_take()
        vector = None
        if audio is not None:
            if not self.voiceprint.ready():
                self.hub.brain.enroll = None
                self._close_print_modal()
                self.say("Falta el modelo de la huella.")
                self._hold_mic(False)
                self._refresh()
                return
            try:
                vector = self.voiceprint.embed(audio)
            except Exception as exc:
                self._write_crash(exc)
        turn = self.hub.brain.accept_take(audio, vector, text)
        self._refresh()
        if self.hub.brain.enroll is not None:
            self.ui.put(self._ensure_print_modal)
        else:
            self._close_print_modal()
        for line in turn.speak:
            self.say(line)
        self._apply(turn)
        if self.hub.brain.enroll is None:
            self._close_print_modal()
            self._hold_mic(False)

    def _arm_take_mic(self) -> bool:
        if self._ears_suspended:
            self._resume_ears()
        if self.dictation is None and self.kroko is None and self.offline is None:
            self._sync_ear()
        if self.dictation is None and self.kroko is None and self.offline is None:
            self.hub.brain.note("huella: el micrófono no está abierto")
            return False
        self._hold_mic(True)
        import time

        time.sleep(0.1)
        self._drop_queued_phrases()
        while True:
            try:
                self._take_box.get_nowait()
            except queue.Empty:
                break
        self._begin_take()
        return True

    def _begin_take(self) -> None:
        """Open the microphone and beep together. The tone does not delay the ear."""
        from grok_assistant.listening.enroll_audio import play_tone

        brain = self.hub.brain
        brain.hearing = True
        brain._live_text = ""
        brain._live_open = False
        self._take_open = True
        self._set_capture(True)
        self._set_hold(True)
        self._hold_mic(False)
        threading.Thread(target=play_tone, args=(True, self.hub.brain.settings.output), daemon=True).start()
        self.ui.put(self._ensure_print_modal)
        self._refresh()

    def _end_take(self) -> None:
        """Close the long window and beep while the microphone is paused."""
        from grok_assistant.listening.enroll_audio import play_tone

        self.hub.brain.hearing = False
        self._set_hold(False)
        self._set_capture(False)
        play_tone(False, self.hub.brain.settings.output)
        self._refresh()

    def _set_capture(self, capture: bool) -> None:
        for ear in (self.kroko, self.offline):
            if ear is not None:
                ear.set_capture(capture)

    def _set_hold(self, hold: bool) -> None:
        for ear in (self.kroko, self.offline):
            if ear is not None and hasattr(ear, "set_hold"):
                ear.set_hold(hold)

    def _wait_print_decision(self) -> tuple[str, str, object]:
        """Seguir keeps this phrase. Reintentar records it again. Salir drops the session."""
        pending = []
        while True:
            try:
                pending.append(self._print_wait.get_nowait())
            except queue.Empty:
                break
        if "salir" in pending:
            return "salir", "", None
        pending_text, pending_audio = "", None
        while True:
            try:
                decision = self._print_wait.get(timeout=0.15)
            except queue.Empty:
                decision = ""
            while True:
                try:
                    text, audio = self._take_box.get_nowait()
                except queue.Empty:
                    break
                if audio is not None and time.monotonic() >= self._drop_take_audio:
                    pending_text, pending_audio = str(text or ""), audio
                    self.ui.put(lambda heard=pending_text: self._set_print_heard(heard))
            if decision == "salir":
                return "salir", "", None
            if decision == "reintentar":
                extra = []
                while True:
                    try:
                        extra.append(self._print_wait.get_nowait())
                    except queue.Empty:
                        break
                if "salir" in extra:
                    return "salir", "", None
                self._restart_print_listen()
                pending_text, pending_audio = "", None
                continue
            if decision != "seguir":
                continue
            if pending_audio is None:
                self._flush_open_ear()
                try:
                    text, audio = self._take_box.get(timeout=1.2)
                except queue.Empty:
                    text, audio = "", None
                if audio is not None:
                    pending_text, pending_audio = str(text or ""), audio
            if pending_audio is None:
                self.ui.put(lambda: self._set_print_hint(_ui("dialog.print_wait", "Aún no oigo. Di la frase y pulsa Seguir.")))
                continue
            return "seguir", pending_text, pending_audio

    def _abort_print(self) -> None:
        self._take_open = False
        self._set_hold(False)
        self._end_take()
        self._hold_mic(False)
        turn = self.hub.brain.discard_capture()
        self._close_print_modal()
        for line in turn.speak:
            self.say(line)
        self._refresh()

    def _ensure_print_modal(self) -> None:
        enroll = self.hub.brain.enroll
        if not isinstance(enroll, dict) or enroll.get("stage") != "takes":
            self._close_print_modal()
            return
        if self._print_win is None or not self._print_win.winfo_exists():
            win = tk.Toplevel(self.root)
            win.title(_ui("dialog.print_name", "Huella"))
            win.configure(bg=look.bg)
            win.resizable(False, False)
            win.protocol("WM_DELETE_WINDOW", self._print_leave)
            self._print_count = tk.StringVar(master=win)
            self._print_phrase = tk.StringVar(master=win)
            self._print_heard = tk.StringVar(master=win)
            self._print_hint = tk.StringVar(master=win)
            ttk.Label(win, textvariable=self._print_count, style="Muted.TLabel").pack(anchor="w", padx=18, pady=(16, 0))
            ttk.Label(win, text=_ui("dialog.print_say", "Di esta frase"), style="Muted.TLabel").pack(anchor="w", padx=18, pady=(10, 0))
            tk.Label(
                win, textvariable=self._print_phrase, bg=look.bg, fg=look.amber,
                font=("Segoe UI", 22, "bold"), wraplength=460, justify="left",
            ).pack(anchor="w", padx=18, pady=(8, 4))
            ttk.Label(win, text=_ui("dialog.print_heard", "Oído"), style="Muted.TLabel").pack(anchor="w", padx=18, pady=(12, 0))
            tk.Label(
                win, textvariable=self._print_heard, bg=look.field, fg=look.ink, font=look.font,
                wraplength=460, justify="left", anchor="nw", padx=10, pady=8, height=2,
            ).pack(fill="x", padx=18, pady=(4, 0))
            ttk.Label(win, textvariable=self._print_hint, style="Muted.TLabel").pack(anchor="w", padx=18, pady=(8, 0))
            row = ttk.Frame(win)
            row.pack(fill="x", padx=18, pady=16)
            RoundButton(row, text=_ui("dialog.print_retry", "Reintentar"), command=self._print_retry, padx=18, pady=8).pack(side="left")
            RoundButton(row, text=_ui("dialog.print_next", "Seguir"), command=self._print_next, padx=18, pady=8).pack(side="left", padx=(12, 0))
            RoundButton(row, text=_ui("dialog.print_leave", "Salir"), command=self._print_leave, padx=18, pady=8).pack(side="right")
            self._print_win = win
            self.root.deiconify()
            win.update_idletasks()
            win.geometry("520x320")
            win.grab_set()
            win.lift()
        self._fill_print_modal()

    def _fill_print_modal(self) -> None:
        enroll = self.hub.brain.enroll
        if self._print_win is None or not isinstance(enroll, dict):
            return
        index = int(enroll.get("take") or 0)
        phrases = self.hub.brain._phrases()
        total = len(phrases)
        phrase = phrases[index] if 0 <= index < total else ""
        count = _ui("dialog.print_count", "{n} de {total}").replace("{n}", str(index + 1)).replace("{total}", str(total))
        self._print_count.set(count)
        self._print_phrase.set(phrase)
        self._print_hint.set("")
        self._print_heard.set(self.hub.brain._live_text or "")

    def _set_print_heard(self, heard: str) -> None:
        if self._print_win is None or not self._print_win.winfo_exists():
            return
        self._print_heard.set(heard)
        if hasattr(self, "_print_hint"):
            self._print_hint.set("")

    def _set_print_hint(self, hint: str) -> None:
        if self._print_win is None or not self._print_win.winfo_exists():
            return
        self._print_hint.set(hint)

    def _print_next(self) -> None:
        self._print_wait.put("seguir")

    def _print_retry(self) -> None:
        self._print_wait.put("reintentar")

    def _print_leave(self) -> None:
        self._print_wait.put("salir")

    def _restart_print_listen(self) -> None:
        """Drop only this phrase and listen for it again. Earlier phrases stay."""
        from grok_assistant.listening.enroll_audio import play_tone

        self._drop_take_audio = time.monotonic() + 0.35
        self._hold_mic(True)
        time.sleep(0.15)
        while True:
            try:
                self._take_box.get_nowait()
            except queue.Empty:
                break
        brain = self.hub.brain
        brain._live_text = ""
        brain._live_open = False
        self._set_capture(True)
        self._set_hold(True)
        self._hold_mic(False)
        threading.Thread(target=play_tone, args=(True, self.hub.brain.settings.output), daemon=True).start()
        self.ui.put(self._mark_print_retry)

    def _mark_print_retry(self) -> None:
        self._set_print_heard("")
        self._set_print_hint(_ui("dialog.print_again", "Otra vez. Habla después del pitido."))

    def _close_print_modal(self) -> None:
        def close() -> None:
            win = self._print_win
            self._print_win = None
            if win is not None and win.winfo_exists():
                try:
                    win.grab_release()
                except tk.TclError:
                    pass
                win.destroy()

        self.ui.put(close)

    def _flush_open_ear(self) -> None:
        """The wait ran out. Keep whatever sound the open ear already caught."""
        for ear in (self.kroko, self.offline):
            flush = getattr(ear, "request_flush", None)
            if flush is not None:
                flush()

    def _drop_queued_phrases(self) -> None:
        kept = []
        while True:
            try:
                item = self.jobs.get_nowait()
            except queue.Empty:
                break
            if item[0] != "phrase":
                kept.append(item)
        for item in kept:
            self.jobs.put(item)

    def _suspend_ears(self) -> None:
        self._ears_suspended = True
        ears = [self.dictation, self.kroko, self.offline]
        for ear in ears:
            if ear is not None:
                ear.stop()
        for ear in ears:
            thread = getattr(ear, "_thread", None) if ear is not None else None
            if thread is not None:
                thread.join(timeout=2)
        self.dictation = None
        self.kroko = None
        self.offline = None

    def _resume_ears(self) -> None:
        if not self._ears_suspended:
            return
        self._ears_suspended = False
        self._sync_ear()

    def _score_person_later(self, name: str) -> None:
        threading.Thread(target=self._score_named, args=(name, None), daemon=True).start()

    def _score_pending(self) -> None:
        self._score_named("", None)

    def _score_named(self, name: str, only_ear: str | None) -> None:
        from grok_assistant.listening.ear_score import score_person

        book = self.hub.brain.speakers
        microphone = self.hub.brain.settings.microphone
        lines: list[str] = []
        with self._score_lock:
            ears = [ear for ear in self.hub.brain.recognizers if ear != "teclado"]
            if only_ear:
                pending = [(name, only_ear)] if book.raw_clips(name, microphone) else []
            elif name:
                pending = [
                    (name, ear)
                    for ear in ears
                    if book.raw_clips(name, microphone) and book.score_of(name, ear, microphone) is None
                ]
            else:
                pending = book.pending_scores(ears, microphone)
            for person, ear in pending:
                signature = tuple(clip["file"] for clip in book.raw_clips(person, microphone))
                try:
                    hits, total = score_person(book, person, ear, microphone=microphone)
                except Exception as exc:
                    self._write_crash(exc)
                    continue
                current = tuple(clip["file"] for clip in book.raw_clips(person, microphone))
                if current != signature:
                    book.drop_score(person, ear, microphone)
                    continue
                if not total:
                    continue
                label = _ui(f"ear.{ear}", ear)
                percent = round(100 * hits / total)
                lines.append(f"{label} {hits} de {total}")
                self.ui.put(lambda person=person, label=label, percent=percent: self._note(f"{person} · {label}: {percent}%"))
        if lines and name:
            self.jobs.put(("speak", ". ".join(lines) + "."))
        if lines:
            self.ui.put(self._apply_best_ear)

    def _hold_mic(self, hold: bool) -> None:
        self._mic_held = bool(hold)
        self._push_mic_pause()

    def _push_mic_pause(self) -> None:
        paused = self._mic_held or self.user_paused
        if self.dictation is not None:
            self.dictation.set_paused(paused)
        if self.kroko is not None:
            self.kroko.set_paused(paused)
        if self.offline is not None:
            self.offline.set_paused(paused)
