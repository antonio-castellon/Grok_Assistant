"""Waiting lines while Grok searches. Cheeky ones stay rare."""

from grok_assistant.notebook.settings import Settings
from grok_assistant.speaking.waits import RARE, STYLES, buckets, catalog, pick


def test_each_language_has_the_five_styles():
    expect = {"plain": 20, "witty": 20, "dry": 18, "tech": 18, "cheeky": 20}
    for code in ("es", "en", "fr", "de"):
        rows = catalog(code)
        texts = [row["text"] for row in rows]
        assert len(texts) == 96
        assert len(texts) == len(set(texts))
        for style, count in expect.items():
            found = [row for row in rows if row["style"] == style]
            assert len(found) == count, f"{code} {style}"


def test_spanish_lines_are_the_requested_ones():
    texts = [row["text"] for row in catalog("es")]
    assert texts[0] == "Un momento, que lo miro."
    assert "Buscando... con cierta dignidad." in texts
    assert "Comprobando. Por higiene intelectual." in texts
    assert "Ningún servidor ha resultado herido." in " ".join(texts) or any(
        "Ningún servidor ha resultado herido." in line for line in texts
    )
    assert texts[-1] == "Buscando... el plan B sigue siendo buscar."


def test_cheeky_lines_are_one_in_eight_when_everything_is_on():
    rare = {row["text"] for row in catalog("es") if row["style"] == RARE}
    index = 0
    previous = ""
    hits = 0
    for _ in range(80):
        line, index = pick("es", None, index, previous)
        previous = line
        if line in rare:
            hits += 1
    assert hits == 10


def test_a_single_style_stays_inside_that_style():
    plain, rare = buckets("es", ["plain"])
    assert rare == []
    assert plain[0] == "Un momento, que lo miro."
    assert len(plain) == 20
    line, index = pick("es", ["cheeky"], 0)
    assert line == "Buscando... no toques nada."
    assert index == 1


def test_an_old_config_starts_with_every_wait_style(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"model": "grok-4.7"}', encoding="utf-8")
    loaded = Settings.load(path)
    assert loaded.wait_styles == list(STYLES)
