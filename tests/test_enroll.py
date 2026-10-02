"""One recording, one person. Each listener is scored from the saved sound."""

from grok_assistant.listening.ear_score import score_person
from grok_assistant.listening.enroll_audio import PHRASES, MIN_KEEP, phrase_hit, one_voice, read_wav, record_phrase, write_wav
from grok_assistant.notebook.store import SpeakerBook


def test_a_held_take_stays_open_until_seguir():
    from grok_assistant.listening.enroll_audio import TAKE_QUIET
    from grok_assistant.listening.kroko_ear import KrokoEar

    ear = KrokoEar(lambda *_: None)
    ear.set_hold(True)
    assert ear._capture_ready("hola", TAKE_QUIET, 2.0) is False
    ear.set_hold(False)
    assert ear._capture_ready("hola", TAKE_QUIET, 2.0) is True


def test_a_print_take_stays_open_through_a_short_pause():
    from grok_assistant.listening.enroll_audio import TAKE_MAX_VOICE, TAKE_MIN_VOICE, TAKE_QUIET, tone
    from grok_assistant.listening.kroko_ear import KrokoEar

    ear = KrokoEar(lambda *_: None, talk_mode=lambda: "saludo")
    assert ear._ready("qué hora es", 0.7, True) is False
    assert ear._ready("qué hora es", 1.2, True) is True
    assert ear._ready("hola grok", 1.2, True) is False
    fast = KrokoEar(lambda *_: None)
    assert fast._ready("hola grok", 0.7, True) is False
    assert fast._ready("hola grok", 1.2, True) is True
    assert TAKE_QUIET == 1.0
    assert ear._capture_ready("qué hora es", 0.5, 2.0) is False
    assert ear._capture_ready("qué hora es", TAKE_QUIET, 2.0) is True
    assert ear._capture_ready("", TAKE_QUIET, TAKE_MIN_VOICE - 0.1) is False
    assert ear._capture_ready("Hola, droga", 0.2, 0.0) is False
    assert ear._capture_ready("Hola, droga", TAKE_QUIET, 0.0) is True
    assert ear._capture_ready("", TAKE_QUIET, 2.0) is True
    assert ear._capture_ready("frase larga", 0.2, TAKE_MAX_VOICE) is True
    assert tone(True) == (880, 140)
    assert tone(False) == (494, 220)


def test_a_decoded_word_counts_as_sound_and_restarts_the_pause():
    from grok_assistant.listening.enroll_audio import TAKE_MIN_VOICE
    from grok_assistant.listening.kroko_ear import capture_has_sound, note_capture_speech

    mark, quiet, voiced = note_capture_speech("", "Hola, droga", 2.0, 0.0)
    assert mark == "Hola, droga"
    assert quiet == 0.0
    assert voiced == TAKE_MIN_VOICE
    same, quiet, voiced = note_capture_speech(mark, "Hola, droga", 0.4, voiced)
    assert same == mark
    assert quiet == 0.4
    grown, quiet, _voiced = note_capture_speech(mark, ". Hola, Grog", 1.0, voiced)
    assert grown == ". Hola, Grog"
    assert quiet == 0.0
    assert capture_has_sound("Hola, droga", 0.0) is True
    assert capture_has_sound("", 0.2) is True
    assert capture_has_sound("", 0.0) is False
    assert capture_has_sound("   ", 0.0) is False


def test_sixteen_different_phrases():
    assert len(PHRASES) == 16
    assert len(set(PHRASES)) == 16
    assert MIN_KEEP == 12


def test_the_greeting_phrase_uses_the_wake_name():
    from grok_assistant.listening.enroll_audio import enroll_phrases

    assert enroll_phrases("Miguel")[0] == "hola Miguel"
    assert enroll_phrases("Miguel")[1:] == PHRASES[1:]
    assert enroll_phrases("grok") == PHRASES
    assert enroll_phrases("  ") == PHRASES
    assert len(set(enroll_phrases("Miguel"))) == 16


def test_a_known_phrase_is_a_hit_only_when_the_words_arrive():
    assert phrase_hit("hola grok", "Ola grok")
    assert phrase_hit("qué hora es", "que hora es")
    assert phrase_hit("pon una canción", "pon una cancion de jazz")
    assert not phrase_hit("hola grok", "hola")
    assert not phrase_hit("sube el volumen", "baja el volumen")
    assert not phrase_hit("qué hora es", "")


def test_one_person_stays_one_print_and_a_split_is_refused():
    same = [[1.0, 0.0] for _ in range(16)]
    assert one_voice(same) == list(range(16))
    mixed = [[1.0, 0.0] for _ in range(12)] + [[0.0, 1.0] for _ in range(4)]
    assert one_voice(mixed) == list(range(12))
    split = [[1.0, 0.0] for _ in range(8)] + [[0.0, 1.0] for _ in range(8)]
    assert one_voice(split) is None
    short = [[1.0, 0.0] for _ in range(11)]
    assert one_voice(short) is None


def test_a_quiet_microphone_returns_nothing():
    import numpy as np

    quiet = np.zeros(1600, dtype=np.float32)

    def read(_count):
        return quiet

    assert record_phrase(read=read, seconds=0.4) is None


def test_a_phrase_ends_when_the_voice_stops():
    import numpy as np

    loud = np.full(1600, 0.05, dtype=np.float32)
    quiet = np.zeros(1600, dtype=np.float32)
    blocks = [loud] * 5 + [quiet] * 8

    def read(_count):
        return blocks.pop(0)

    audio = record_phrase(read=read, seconds=5)
    assert audio is not None
    assert audio.size >= 1600 * 5


def test_raw_sound_builds_one_print_for_every_listener(tmp_path):
    book = SpeakerBook(tmp_path / "speakers.json")
    samples = [0.01] * 1600
    clips = [{"phrase": phrase, "samples": samples} for phrase in PHRASES]
    book.store_recording("Ana", clips, [[1.0, 0.0] for _ in PHRASES], lock=True)
    assert book.take_count("Ana") == 16
    assert book.closest([1.0, 0.0], "whisper") == "Ana"
    assert book.closest([1.0, 0.0], "kroko") == "Ana"
    assert book.closest([1.0, 0.0], "windows") == "Ana"
    assert book.closest([0.0, 1.0], "whisper") is None
    wav = book.raw_root() / book.raw_clips("Ana")[0]["file"]
    assert read_wav(wav) is not None
    book.rename("Ana", "Ana María")
    moved = book.raw_root() / book.raw_clips("Ana María")[0]["file"]
    assert moved.exists()
    assert not wav.exists()
    book.delete("Ana María")
    assert book.names() == []
    assert not moved.exists()


def test_each_listener_is_scored_from_the_same_raw(tmp_path):
    book = SpeakerBook(tmp_path / "speakers.json")
    clips = []
    for index, phrase in enumerate(PHRASES):
        clips.append({"phrase": phrase, "samples": [0.01 * (index + 1)] * 8})
    book.store_recording("Ana", clips, [[1.0, 0.0] for _ in PHRASES], True)

    def hear(ear, audio):
        if ear != "whisper" or audio is None:
            return ""
        index = int(round(float(audio[0]) / 0.01)) - 1
        if 0 <= index < len(PHRASES) and index % 2 == 0:
            return PHRASES[index]
        return "ruido"

    hits, total = score_person(book, "Ana", "whisper", transcribe=hear)
    assert total == 16
    assert hits == 8
    assert book.score_of("Ana", "whisper") == (8, 16)
    assert book.accuracies("Ana") == {"whisper": 50}
    assert book.pending_scores(["whisper", "kroko"]) == [("Ana", "kroko")]


def test_a_score_is_a_whole_percent_beside_the_library(tmp_path):
    from grok_assistant.listening.listen import eligible_ears, highest_accuracy, with_accuracy

    book = SpeakerBook(tmp_path / "speakers.json")
    book.people["Ana"] = {
        "prints": {},
        "scores": {
            "whisper": {"hits": 15, "total": 16},
            "kroko": {"hits": 1, "total": 3},
            "base": {"hits": 1, "total": 0},
            "canary": "no",
        },
    }
    assert book.accuracies("Ana") == {"whisper": 94, "kroko": 33}
    assert book.accuracies("Nadie") == {}
    book.people["Luis"] = {
        "prints": {},
        "scores": {
            "whisper": {"hits": 4, "total": 16},
            "kroko": {"hits": 16, "total": 16},
        },
    }
    book.people["Ana"]["scores"]["kroko"] = {"hits": 14, "total": 16}
    assert book.accuracies("Ana")["whisper"] > book.accuracies("Ana")["kroko"]
    assert book.combined_accuracies() == {"whisper": 59, "kroko": 94}
    assert highest_accuracy(book.combined_accuracies(), ["kroko", "whisper"], "whisper") == "kroko"
    assert SpeakerBook(tmp_path / "empty.json").combined_accuracies() == {}
    assert with_accuracy("Whisper pequeño", 94) == "Whisper pequeño (94%)"
    assert with_accuracy("Kroko", None) == "Kroko"
    available = ["teclado", "windows", "kroko", "whisper"]
    assert highest_accuracy({"kroko": 80, "whisper": 94, "windows": 70}, available, "kroko") == "whisper"
    assert highest_accuracy({"kroko": 90, "whisper": 90}, available, "kroko") == "kroko"
    assert highest_accuracy({}, available, "windows") == "windows"
    assert highest_accuracy({"teclado": 100, "whisper": 10}, ["whisper"], "kroko") == "whisper"
    assert eligible_ears(available, "es") == ["windows", "kroko", "whisper"]
    assert eligible_ears(available + ["base"], "en") == ["whisper", "base"]


def test_a_heard_take_gets_a_campplus_vector():
    import numpy as np
    import pytest

    pytest.importorskip("sherpa_onnx")
    from grok_assistant.listening.voiceprint import VoicePrint

    printer = VoicePrint()
    if not printer.ready():
        pytest.skip("campplus model is not installed")
    short = np.zeros(1600, dtype=np.float32)
    assert printer.embed(short) is None
    audio = np.random.default_rng(1).normal(0, 0.02, 16000).astype(np.float32)
    vector = printer.embed(audio)
    assert vector is not None
    assert len(vector) == 192
    again = printer.embed(audio)
    assert again is not None
    assert len(again) == len(vector)


def test_wav_roundtrip_keeps_the_phrase(tmp_path):
    import numpy as np

    path = tmp_path / "00.wav"
    source = np.linspace(-0.2, 0.2, 1600, dtype=np.float32)
    write_wav(path, source)
    back = read_wav(path)
    assert back is not None
    assert abs(float(back[0]) - float(source[0])) < 0.01
    assert abs(float(back[-1]) - float(source[-1])) < 0.01
