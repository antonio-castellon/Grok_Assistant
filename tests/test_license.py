from conftest import tk_root
from grok_assistant.paths import bundle_root, license_text


def test_the_shipped_license_declines_responsibility_for_grok():
    text = (bundle_root() / "LICENSE.md").read_text(encoding="utf-8")
    assert "Antonio Castellon no se hace responsable" in text
    assert "fallo de seguridad" in text
    assert "experimental" in text.lower()
    assert license_text() == text


def test_about_shows_the_license_on_its_own_tab(tmp_path):
    from grok_assistant.i18n import activate
    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    activate("es")
    root = tk_root()
    root.withdraw()
    try:
        app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
        app._build_about()
        book = app._about_win.winfo_children()[0]
        labels = [button.cget("text") for _page, button in book._tabs]
        assert labels == ["Acerca de", "Comandos", "Licencia"]
        about = book._tabs[0][0].winfo_children()[0].get("1.0", "end")
        license_page = book._tabs[2][0].winfo_children()[0].get("1.0", "end")
        assert "experimental" in about.lower()
        assert "LICENSE.md" not in about
        assert "Antonio Castellon no se hace responsable" in license_page
        commands = book._tabs[1][0].winfo_children()[0].get("1.0", "end")
        assert "Apagar el equipo" not in commands
        assert "micrófono sigue abierto" in commands
    finally:
        app._about_win.destroy()
        root.destroy()
