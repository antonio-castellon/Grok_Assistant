from grok_assistant.paths import bundle_root, ensure_license


def test_the_shipped_license_declines_responsibility_for_grok():
    text = (bundle_root() / "LICENSE.md").read_text(encoding="utf-8")
    assert "Antonio Castellon no se hace responsable" in text
    assert "fallo de seguridad" in text
    assert "experimental" in text.lower()


def test_the_license_is_copied_beside_the_program_once(tmp_path):
    source = tmp_path / "packed" / "LICENSE.md"
    source.parent.mkdir()
    source.write_text("límites\n", encoding="utf-8")
    folder = tmp_path / "beside"
    copied = ensure_license(folder, source)
    assert copied == folder / "LICENSE.md"
    assert copied.read_text(encoding="utf-8") == "límites\n"
    copied.write_text("editado\n", encoding="utf-8")
    ensure_license(folder, source)
    assert copied.read_text(encoding="utf-8") == "editado\n"
    assert ensure_license(tmp_path / "empty", tmp_path / "missing.md") is None
    assert not (tmp_path / "empty").exists()
