"""The house rules: what stays home, and what is allowed to leave."""

from pathlib import Path

import pytest

from grok_assistant.cloud.grok_cli import GrokError
from grok_assistant.rules.hub import build
from grok_assistant.paths import load_lines


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t

    def wall(self):
        return 1_700_000_000.0


class FakeCLI:
    def __init__(self):
        self.calls = []
        self.answer = "Son las tres."
        self.classified = {"accion": "ignorar", "orden": "", "texto": ""}

    def classify(self, text, model):
        self.calls.append(("classify", text))
        return self.classified

    def converse(self, text, *, model, effort, session_id, first, agent_path, system=None, files=False):
        self.calls.append(("converse", text, effort, agent_path))
        return self.answer


@pytest.fixture
def world(tmp_path):
    clock = Clock()
    cli = FakeCLI()
    hub = build(tmp_path / "data", tmp_path / "agents", cli, clock=clock, wall=clock.wall, account_dir=tmp_path / "account")
    return hub, cli, clock


def test_lists_are_long_and_distinct():
    from grok_assistant.speaking.waits import catalog

    hellos = load_lines("hellos-es.txt")
    waits = [row["text"] for row in catalog("es")]
    assert len(hellos) >= 180
    assert len(waits) == 96
    assert waits[0] == "Un momento, que lo miro."
    assert "Buscando... el plan B sigue siendo buscar." in waits
    assert len(set(hellos)) == len(hellos)
    assert len(set(waits)) == len(waits)
    assert all(line.startswith("Hola,") for line in hellos)


def test_startup_uses_the_saved_lines(world):
    from grok_assistant.speaking.banter import pool

    hub, _cli, _clock = world
    spoken = pool("es", hub.brain.settings.line_kinds, hub.brain.settings.line_themes)
    line = hub.startup()
    assert line == spoken[0]
    assert hub.brain.settings.hello_index == 1


def test_room_chatter_stays_home(world):
    hub, cli, _clock = world
    result = hub.run("qué tal el partido de ayer con los vecinos del quinto")
    assert result.spoken == []
    assert cli.calls == []
    assert hub.sent == []
    saved = hub.brain.sessions.current().lines[-1]
    assert saved["decision"] == "ignorar"
    assert saved["sent"] is False
    assert "partido" in saved["heard"]


def test_a_question_in_the_same_breath_is_sent(world):
    hub, cli, _clock = world
    result = hub.run("hola grok qué hora es")
    assert any(call[0] == "converse" and "hora" in call[1] for call in cli.calls)
    assert hub.brain.in_conversation
    assert result.spoken[0] != "Hola."


def test_misheard_wake_and_presence(world):
    hub, _cli, _clock = world
    assert hub.run("hola grop").spoken == ["Hola."]
    hub.brain.in_conversation = False
    assert hub.run("estás ahí grok").spoken == ["Sí, aquí estoy."]


def test_exact_and_one_character_commands_stay_local(world):
    hub, cli, _clock = world
    said = hub.run("comando subir volumen").spoken
    assert "75" in said[0]
    assert cli.calls == []
    said = hub.run("comando subir voluman").spoken
    assert "80" in said[0]
    assert cli.calls == []


def test_two_wrong_characters_go_to_the_classifier_only(world):
    hub, cli, _clock = world
    result = hub.run("comando subir volumanx")
    assert cli.calls == [("classify", "subir volumanx")]
    assert result.spoken == ["No conozco ese comando."]
    assert hub.brain.settings.wait_index == 0


def test_long_phrase_outside_is_dropped_unless_it_is_a_song(world):
    hub, cli, _clock = world
    hub.run("uno dos tres cuatro cinco seis siete")
    assert cli.calls == []
    title = " ".join(f"tema{i}" for i in range(13))
    played = hub.run(f"pon la canción {title}")
    assert any(effect[0] == "play" for effect in played.effects)
    assert cli.calls == []
    longer = " ".join(f"tema{i}" for i in range(14))
    dropped = hub.run(f"pon la canción {longer}")
    assert dropped.effects == []
    assert cli.calls == []


def test_question_sends_text_and_a_filler_not_the_room(world):
    hub, cli, _clock = world
    hub.run("hablan de fútbol en la cocina")
    hub.run("hola grok")
    from grok_assistant.speaking.waits import pick

    spoken, _index = pick("es", hub.brain.settings.wait_styles, 0)
    result = hub.run("qué hora es")
    assert result.spoken[0] == spoken
    assert result.spoken[1] == "Son las tres."
    assert cli.calls[0][0] == "converse"
    assert cli.calls[0][1] == "qué hora es"
    assert "fútbol" not in cli.calls[0][1]
    assert hub.brain.settings.wait_index == 1


def test_local_command_does_not_spend_a_filler(world):
    hub, _cli, _clock = world
    before = hub.brain.settings.wait_index
    hub.run("comando ayuda")
    assert hub.brain.settings.wait_index == before


def test_a_near_greeting_goes_to_the_text_identifier(world):
    hub, cli, _clock = world

    class Hear:
        def interpret(self, phrase, in_conversation):
            return {"accion": "saludo", "orden": "", "texto": ""}

    hub.mind = Hear()
    hub.brain.settings.local_llm = True
    result = hub.run("Hola Groo")
    assert result.spoken == ["Hola."]
    assert hub.brain.in_conversation
    assert cli.calls == []
    assert any(line.split("  ")[1] == "·" and "Hola Groo" in line for line in hub.brain.logs)


def test_poner_una_cancion_is_a_command_even_in_conversation(world):
    hub, cli, _clock = world

    class Steal:
        def interpret(self, phrase, in_conversation):
            return {"accion": "texto", "orden": "", "texto": ""}

    hub.mind = Steal()
    hub.brain.settings.local_llm = True
    hub.run("hola grok")
    result = hub.run("poner una cancion")
    assert result.spoken == ["¿Qué canción?"]
    assert cli.calls == []


def test_conversation_goes_to_grok_without_the_local_model(world):
    hub, cli, _clock = world

    class Steal:
        def interpret(self, phrase, in_conversation):
            return {"accion": "comando", "orden": "subir volumen", "texto": ""}

    hub.mind = Steal()
    hub.brain.settings.local_llm = True
    hub.run("hola grok")
    result = hub.run("qué hora es")
    assert cli.calls
    assert cli.calls[0][0] == "converse"
    assert "hora" in cli.calls[0][1]
    assert "Volumen" not in " ".join(result.spoken)


def test_the_second_reading_keeps_an_english_name():
    from grok_assistant.listening.refine import choose_transcript

    assert choose_transcript("pon la cancion de de bi tles", "pon la canción de The Beatles") == "pon la canción de The Beatles"
    assert choose_transcript("pon la cancion", "") == "pon la cancion"
    assert choose_transcript("Hola, Grok, ¿me escuches?", "[MUSIC]") == "Hola, Grok, ¿me escuches?"
    assert choose_transcript("qué hora es", "Kuala meringainya") == "qué hora es"
    assert choose_transcript("para la música", "aile, na me laan na tisia ar") == "para la música"
    assert choose_transcript("pon la cancion de mozart", "pon la canción de Batman") == "pon la cancion de mozart"


def test_test_mode_keeps_the_selected_ear(world):
    from grok_assistant.listening.refine import pick_transcript

    assert pick_transcript("hola desde kroko", "hola desde whisper", True) == "hola desde kroko"
    assert pick_transcript("pon la cancion de de bi tles", "pon la canción de The Beatles", False).endswith("Beatles")
    hub, _cli, _clock = world
    hub.brain.settings.recognizer = "kroko"
    hub.run("prueba")
    hub.run("qué hora es")
    text = "\n".join(hub.brain.logs)
    assert "qué hora es" in text
    assert "Kroko" in text
    assert "Whisper" not in text


def test_debug_log_keeps_the_last_500_lines(world):
    hub, _cli, _clock = world
    for number in range(600):
        hub.brain.note(f"linea {number}")
    assert len(hub.brain.logs) == 500
    assert hub.brain.logs[-1].endswith("linea 599")
    assert hub.brain.logs[0].endswith("linea 100")


def test_ok_closes_without_the_waiting_line(world):
    hub, cli, _clock = world
    hub.run("hola grok")
    before = hub.brain.settings.wait_index
    result = hub.run("ok")
    assert result.spoken == ["Vale."]
    assert hub.brain.settings.wait_index == before
    assert cli.calls == []
    assert not hub.brain.in_conversation


def test_outside_conversation_the_local_model_can_close(world):
    hub, cli, _clock = world

    class Close:
        def interpret(self, phrase, in_conversation):
            return {"accion": "cierre", "orden": "gracias", "texto": ""}

    hub.mind = Close()
    hub.brain.settings.local_llm = True
    result = hub.run("graxias")
    assert result.spoken == ["De nada."]
    assert cli.calls == []


def test_a_typed_name_is_kept_before_any_repetition(world):
    hub, _cli, _clock = world
    hub.brain.settings.wake_heard = ["hola droga", "hola grog"]
    turn = hub.brain.rename_typed("luz")
    assert hub.brain.settings.wake_name == "luz"
    assert hub.brain.settings.wake_heard == []
    assert hub.brain.naming["stage"] == "train_offer"
    assert turn.speak[0] == "A partir de ahora me llamo luz."
    left = hub.run("salir")
    assert left.spoken == ["Me sigo llamando luz."]
    assert hub.brain.naming is None
    assert hub.brain.settings.wake_name == "luz"
    hub.run("hola luz")
    assert hub.brain.in_conversation
    hub.brain.in_conversation = False
    empty = hub.brain.rename_typed("   ")
    assert empty.speak == ["Dime un nombre."]
    assert hub.brain.settings.wake_name == "luz"


def test_six_repetitions_can_follow_a_typed_name(world):
    hub, _cli, _clock = world
    hub.brain.rename_typed("luz")
    hub.run("sí")
    for heard in ("luz", "lus", "luz", "luz", "luz", "luz"):
        hub.run(heard)
    assert hub.brain.naming is None
    assert hub.brain.settings.wake_name == "luz"
    assert "lus" in hub.brain.settings.wake_heard
    hub.run("lus")
    assert hub.brain.in_conversation


def test_a_trained_name_wakes_from_what_was_heard(world):
    hub, _cli, _clock = world
    hub.run("comando cambiar nombre")
    hub.run("casa")
    hub.run("sí")
    for heard in ("casa", "caza", "casaa", "kasa", "casa", "cassa"):
        hub.run(heard)
    assert hub.brain.naming is None
    assert hub.brain.settings.wake_name == "casa"
    assert "caza" in hub.brain.settings.wake_heard
    hub.run("caza")
    assert hub.brain.in_conversation


def test_thanks_closes_without_cloud(world):
    hub, cli, _clock = world
    hub.run("hola grok")
    result = hub.run("muchas gracias")
    assert result.spoken == ["De nada."]
    assert not hub.brain.in_conversation
    assert cli.calls == []


def test_pending_vale_confirms_and_any_other_phrase_cancels(world):
    hub, cli, _clock = world
    cli.classified = {"accion": "comando", "orden": "subir volumen", "texto": ""}
    asked = hub.run("comando sube un poco el volumen")
    assert asked.spoken[0].startswith("Has dicho: subir volumen")
    cancelled = hub.run("mejor no")
    assert cancelled.spoken == ["Vale."]
    assert "Volumen" not in " ".join(cancelled.spoken)
    asked = hub.run("comando sube un poco el volumen")
    confirmed = hub.run("vale")
    assert "Volumen" in confirmed.spoken[0]


def test_conversation_close_is_not_session_close(world):
    hub, _cli, _clock = world
    hub.run("hola grok")
    hub.run("comando crear sesion cocina")
    hub.run("sí")
    hub.run("comando abrir sesion cocina")
    assert hub.brain.sessions.active == "cocina"
    closed = hub.run("cierra conversación")
    assert closed.spoken == ["Adiós."]
    assert hub.brain.sessions.active == "cocina"
    assert not hub.brain.in_conversation
    hub.run("hola grok")
    back = hub.run("comando cerrar sesion")
    assert "compartida" in back.spoken[0]
    assert hub.brain.sessions.active == "compartida"
    assert not hub.brain.in_conversation


def test_agent_create_needs_the_password_and_listing_does_not(world, tmp_path):
    hub, cli, clock = world
    blocked = hub.run("comando crear agente compras")
    assert "contraseña" in blocked.spoken[0].lower()
    assert list(Path(tmp_path / "agents").glob("*.md")) == []
    hub.brain.auth.set_password("secreto")
    asked = hub.run("comando crear agente compras")
    assert any(effect[0] == "ask_password" for effect in asked.effects)
    made = hub.submit_password("secreto")
    assert any("creado" in line for line in made.spoken)
    assert hub.brain.agents.resolve("compras") is not None
    hub.run("no")
    clock.t += 301
    hub.run("comando lista las personas")
    denied = hub.submit_password("nope")
    assert "incorrecta" in denied.spoken[0].lower()
    listed = hub.run("comando listar agentes")
    assert "compras" in listed.spoken[0]
    assert cli.calls == []


def test_the_agent_menu_lists_account_agents_and_a_local_file_wins(tmp_path, monkeypatch):
    from grok_assistant.cloud.account_agents import agents_from_bundle, agents_from_customizations
    from grok_assistant.notebook.store import AgentBook

    account = tmp_path / "bundled"
    account.mkdir()
    (account / "explore.md").write_text("---\nname: explore\n---\n\nLee.\n", encoding="utf-8")
    (account / "plan.md").write_text("---\nname: plan\n---\n\nPlan.\n", encoding="utf-8")
    local = tmp_path / "local"
    local.mkdir()
    (local / "compras.md").write_text("---\nname: compras\n---\n\nListas.\n", encoding="utf-8")
    (local / "explore.md").write_text("---\nname: explore\n---\n\nMio.\n", encoding="utf-8")
    book = AgentBook(local, tmp_path / "state.json", account, tmp_path / "cache")
    rows = {record.name: record.origin for record in book.list()}
    assert rows == {"compras": "local", "explore": "local", "plan": "account"}
    opened = book.open("plan")
    assert opened is not None
    assert opened.origin == "account"
    assert opened.path.name == "plan.md"

    bundle = agents_from_bundle({"agents": {"vega": "---\nname: vega\n---\n\nHola.", "vacio": "  "}})
    assert bundle["vega"].startswith("---\nname: vega")
    assert "vacio" not in bundle
    custom = agents_from_customizations({
        "agentCustomizations": [{"name": "Casa", "instructions": "Fechas y listas."}, {"id": ""}],
    })
    assert "Casa" in custom
    assert "Fechas y listas." in custom["Casa"]

    monkeypatch.setattr(
        "grok_assistant.cloud.account_agents.fetch_account_agents",
        lambda auth_path=None: {"vega": "---\nname: vega\n---\n\nHola.\n"},
    )
    book.refresh_account()
    saved = book.resolve("vega")
    assert saved is not None and saved.origin == "account"
    assert (tmp_path / "cache" / "vega.md").read_text(encoding="utf-8").startswith("---")
    still = book.resolve("explore")
    assert still is not None and still.origin == "local"


def test_password_file_has_no_password(world, tmp_path):
    hub, _cli, _clock = world
    hub.brain.auth.set_password("clave-larga")
    raw = (tmp_path / "data" / "admin.json").read_text(encoding="utf-8")
    assert "clave-larga" not in raw
    assert hub.brain.auth.verify("clave-larga")
    assert not hub.brain.auth.verify("otra")


def test_shared_session_expires_and_takes_the_local_notes_with_it(world):
    hub, _cli, clock = world
    hub.run("ruido de la sala")
    hub.brain.sessions.sessions["compartida"].created = clock.wall() - 90_000
    hub.brain.sessions.sessions["compartida"].lines.append(
        {"heard": "viejo secreto", "decision": "ignorar", "sent": False}
    )
    hub.run("otro ruido")
    heard = [item.get("heard") for item in hub.brain.sessions.current().lines]
    assert "viejo secreto" not in heard


def test_command_line_from_the_model_is_run_and_not_read(world):
    hub, cli, _clock = world
    hub.run("hola grok")
    cli.answer = "COMANDO: subir volumen"
    result = hub.run("haz lo del volumen")
    assert all("COMANDO" not in line for line in result.spoken)
    assert any("Volumen" in line for line in result.spoken)


def test_long_answer_offers_detail_once_and_high_effort(world):
    hub, cli, _clock = world
    hub.run("hola grok")
    cli.answer = " ".join(["palabra"] * 30)
    first = hub.run("cuéntame eso con calma")
    assert any("más detalle" in line for line in first.spoken)
    again = hub.run("sí")
    assert any(call[0] == "converse" and call[2] == "high" for call in cli.calls)
    assert not any("más detalle" in line for line in again.spoken)


def test_cloud_error_does_not_offer_detail(world):
    hub, cli, _clock = world

    def explode(*_args, **_kwargs):
        raise GrokError("boom")

    cli.converse = explode
    hub.run("hola grok")
    result = hub.run("qué hora es")
    assert result.spoken[-1] == "Ahora mismo no llego a la nube."
    assert all("detalle" not in line for line in result.spoken)


def test_test_mode_hears_and_does_nothing(world):
    hub, cli, _clock = world
    entered = hub.run("prueba")
    assert "salir" in entered.spoken[0].lower()
    assert "prueba" in entered.spoken[0].lower()
    ignored = hub.run("comando subir volumen")
    assert ignored.spoken == []
    assert cli.calls == []
    left = hub.run("salir")
    assert left.spoken == ["Salgo de la prueba. Vuelvo a escuchar."]
    hub.run("comando prueba")
    menu_left = hub.run("comando salir")
    assert menu_left.spoken == ["Salgo de la prueba. Vuelvo a escuchar."]
    assert hub.brain.test_mode is False


def test_the_menu_test_switch_logs_the_change_and_renames_itself(world):
    hub, _cli, _clock = world
    from grok_assistant.i18n import activate
    from grok_assistant.ui.chrome import test_switch_label

    activate("es")
    assert test_switch_label(False) == "Activar prueba"
    assert test_switch_label(True) == "Desactivar prueba"
    entered = hub.brain._enter_test("Activar prueba")
    assert hub.brain.test_mode is True
    shown = "\n".join(hub.brain.logs)
    assert "Activar prueba" in shown
    assert "modo prueba: activado" in shown
    assert entered.speak[0] in shown
    left = hub.brain._leave_test("Desactivar prueba")
    assert hub.brain.test_mode is False
    assert left.speak == ["Salgo de la prueba. Vuelvo a escuchar."]
    shown = "\n".join(hub.brain.logs)
    assert "Desactivar prueba" in shown
    assert "modo prueba: desactivado" in shown
    assert left.speak[0] in shown
    assert test_switch_label(False) == "Activar prueba"


def test_locked_voice_is_the_only_one_heard(world):
    hub, _cli, _clock = world
    hub.brain.embedder_ready = True
    hub.brain.speakers.add("Ana", [[1.0, 0.0]], lock=True)
    assert hub.run("hola grok", speaker_id="Luis").spoken == []
    assert hub.run("hola grok", speaker_id="Ana").spoken


def test_audio_without_a_saved_print_is_not_processed(world):
    hub, cli, _clock = world
    hub.brain.embedder_ready = True
    hub.brain.settings.local_llm = True
    before = list(hub.brain.logs)
    stranger = hub.run("que hora es en la cocina", vector=[0.0, 1.0])
    assert stranger.spoken == []
    assert hub.brain.logs == before
    assert cli.calls == []
    hub.brain.speakers.add("Ana", [[1.0, 0.0]], lock=False)
    before = list(hub.brain.logs)
    missed = hub.run("pon la radio de la cocina", vector=[0.0, 1.0])
    assert missed.spoken == []
    assert hub.brain.logs == before
    typed = hub.run("hola grok")
    assert typed.spoken


def test_new_print_name_never_leaves(world):
    hub, cli, _clock = world
    asked = hub.run("hola grok", unknown_print=True, vector=[0.2, 0.9])
    assert "cómo te llamas" in asked.spoken[0]
    named = hub.run("Ana", vector=[0.2, 0.9])
    assert "Ana" in named.spoken[0]
    assert hub.brain.speakers.locked is None
    assert cli.calls == []


def test_file_edits_stay_off_until_an_admin_allows_them(world, tmp_path):
    import json

    hub, _cli, _clock = world
    assert hub.brain.settings.grok_files is False
    blocked = hub.brain.set_grok_files(True)
    assert hub.brain.settings.grok_files is False
    assert "contraseña" in blocked.speak[0].lower()
    hub.brain.auth.set_password("secreto")
    asked = hub.brain.set_grok_files(True)
    assert any(effect[0] == "ask_password" for effect in asked.effects)
    assert hub.brain.settings.grok_files is False
    done = hub.submit_password("secreto")
    assert hub.brain.settings.grok_files is True
    assert any("archivos" in line for line in done.spoken)
    saved = json.loads((tmp_path / "data" / "config.json").read_text(encoding="utf-8"))
    assert saved["grok_files"] is True
    room = (tmp_path / "data" / "AGENTS.md").read_text(encoding="utf-8")
    assert "cambiar archivos" in room
    assert "shell" in room
    closed = hub.run("comando grok solo web")
    assert hub.brain.settings.grok_files is False
    assert any("web" in line for line in closed.spoken)
    room = (tmp_path / "data" / "AGENTS.md").read_text(encoding="utf-8")
    assert "No edites archivos" in room


def test_admin_lasts_five_minutes(world):
    hub, _cli, clock = world
    hub.brain.auth.set_password("secreto")
    hub.run("comando modo administrador")
    hub.submit_password("secreto")
    assert hub.brain.is_admin()
    clock.t += 301
    result = hub.tick()
    assert not hub.brain.is_admin()
    assert any("administrador" in line for line in result.spoken)


def test_open_chat_uses_the_silence_minutes(world):
    hub, _cli, clock = world
    hub.brain.settings.talk_mode = "abierta"
    hub.brain.settings.quiet_minutes = 3
    hub.run("hola grok")
    clock.t += 120
    hub.tick()
    assert hub.brain.in_conversation
    clock.t += 61
    hub.tick()
    assert not hub.brain.in_conversation


def test_question_command_opens_without_the_name(world):
    hub, cli, clock = world
    hub.brain.settings.quiet_minutes = 0.5
    opened = hub.run("comando pregunta")
    assert opened.spoken == ["Dime."]
    assert hub.brain.in_conversation
    assert cli.calls == []
    assert hub.run("comando abrir charla").spoken == ["Dime."]
    assert hub.run("comando abrir conversacion").spoken == ["Dime."]
    assert hub.run("comando abre conversacion").spoken == ["Dime."]
    clock.t += 29
    hub.tick()
    assert hub.brain.in_conversation
    clock.t += 2
    hub.tick()
    assert not hub.brain.in_conversation
    again = hub.run("comando pregunta")
    assert again.spoken == ["Dime."]
    closed = hub.run("vale, gracias")
    assert not hub.brain.in_conversation
    assert closed.spoken == ["De nada."]
    hub.run("comando abrir charla")
    assert hub.run("ok gracias").spoken == ["De nada."]
    assert not hub.brain.in_conversation


def test_shared_notebook_rolls_by_the_chosen_days(world):
    hub, _cli, clock = world
    hub.brain.settings.shared_days = 20
    shared = hub.brain.sessions.sessions["compartida"]
    shared.grok_id = "vieja"
    now = clock.wall()
    day = 24 * 60 * 60
    shared.lines = [
        {"ts": now - 21 * day, "heard": "dia 1", "decision": "ignorar", "sent": False},
        {"ts": now - 2 * day, "heard": "dia reciente", "decision": "ignorar", "sent": False},
    ]
    hub.run("otro ruido")
    heard = [item.get("heard") for item in hub.brain.sessions.current().lines]
    assert "dia 1" not in heard
    assert "dia reciente" in heard
    assert hub.brain.sessions.current().grok_id == "vieja"

    shared = hub.brain.sessions.sessions["compartida"]
    shared.lines = [
        {"ts": now - 21 * day, "heard": "solo viejo", "decision": "ignorar", "sent": False}
    ]
    shared.grok_id = "vieja"
    hub.run("otro ruido")
    heard = [item.get("heard") for item in hub.brain.sessions.current().lines]
    assert "solo viejo" not in heard
    assert hub.brain.sessions.current().grok_id is None

    made = hub.brain.sessions.create("cocina")
    assert made == "cocina"
    hub.brain.sessions.open("cocina")
    hub.brain.sessions.current().lines.append(
        {"ts": now - 40 * day, "heard": "receta vieja", "decision": "ignorar", "sent": False}
    )
    hub.run("otro ruido")
    named = [item.get("heard") for item in hub.brain.sessions.current().lines]
    assert "receta vieja" in named


def test_conversation_timeout_ignores_time_spent_busy(world):
    hub, _cli, clock = world
    hub.run("hola grok")
    clock.t += 30
    assert hub.brain.in_conversation
    clock.t += 61
    hub.tick()
    assert not hub.brain.in_conversation


def test_apagar_is_not_a_command(world):
    hub, _cli, _clock = world
    result = hub.run("comando apagar")
    assert result.spoken == ["No conozco ese comando."]
    assert not any(effect[0] == "shutdown" for effect in result.effects)


def test_stop_music_is_not_pause_music(world):
    hub, _cli, _clock = world
    assert hub.run("comando para la musica").spoken == ["Paro la música."]
    assert hub.run("comando pausa la musica").spoken == ["Pauso."]


def test_the_corner_says_waiting_until_a_conversation_starts(world):
    hub, _cli, _clock = world
    assert hub.brain.banner_label() == "ESPERA"
    hub.run("hola grok")
    assert hub.brain.banner_label() == "EN CONVERSACIÓN"
    hub.brain.paused = True
    assert hub.brain.banner_label() == "EN PAUSA"


def test_the_log_hangs_each_step_under_the_heard_line(world):
    hub, _cli, _clock = world

    class Mind:
        def available(self):
            return True

        def interpret(self, phrase, in_conversation):
            return {"accion": "texto", "orden": "", "texto": phrase}

    hub.mind = Mind()
    hub.brain.settings.local_llm = True
    hub.run("qué hora es en madrid")
    assert any(line.split("  ")[1] == "·" and line.endswith("qué hora es en madrid") for line in hub.brain.logs)
    assert any(line.split("  ")[1] == "¦" and line.endswith("LLM: texto") for line in hub.brain.logs)


def test_a_local_order_that_is_not_on_the_list_stays_visible(world):
    hub, _cli, _clock = world

    class Mind:
        def available(self):
            return True

        def interpret(self, phrase, in_conversation):
            return {"accion": "comando", "orden": "apaga la tele", "texto": ""}

    hub.mind = Mind()
    hub.brain.settings.local_llm = True
    hub.run("apaga la tele")
    assert any(line.endswith("LLM: comando · apaga la tele") for line in hub.brain.logs)
    hub.run("hola grok")
    hub.run("qué tiempo hará mañana")
    assert any(line.split("  ")[1] == "¦" and line.endswith("Grok: Son las tres.") for line in hub.brain.logs)


def test_a_take_without_audio_does_not_erase_the_print(world):
    hub, _cli, _clock = world
    hub.brain.speakers.add("Ana", [[1.0, 0.0]], lock=True)
    hub.brain.enroll = {
        "stage": "takes", "target": "Ana", "spoken": "Ana",
        "take": 0, "vectors": [], "clips": [], "misses": 0,
    }
    missed = hub.brain.accept_take(None, None)
    assert "huella" in missed.speak[0].lower()
    assert hub.brain.enroll["take"] == 0
    assert hub.brain.speakers.take_count("Ana") == 1
    samples = [0.01] * 1600
    vector = [0.2, 0.98]
    last = None
    for _number in range(16):
        last = hub.brain.accept_take(samples, vector)
    assert hub.brain.enroll is None
    assert hub.brain.speakers.take_count("Ana") == 16
    assert len(hub.brain.speakers.raw_clips("Ana")) == 16
    assert hub.brain.speakers.closest(vector, "teclado") == "Ana"
    assert hub.brain.speakers.closest(vector, "whisper") == "Ana"
    assert hub.brain.speakers.closest(vector, "kroko") == "Ana"
    assert hub.brain.speakers.locked == "Ana"
    assert "todos los motores" in last.speak[0]


def test_a_split_recording_does_not_create_a_second_person(world):
    hub, _cli, _clock = world
    hub.brain.speakers.add("Ana", [[1.0, 0.0]], lock=True)
    hub.brain.start_capture("Ana")
    samples = [0.01] * 1600
    turn = None
    for number in range(16):
        vector = [1.0, 0.0] if number < 8 else [0.0, 1.0]
        turn = hub.brain.accept_take(samples, vector)
    assert hub.brain.enroll is None
    assert "no cambio la huella" in turn.speak[0]
    assert len(hub.brain.speakers.raw_clips("Ana")) == 16
    assert any(effect[0] == "score_prints" for effect in turn.effects)
    assert hub.brain.speakers.closest([1.0, 0.0], "canary") == "Ana"
    assert hub.brain.speakers.closest([0.0, 1.0], "canary") is None
    assert hub.brain.speakers.locked == "Ana"
    assert any("wav guardados" in line for line in hub.brain.logs)


def test_outlier_takes_stay_in_the_raw_sound(world):
    hub, _cli, _clock = world
    hub.brain.start_capture("Ana")
    samples = [0.01] * 1600
    turn = None
    for number in range(16):
        vector = [1.0, 0.0] if number < 12 else [0.0, 1.0]
        turn = hub.brain.accept_take(samples, vector)
    assert len(hub.brain.speakers.raw_clips("Ana")) == 16
    assert hub.brain.speakers.closest([1.0, 0.0]) == "Ana"
    assert hub.brain.speakers.closest([0.0, 1.0]) is None
    assert "12 de 16" in turn.speak[0]


def test_a_first_recording_keeps_the_wavs_when_the_voices_split(world):
    hub, _cli, _clock = world
    hub.brain.start_capture("Ana")
    samples = [0.01] * 1600
    turn = None
    for number in range(16):
        vector = [1.0, 0.0] if number < 8 else [0.0, 1.0]
        turn = hub.brain.accept_take(samples, vector)
    assert len(hub.brain.speakers.raw_clips("Ana")) == 16
    assert hub.brain.speakers.closest([1.0, 0.0]) is None
    assert hub.brain.speakers.locked is None
    assert any(effect[0] == "score_prints" for effect in turn.effects)
    assert any("wav guardados" in line for line in hub.brain.logs)


def test_a_take_writes_what_the_ear_heard(world):
    hub, _cli, _clock = world
    hub.brain.settings.recognizer = "kroko"
    hub.brain.start_capture("Ana")
    samples = [0.01] * 1600
    hub.brain.accept_take(samples, [0.2, 0.98], "hola grok")
    text = "\n".join(hub.brain.logs)
    assert "hola grok" in text
    assert "Kroko" in text
    missed = hub.brain.accept_take(None, None, "estás ahí")
    assert "estás ahí" in missed.speak[0]
    assert "micrófono" not in missed.speak[0]
    assert any("estás ahí" in line for line in hub.brain.logs)
    hub.brain.accept_take(None, None)
    assert any("silencio" in line and "Kroko" in line for line in hub.brain.logs)
    kept = hub.brain.accept_take(samples, [0.2, 0.98], "")
    assert hub.brain.enroll["take"] == 2
    assert "micrófono" not in kept.speak[0]
    assert any("sonido guardado" in line for line in hub.brain.logs)
    wrong = hub.brain.accept_take(samples, [0.2, 0.98], "otra frase")
    assert hub.brain.enroll["take"] == 3
    assert "repite" not in wrong.speak[0].lower()


def test_words_show_while_they_are_still_being_said(world):
    hub, _cli, _clock = world
    hub.brain.hearing = True
    assert hub.brain.banner_label() == "OYENDO"
    hub.brain.preview("qué")
    hub.brain.preview("qué hora")
    assert len(hub.brain.logs) == 1
    assert hub.brain.logs[-1].endswith("qué hora")
    assert hub.brain.banner_label() == "qué hora"
    hub.brain.preview("qué hora")
    assert len(hub.brain.logs) == 1
    hub.brain._flow("qué hora es")
    assert len(hub.brain.logs) == 1
    assert hub.brain.logs[-1].endswith("qué hora es")
    assert hub.brain._live_open is False
    hub.brain.preview("qué hora es")
    assert len(hub.brain.logs) == 1
    hub.brain.hearing = False
    assert hub.brain.banner_label() == "ESPERA"


def test_the_print_prompt_uses_the_renamed_assistant(world):
    hub, _cli, _clock = world
    hub.brain.settings.wake_name = "Miguel"
    started = hub.brain.start_capture("Ana")
    assert "hola Miguel" in started.speak[0]
    assert "hola grok" not in started.speak[0]
    samples = [0.01] * 1600
    hub.brain.accept_take(samples, [0.2, 0.98], "hola miguel")
    assert hub.brain.enroll["clips"][0]["phrase"] == "hola Miguel"
    assert "estás ahí" in hub.brain._prompt_take().speak[0]


def test_leaving_the_print_discards_the_audio(world):
    hub, _cli, _clock = world
    hub.brain.start_capture("Ana")
    samples = [0.01] * 1600
    hub.brain.accept_take(samples, [0.2, 0.98], "hola")
    assert hub.brain.enroll["take"] == 1
    turn = hub.brain.discard_capture()
    assert hub.brain.enroll is None
    assert hub.brain.speakers.raw_clips("Ana") == []
    assert "no guardo" in turn.speak[0].lower()
    assert any("no guardo los audios" in line for line in hub.brain.logs)


def test_three_empty_takes_stop_the_recording(world):
    hub, _cli, _clock = world
    started = hub.brain.start_capture("Ana")
    assert "16" in started.speak[0]
    assert "pitido" in started.speak[0]
    assert "Reintentar" in started.speak[0]
    assert any(item[0] == "record_take" for item in started.effects)
    first = hub.brain.accept_take(None, None)
    assert hub.brain.enroll["take"] == 0
    assert any(effect[0] == "record_take" for effect in first.effects)
    hub.brain.accept_take(None, None)
    last = hub.brain.accept_take(None, None)
    assert hub.brain.enroll is None
    assert "micrófono" in last.speak[0]


def test_prints_are_stored_next_to_the_executable(tmp_path, monkeypatch):
    import grok_assistant.paths as paths

    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "executable", str(tmp_path / "GrokAssistant.exe"))
    assert paths.speakers_file() == tmp_path / "data" / "speakers.json"


def test_a_print_can_be_renamed_and_recaptured(world):
    hub, _cli, _clock = world
    hub.brain.speakers.add("Ana", [[1.0, 0.0]], lock=True)
    hub.brain.speakers.add("Luis", [[0.0, 1.0]], lock=False)
    assert hub.brain.speakers.rename("Ana", "Luis") is None
    assert hub.brain.speakers.rename("Ana", "Ana María") == "Ana María"
    assert hub.brain.speakers.locked == "Ana María"
    turn = hub.brain.start_capture("Ana María")
    assert hub.brain.enroll["stage"] == "takes"
    assert hub.brain.enroll["target"] == "Ana María"
    assert turn.speak


def test_windows_recognizer_is_not_rewritten_to_kroko(world):
    hub, cli, _clock = world
    hub.brain.recognizers = ["teclado", "windows", "kroko"]
    hub.brain.settings.recognizer = "kroko"
    said = hub.run("comando reconocedor windows").spoken[0]
    assert "windows" in said.lower()
    assert hub.brain.settings.recognizer == "windows"
    assert cli.calls == []


def test_unmatched_text_stays_home_until_a_conversation_starts(world):
    hub, cli, _clock = world

    class Pass:
        def interpret(self, phrase, in_conversation):
            return {"accion": "texto", "orden": "", "texto": ""}

    hub.mind = Pass()
    hub.brain.settings.local_llm = True
    result = hub.run("qué tiempo hará mañana en casa")
    assert cli.calls == []
    assert not hub.brain.in_conversation
    assert result.spoken == []


def test_a_voice_from_another_language_is_dropped(world):
    hub, _cli, _clock = world
    hub.brain.voices = ["Helena", "Zira"]
    hub.brain.settings.voice_index = 0
    hub.brain.set_devices(["Helena", "Dave · España"], ["teclado"])
    assert hub.brain.voices[hub.brain.settings.voice_index] == "Helena"
    hub.brain.voices = ["Helena", "Zira"]
    hub.brain.settings.voice_index = 1
    hub.brain.set_devices(["Helena", "Dave · España"], ["teclado"])
    assert "Zira" not in hub.brain.voices
    assert hub.brain.settings.voice_index == 0


def test_ola_grok_still_wakes_when_the_identifier_says_no(world):
    hub, cli, _clock = world

    class Nope:
        def available(self):
            return True

        def interpret(self, phrase, in_conversation):
            return {"accion": "texto", "orden": "", "texto": ""}

    hub.mind = Nope()
    hub.brain.settings.local_llm = True
    heard = hub.run("Ola Grok")
    assert heard.spoken == ["Hola."]
    assert hub.brain.in_conversation
    assert cli.calls == []
    asked = hub.run("Ola Grok qué hora es")
    assert any(call[0] == "converse" and "hora" in call[1] for call in cli.calls)
    assert asked.spoken[0] != "Hola."


def test_a_short_reread_does_not_erase_the_sentence():
    from grok_assistant.rules.match import endpoint_quiet
    from grok_assistant.listening.refine import choose_transcript

    assert endpoint_quiet("Ola Grok", "grok", "saludo") == 2.0
    assert endpoint_quiet("Ola Grok qué hora es", "grok", "saludo") == 0.7
    assert endpoint_quiet("Ola Grok", "grok", "seguida") == 0.7
    assert endpoint_quiet("Ola Grok", "grok", "abierta") == 0.7
    assert choose_transcript("qué tiempo hace mañana", "1.0") == "qué tiempo hace mañana"


def test_french_pack_greets_and_plays_a_song(world):
    from grok_assistant.i18n import activate

    hub, _cli, _clock = world
    activate("fr")
    try:
        assert hub.run("bonjour grok").spoken == ["Bonjour."]
        song = hub.run("mets la chanson luna")
        assert any(item[0] == "play" and item[1] == "luna" for item in song.effects)
        assert song.spoken == ["Je mets luna."]
    finally:
        activate("es")


def test_hola_grok_me_escuchas_is_answered_here(world):
    hub, cli, _clock = world
    result = hub.run("hola grok, Me escuchas?")
    assert result.spoken == ["Sí, te escucho."]
    assert hub.brain.in_conversation
    assert cli.calls == []
    heard = hub.run("Hola, Grok, ¿me escuches?")
    assert heard.spoken == ["Sí, te escucho."]
    assert cli.calls == []
    noise = hub.run("[MUSIC]")
    assert noise.spoken == []
    assert cli.calls == []


def test_blank_or_a_short_word_never_reaches_grok(world):
    hub, cli, _clock = world

    class Pass:
        def interpret(self, phrase, in_conversation):
            return {"accion": "texto", "orden": "", "texto": ""}

    hub.mind = Pass()
    hub.brain.settings.local_llm = True
    assert hub.run("   ").spoken == []
    assert hub.run("eh").spoken == []
    assert cli.calls == []
    assert not hub.brain.in_conversation


def test_conversation_goes_straight_to_grok(world):
    hub, cli, _clock = world

    class Swallow:
        def interpret(self, phrase, in_conversation):
            return {"accion": "ignorar", "orden": "", "texto": ""}

    hub.mind = Swallow()
    hub.run("hola grok")
    hub.run("qué tiempo hará mañana en casa")
    assert cli.calls
    assert cli.calls[0][0] == "converse"
    assert "tiempo" in cli.calls[0][1]
    assert any(line.endswith("LLM: ignorar") for line in hub.brain.logs)


def test_hola_miren_is_a_greeting_to_miguel(world):
    from grok_assistant.rules.match import near_greeting

    assert near_greeting("Hola miren.", "Miguel") == "hola Miguel"
    assert near_greeting("miren", "Miguel") is None
    assert near_greeting("hola maria", "Miguel") is None
    assert near_greeting("qué tiempo va a hacer mañana", "Miguel") is None

    hub, cli, _clock = world
    called = []

    class Echo:
        def available(self):
            return True

        def interpret(self, phrase, in_conversation):
            called.append(phrase)
            return {
                "accion": "ilegible",
                "orden": "",
                "texto": "El reconocedor responde con el mensaje: " + phrase,
            }

    hub.mind = Echo()
    hub.brain.settings.local_llm = True
    hub.brain.settings.wake_name = "Miguel"
    result = hub.run("Hola miren.")
    assert result.spoken == ["Hola."]
    assert hub.brain.in_conversation
    assert cli.calls == []
    assert called == []
    text = "\n".join(hub.brain.logs)
    assert "Hola miren." in text
    assert "LLM: saludo · hola Miguel" in text
    assert "reconocedor" not in text


def test_an_illegible_reading_does_not_repeat_the_phrase(world):
    hub, cli, _clock = world

    class Echo:
        def available(self):
            return True

        def interpret(self, phrase, in_conversation):
            return {
                "accion": "ilegible",
                "orden": "",
                "texto": "El reconocedor responde con el mensaje: " + phrase,
            }

    hub.mind = Echo()
    hub.brain.settings.local_llm = True
    hub.run("qué hora es en madrid")
    assert cli.calls == []
    assert not hub.brain.in_conversation
    text = "\n".join(hub.brain.logs)
    assert "LLM: comando o accion no detectada" in text
    assert "LLM: ilegible" not in text
    assert "reconocedor" not in text
    assert hub.skip_ear_note


def test_a_dropped_phrase_omits_the_recognizer_and_an_open_chat_keeps_it(world):
    hub, cli, _clock = world

    class Echo:
        def available(self):
            return True

        def interpret(self, phrase, in_conversation):
            return {"accion": "ilegible", "orden": "", "texto": phrase}

    hub.mind = Echo()
    hub.brain.settings.local_llm = True

    from grok_assistant.ui.worker import WorkerMixin

    class Ear(WorkerMixin):
        def __init__(self):
            self.hub = hub

        def say(self, text):
            return None

        def _apply(self, result):
            return None

        def _refresh(self):
            return None

        def _ask(self, title):
            return ""

    ear = Ear()
    ear._job("phrase", "no sé si esto me está escuchando", None, None, "Whisper small · relectura")
    text = "\n".join(hub.brain.logs)
    assert "LLM: comando o accion no detectada" in text
    assert "Whisper" not in text
    assert cli.calls == []

    ear._job("phrase", "hola grok", None, None, "Whisper small")
    ear._job("phrase", "qué tiempo hará mañana", None, None, "Whisper base")
    text = "\n".join(hub.brain.logs)
    assert "Whisper small · relectura" not in text
    assert any(line.endswith("Whisper small") for line in hub.brain.logs)
    assert any(line.endswith("Whisper base") for line in hub.brain.logs)
    assert cli.calls[-1][1] == "qué tiempo hará mañana"
    assert not hub.skip_ear_note


def test_an_open_conversation_logs_the_reading_and_keeps_the_question(world):
    hub, cli, _clock = world

    class Read:
        def available(self):
            return True

        def interpret(self, phrase, in_conversation):
            assert in_conversation
            return {"accion": "comando", "orden": "subir volumen", "texto": "reescrito"}

    hub.mind = Read()
    hub.brain.settings.local_llm = True
    hub.run("hola grok")
    result = hub.run("¿Qué tiempo va a hacer mañana?")
    assert cli.calls[0][1] == "¿Qué tiempo va a hacer mañana?"
    assert "Volumen" not in " ".join(result.spoken)
    assert any(line.endswith("LLM: comando · subir volumen · reescrito") for line in hub.brain.logs)
    assert any(line.endswith("Grok: Son las tres.") for line in hub.brain.logs)


def test_one_loose_recognizer_character(world):
    hub, _cli, _clock = world
    said = hub.run("comando otro reconocedot").spoken[0]
    assert "teclado" in said.lower()


def test_simple_tab_chooses_how_to_talk_and_how_many_days(tmp_path):
    import tkinter as tk

    from grok_assistant.rules.hub import build
    from grok_assistant.i18n import activate
    from grok_assistant.ui.app import TrayApp

    root = tk.Tk()
    root.geometry("1000x800+40+40")
    root.attributes("-alpha", 0)
    root.withdraw()
    try:
        hub = build(tmp_path, tmp_path / "agents")
        hub.brain.settings.wake_name = "Miguel"
        activate("es")
        app = TrayApp(root, hub)
        root.deiconify()
        root.update()
        days_y = app.shared_days_box.master.winfo_y()
        quiet_y = app.quiet_minutes_box.master.winfo_y()
        assert days_y > 0 and days_y == quiet_y
        assert app.shared_label.winfo_y() + app.shared_label.winfo_height() == (
            app.quiet_label.winfo_y() + app.quiet_label.winfo_height()
        )
        assert app.talk_mode_box.get() == "Pregunta seguida"
        hint = app.talk_hint.cget("text")
        assert "Miguel" in hint and "qué hora es" in hint and "más rápida" in hint
        app.talk_mode_box.set("Primero el saludo")
        app._pick_talk_mode()
        assert hub.brain.settings.talk_mode == "saludo"
        assert app._phrase_silence() == 2.0
        hub.brain.in_conversation = True
        assert app._phrase_silence() == 0.7
        hub.brain.in_conversation = False
        app.talk_mode_box.set("Charla abierta")
        app._pick_talk_mode()
        assert hub.brain.settings.talk_mode == "abierta"
        assert "EN CONVERSACIÓN" in app.talk_hint.cget("text")
        app.shared_days_var.set("20")
        app._pick_shared_days()
        assert hub.brain.settings.shared_days == 20
        app.shared_days_var.set("0")
        app._pick_shared_days()
        assert hub.brain.settings.shared_days == 1
        app.shared_days_var.set("400")
        app._pick_shared_days()
        assert hub.brain.settings.shared_days == 365
        assert "minutos" in app.quiet_label.cget("text").lower()
        app.quiet_minutes_var.set("0,5")
        app._pick_quiet_minutes()
        assert hub.brain.settings.quiet_minutes == 0.5
        assert app.quiet_minutes_var.get() == "0.5"
        app.quiet_minutes_var.set("0")
        app._pick_quiet_minutes()
        assert hub.brain.settings.quiet_minutes == 0.1
        app.quiet_minutes_var.set("90")
        app._pick_quiet_minutes()
        assert hub.brain.settings.quiet_minutes == 60.0
        activate("en")
        app._apply_chrome()
        root.update()
        assert app.shared_days_box.master.winfo_y() == app.quiet_minutes_box.master.winfo_y()
        assert app.talk_mode_box.get() == "Open chat"
        assert "Hello Miguel" in app.talk_hint.cget("text")
        assert "days" in app.days_hint.cget("text")
    finally:
        activate("es")
        root.destroy()
