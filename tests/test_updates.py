import tkinter as tk

from grok_assistant.house.updates import apply_update, asset_url, choose_update, find_update, parse_build
from grok_assistant.paths import resource_root

PREFIX = "https://github.com/antonio-castellon/Grok_Assistant/releases/download/"


def _release(tag, published, body, url=None, draft=False, name="GrokAssistant.exe"):
    assets = []
    if url is not None:
        assets.append({"name": name, "browser_download_url": url})
    return {
        "tag_name": tag,
        "published_at": published,
        "body": body,
        "draft": draft,
        "assets": assets,
    }


def test_choose_update_picks_the_newest_different_build():
    releases = [
        _release("v1.0-rc", "2026-10-02T00:00:00Z", "build: bbbbbbbbbbbb", PREFIX + "v1.0-rc/GrokAssistant.exe"),
        _release("v1.0-rc.2", "2026-10-03T00:00:00Z", "build: cccccccccccc", PREFIX + "v1.0-rc.2/GrokAssistant.exe"),
    ]
    offer = choose_update(releases, "aaaaaaaaaaaa", "2026-10-01T00:00:00Z")
    assert offer["tag"] == "v1.0-rc.2"
    assert offer["build"] == "cccccccccccc"
    assert offer["url"].endswith("/v1.0-rc.2/GrokAssistant.exe")


def test_the_same_build_is_not_an_update():
    releases = [_release("v1.0-rc.2", "2026-10-02T00:00:00Z", "Build: aaaaaaaaaaaa", PREFIX + "v1.0-rc.2/GrokAssistant.exe")]
    assert choose_update(releases, "aaaaaaaaaaaa", "2026-10-01T00:00:00Z") is None


def test_an_older_release_is_not_an_update():
    releases = [_release("v1.0-rc", "2026-09-01T00:00:00Z", "build: bbbbbbbbbbbb", PREFIX + "v1.0-rc/GrokAssistant.exe")]
    assert choose_update(releases, "aaaaaaaaaaaa", "2026-10-01T00:00:00Z") is None


def test_a_release_without_a_build_line_or_the_executable_is_ignored():
    url = PREFIX + "v1.0-rc/GrokAssistant.exe"
    assert choose_update([_release("v1.0-rc", "2026-10-02T00:00:00Z", "Release candidate", url)], "aaaaaaaaaaaa", "2026-10-01T00:00:00Z") is None
    assert choose_update([_release("v1.0-rc.2", "2026-10-02T00:00:00Z", "build: bbbbbbbbbbbb")], "aaaaaaaaaaaa", "2026-10-01T00:00:00Z") is None


def test_a_foreign_download_and_a_draft_are_ignored():
    foreign = _release("v1.0-rc.2", "2026-10-02T00:00:00Z", "build: bbbbbbbbbbbb", "https://evil.example/GrokAssistant.exe")
    draft = _release("v1.0-rc.2", "2026-10-02T00:00:00Z", "build: bbbbbbbbbbbb", PREFIX + "v1.0-rc.2/GrokAssistant.exe", draft=True)
    assert choose_update([foreign], "aaaaaaaaaaaa", "2026-10-01T00:00:00Z") is None
    assert choose_update([draft], "aaaaaaaaaaaa", "2026-10-01T00:00:00Z") is None
    assert asset_url(foreign) == ""
    assert parse_build("notes\nbuild: abcdef\n") == "abcdef"


def test_a_missing_local_stamp_offers_nothing():
    releases = [_release("v1.0-rc.2", "2026-10-02T00:00:00Z", "build: bbbbbbbbbbbb", PREFIX + "v1.0-rc.2/GrokAssistant.exe")]
    assert choose_update(releases, "", "2026-10-01T00:00:00Z") is None
    assert choose_update(releases, "aaaaaaaaaaaa", "") is None


def test_a_source_checkout_does_not_offer_or_replace_itself():
    assert find_update() is None
    assert apply_update({"url": PREFIX + "v1.0-rc.2/GrokAssistant.exe"}) is False


def test_an_installed_package_uses_its_own_bundle(tmp_path):
    package = tmp_path / "site-packages" / "grok_assistant"
    bundled = package / "_bundle"
    (bundled / "scripts").mkdir(parents=True)
    (bundled / "scripts" / "speak.ps1").write_text("ok", encoding="utf-8")
    assert resource_root(package / "paths.py") == bundled.resolve()

    repo = tmp_path / "repo" / "src" / "grok_assistant"
    (repo.parents[1] / "scripts").mkdir(parents=True)
    (repo.parents[1] / "scripts" / "speak.ps1").write_text("real", encoding="utf-8")
    (repo / "_bundle" / "scripts").mkdir(parents=True)
    (repo / "_bundle" / "scripts" / "speak.ps1").write_text("staged", encoding="utf-8")
    assert resource_root(repo / "paths.py") == repo.parents[1].resolve()


def test_the_file_menu_names_internet_and_this_machine():
    from grok_assistant.i18n import activate, code, text

    previous = code()
    try:
        activate("es")
        assert text("menu.files_off") == "Grok solo busca en internet"
        assert text("menu.files_on") == "Grok puede cambiar archivos de esta máquina"
        activate("en")
        assert text("menu.files_off") == "Grok only searches the internet"
        assert text("menu.files_on") == "Grok may change files on this machine"
    finally:
        activate(previous)


def test_the_update_button_appears_only_when_there_is_one(tmp_path):
    from grok_assistant.i18n import activate
    from grok_assistant.rules.hub import build
    from grok_assistant.ui.app import TrayApp

    activate("es")
    root = tk.Tk()
    root.withdraw()
    app = TrayApp(root, build(tmp_path, tmp_path / "agents"))
    try:
        assert app.update_button not in app.footer.pack_slaves()
        app._build_about()
        about = app._about_win.winfo_children()[0]._tabs[0][0].winfo_children()[0].get("1.0", "end")
        assert about.count("(build ") == 1
        assert "v1.0-rc.3" in about
        app._update_offer = {"tag": "v1.0-rc.2", "url": PREFIX + "v1.0-rc.2/GrokAssistant.exe", "build": "bbbbbbbbbbbb"}
        app._place_update_button()
        assert app.update_button in app.footer.pack_slaves()
        assert app.update_button.cget("text") == "Actualizar"
    finally:
        root.destroy()
