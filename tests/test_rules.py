"""The house rules: what stays home, and what is allowed to leave."""

from pathlib import Path

import pytest

from grok_assistant.grok_cli import GrokError
from grok_assistant.hub import build
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

    def converse(self, text, *, model, effort, session_id, first, agent_path):
        self.calls.append(("converse", text, effort, agent_path))
        return self.answer


@pytest.fixture
def world(tmp_path):
    clock = Clock()
    cli = FakeCLI()
    hub = build(tmp_path / "data", tmp_path / "agents", cli, clock=clock, wall=clock.wall)
    return hub, cli, clock


def test_lists_are_long_and_distinct():
    hellos = load_lines("hellos-es.txt")
    waits = load_lines("waits-es.txt")
    assert len(hellos) >= 180
    assert len(waits) >= 166
    assert len(set(hellos)) == len(hellos)
    assert len(set(waits)) == len(waits)
    assert all(line.startswith("Hola,") for line in hellos)


def test_startup_uses_the_hello_list_not_the_wait_list(world):
    hub, _cli, _clock = world
    hellos = load_lines("hellos-es.txt")
    waits = load_lines("waits-es.txt")
    line = hub.startup()
    assert line == hellos[0]
    assert line not in waits
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


def test_wake_does_not_upload_the_same_breath(world):
    hub, cli, _clock = world
    result = hub.run("hola grok qué hora es")
    assert result.spoken == ["Hola."]
    assert cli.calls == []
    assert hub.brain.in_conversation


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
    waits = load_lines("waits-es.txt")
    result = hub.run("qué hora es")
    assert result.spoken[0] == waits[0]
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


def test_ok_closes_without_the_waiting_line(world):
    hub, cli, _clock = world
    hub.run("hola grok")
    before = hub.brain.settings.wait_index
    result = hub.run("ok")
    assert result.spoken == ["Vale."]
    assert hub.brain.settings.wait_index == before
    assert cli.calls == []
    assert not hub.brain.in_conversation


def test_local_model_closes_without_asking_grok(world):
    hub, cli, _clock = world

    class Close:
        def interpret(self, phrase, in_conversation):
            return {"accion": "cierre", "orden": "gracias", "texto": ""}

    hub.mind = Close()
    hub.run("hola grok")
    result = hub.run("graxias")
    assert result.spoken == ["De nada."]
    assert cli.calls == []
    assert not any("busque" in line.lower() or "ver" in line.lower() for line in result.spoken)


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


def test_locked_voice_is_the_only_one_heard(world):
    hub, _cli, _clock = world
    hub.brain.embedder_ready = True
    hub.brain.speakers.add("Ana", [[1.0, 0.0]], lock=True)
    assert hub.run("hola grok", speaker_id="Luis").spoken == []
    assert hub.run("hola grok", speaker_id="Ana").spoken


def test_new_print_name_never_leaves(world):
    hub, cli, _clock = world
    asked = hub.run("hola grok", unknown_print=True, vector=[0.2, 0.9])
    assert "cómo te llamas" in asked.spoken[0]
    named = hub.run("Ana", vector=[0.2, 0.9])
    assert "Ana" in named.spoken[0]
    assert hub.brain.speakers.locked is None
    assert cli.calls == []


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


def test_conversation_timeout_ignores_time_spent_busy(world):
    hub, _cli, clock = world
    hub.run("hola grok")
    clock.t += 30
    assert hub.brain.in_conversation
    clock.t += 61
    hub.tick()
    assert not hub.brain.in_conversation


def test_shutdown_is_only_an_effect_after_yes(world):
    hub, cli, _clock = world
    cli.classified = {"accion": "comando", "orden": "apagar", "texto": ""}
    asked = hub.run("comando apaga ya el chisme")
    assert not any(effect[0] == "shutdown" for effect in asked.effects)
    refused = hub.run("no")
    assert refused.spoken == ["Vale."]
    hub.run("comando apagar")
    accepted = hub.run("sí")
    assert any(effect[0] == "shutdown" for effect in accepted.effects)
    assert accepted.spoken[0] == "Apago."


def test_stop_music_is_not_pause_music(world):
    hub, _cli, _clock = world
    assert hub.run("comando para la musica").spoken == ["Paro la música."]
    assert hub.run("comando pausa la musica").spoken == ["Pauso."]


def test_log_names_the_mode_between_the_time_and_the_text(world):
    hub, _cli, _clock = world
    hub.run("hola")
    assert any(line.split("  ")[1:3] == ["modo escucha", "oí"] for line in hub.brain.logs)
    hub.run("hola grok")
    hub.run("qué tiempo hará mañana")
    assert any(line.split("  ")[1] == "modo conversación" for line in hub.brain.logs)


def test_windows_recognizer_is_not_rewritten_to_kroko(world):
    hub, cli, _clock = world
    hub.brain.recognizers = ["teclado", "windows", "kroko"]
    hub.brain.settings.recognizer = "kroko"
    said = hub.run("comando reconocedor windows").spoken[0]
    assert "windows" in said.lower()
    assert hub.brain.settings.recognizer == "windows"
    assert cli.calls == []


def test_unmatched_text_reaches_grok_unchanged(world):
    hub, cli, _clock = world

    class Pass:
        def interpret(self, phrase, in_conversation):
            return {"accion": "texto", "orden": "", "texto": "frase limpia que no debe usarse"}

    hub.mind = Pass()
    hub.run("qué tiempo hará mañana en casa")
    assert cli.calls
    assert cli.calls[0][0] == "converse"
    assert cli.calls[0][1] == "qué tiempo hará mañana en casa"


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


def test_one_loose_recognizer_character(world):
    hub, _cli, _clock = world
    said = hub.run("comando otro reconocedot").spoken[0]
    assert "teclado" in said.lower()
