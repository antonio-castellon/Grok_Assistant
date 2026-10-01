from __future__ import annotations

from grok_assistant.ui.deps import *  # noqa: F401,F403


class FlowMixin:
    """The flow drawing."""

    def _draw_flow(self, snap: dict | None) -> None:
        canvas = getattr(self, "flow", None)
        if canvas is None:
            return
        if snap is None:
            snap = self._flow_snap
        if snap is None:
            return
        self._flow_snap = snap
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 80 or height < 80:
            return
        canvas.delete("all")
        ear = self.hub.brain.settings.recognizer
        kind = snap.get("banner_kind") or "wait"
        paused = kind == "pause"
        testing = kind == "test"
        talking = kind == "talk"
        keyboard = ear == "teclado"
        alive = not paused

        def clip(value: str, limit: int = 46) -> str:
            value = value or ""
            return value if len(value) <= limit else value[: limit - 1] + "…"

        def library_for_ear() -> str:
            if ear == "windows":
                return _ui("flow.lib_speech", "Windows Speech")
            if ear == "teclado":
                return _ui("flow.skip", "no entra")
            return "sherpa-onnx"

        voice_raw = snap.get("voice") or ""
        voice_name = voice_raw.split(". ", 1)[-1] if ". " in voice_raw else voice_raw
        try:
            from grok_assistant.speaking.speech import _piper_by_label

            piper = voice_name in _piper_by_label()
        except Exception:
            piper = False
        if piper:
            voice_lib = "Piper"
        elif os.name == "nt":
            voice_lib = _ui("flow.lib_speech", "Windows Speech")
        else:
            voice_lib = "espeak"
        local_name = snap.get("identifier") or ""
        if local_name == _ui("status.no_identifier", "sin identificador"):
            local_detail = _ui("flow.lib_none", "sin modelo")
        else:
            local_detail = clip(f"{local_name} · llama.cpp")

        try:
            talk_mode = self.hub.brain.settings.talk_mode or ""
        except Exception:
            talk_mode = ""
        open_chat = talk_mode == "abierta"
        pad = 16
        caption = _ui("flow.caption", "")
        if paused:
            caption = _ui("flow.pause", caption)
        elif testing:
            caption = _ui("flow.test", caption)
        elif open_chat:
            caption = _ui(
                "flow.abierta_caption",
                "Charla abierta: el texto va directo a Grok. El modelo local no decide.",
            )
        canvas.create_text(
            pad, 8, anchor="nw", text=caption,
            fill=look.amber if paused or testing else look.muted,
            font=("Segoe UI", 11), width=max(240, width - pad * 2),
        )
        top = 56 if open_chat and not paused and not testing else 34
        avail = max(height - top - 8, 240)
        gap = 8
        box_h = max(46, min(64, int((avail - gap * 7) / 6.4)))
        inner = width - pad * 2
        half = (inner - 12) / 2

        def box(x, y, bw, bh, title, detail, on, size=12):
            canvas.create_rectangle(x, y, x + bw, y + bh, fill=look.flow_on if on else look.field, outline=look.teal if on else look.flow_off, width=2)
            canvas.create_text(x + bw / 2, y + bh * 0.34, text=title, fill=look.ink if on else look.muted, font=("Segoe UI", size, "bold"), width=bw - 14)
            canvas.create_text(x + bw / 2, y + bh * 0.70, text=detail, fill=look.teal if on else look.muted, font=("Segoe UI", max(9, size - 2)), width=bw - 14)

        def down(x, y1, y2, on):
            canvas.create_line(x, y1, x, y2, fill=look.amber if on else look.button_active, width=2, arrow="last", arrowshape=(10, 12, 4))

        y = top
        mic_on = alive and not keyboard
        key_on = alive and keyboard
        box(pad, y, half, box_h, _ui("flow.mic", "Micrófono"), "sounddevice · campplus", mic_on)
        box(pad + half + 12, y, half, box_h, _ui("flow.keys", "Teclado"), _ui("flow.keys_note", "ya es texto"), key_on)
        y += box_h
        down(pad + half / 2, y, y + gap + 2, mic_on)
        down(pad + half + 12 + half / 2, y, y + gap + 2, key_on)
        y += gap
        stt_on = alive and not keyboard and not testing
        stt_detail = library_for_ear()
        if ear != "teclado":
            stt_detail = clip(f"{snap.get('recognizer') or ear} · {stt_detail}")
        box(pad, y, inner, box_h, _ui("flow.stt", "Motor escucha (STT)"), stt_detail, stt_on or (testing and not keyboard))
        y += box_h
        down(width / 2, y, y + gap + 2, alive)
        y += gap
        heard = clip(snap.get("last_heard") or "—")
        box(pad, y, inner, max(40, box_h - 8), _ui("flow.text", "Texto"), heard, alive)
        y += max(40, box_h - 8)
        down(width / 2, y, y + gap + 2, alive and not testing)
        y += gap
        direct = open_chat and talking and not testing
        if direct:
            ask_detail = _ui("flow.abierta_yes", "Sí. Directo a Grok, el modelo local no decide.")
        elif open_chat and not testing:
            ask_detail = _ui("flow.abierta_no", "Aún cerrada. Al abrirse, el texto va directo a Grok.")
        else:
            ask_detail = _ui("flow.yes", "") if talking else _ui("flow.no", "")
        box(pad, y, inner, box_h, _ui("flow.ask", "¿Conversación abierta?"), ask_detail, alive and not testing)
        ask_bottom = y + box_h
        y = ask_bottom + gap
        col = (inner - 12) / 2
        local_on = alive and not testing and not talking
        grok_on = alive and talking
        has_local = local_name != _ui("status.no_identifier", "sin identificador")
        annotating = alive and not testing and talking and has_local and not direct
        if direct:
            local_box = _ui("flow.local_nodecide", "no decide")
        elif annotating:
            local_box = _ui("flow.note", "anota")
        elif talking:
            local_box = _ui("flow.skip", "no entra")
        else:
            local_box = local_detail
        box(pad, y, col, box_h, _ui("flow.local", "Modelo local"), local_box, local_on or annotating)
        box(pad + col + 12, y, col, box_h, _ui("flow.grok", "Grok"), clip(f"{snap.get('model') or 'grok'} · {_ui('flow.grok_note', 'solo texto')}"), grok_on)
        down(pad + col / 2, ask_bottom, y, local_on or annotating)
        down(pad + col + 12 + col / 2, ask_bottom, y, grok_on)
        y += box_h + gap
        chip_w = (col - 8) / 3
        chip_h = max(58, box_h)
        chips = (
            (_ui("flow.stay", "Se queda"), _ui("flow.stay_note", ""), local_on),
            (_ui("flow.command", "Orden"), _ui("flow.command_note", ""), local_on),
            (_ui("flow.open", "Abre"), _ui("flow.open_note", ""), local_on),
        )
        for index, (title, detail, on) in enumerate(chips):
            box(pad + index * (chip_w + 4), y, chip_w, chip_h, title, detail, on, size=10)
        abre_x = pad + 2 * (chip_w + 4) + chip_w
        grok_x = pad + col + 12
        grok_mid = (y - gap - box_h) + box_h * 0.55
        canvas.create_line(
            abre_x - 4, y + 16, grok_x + 10, grok_mid,
            fill=look.amber if local_on else look.button_active, width=2, arrow="last", arrowshape=(10, 12, 4),
        )
        down(pad + col + 12 + col / 2, y - gap, y, grok_on)
        box(
            grok_x, y, col, chip_h,
            _ui("flow.voice", "Voz"), clip(f"{voice_name} · {voice_lib}"), grok_on,
        )
