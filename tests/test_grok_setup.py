from grok_assistant.cloud.grok_cli import interpret_models
from grok_assistant.house.helptext import HELP_TOPICS
from grok_assistant.paths import bundle_root


def test_a_logged_in_model_list_is_ready():
    text = "You are logged in with grok.com.\nAvailable models:\n  * grok-4.7\n"
    assert interpret_models(text, "", 0) == "ready"


def test_a_sign_in_prompt_is_not_ready():
    assert interpret_models("", "Please sign in with grok login", 1) == "signed_out"


def test_the_command_guide_says_how_long_a_phrase_stays_open():
    import json

    from grok_assistant.i18n import bundled_dir

    body = next(text for title, text, _example in HELP_TOPICS if title.startswith("Motor"))
    assert "1,2 segundos" in body
    assert "0,4 segundos" in body
    assert "30 segundos" in body
    assert "2 segundos" in body
    assert "minutos de silencio" in body
    needles = {
        "en": ("1.2 seconds", "0.4 seconds", "30 seconds"),
        "fr": ("1,2 seconde", "0,4 seconde", "30 secondes"),
        "de": ("1,2 Sekunden", "0,4 Sekunden", "30 Sekunden"),
    }
    for code, parts in needles.items():
        pack = json.loads((bundled_dir() / f"{code}.json").read_text(encoding="utf-8"))
        stt = next(item["body"] for item in pack["help"] if "STT" in item["title"])
        for part in parts:
            assert part in stt


def test_every_help_topic_has_an_example():
    from grok_assistant.house.helptext import help_topics

    titles = []
    for title, body, example in help_topics():
        titles.append(title)
        assert body.strip()
        assert example.strip()
        assert "comando" in example or example.split()[0] in {"hola", "qué", "gracias", "pon"}
    assert len(titles) == len(set(titles))
    assert len(titles) >= 12


def test_startup_command_points_at_the_program():
    from grok_assistant.startup import quoted_command

    assert quoted_command(r"C:\DEV.Personal\Grok_Assistant\dist\GrokAssistant.exe") == (
        r'"C:\DEV.Personal\Grok_Assistant\dist\GrokAssistant.exe"'
    )


def test_account_percent_is_the_allowance_already_used():
    from grok_assistant.cloud.account_usage import percent_used

    assert percent_used({"config": {"creditUsagePercent": 79.4}}) == 79
    assert percent_used({"config": {}}) is None
    assert percent_used({}) is None


def test_bundle_root_is_the_checkout_when_not_frozen():
    assert (bundle_root() / "scripts" / "speak.ps1").exists()
    assert (bundle_root() / "listeners" / "dictation.ps1").exists()


def test_tray_keeps_the_full_module_handle():
    import ctypes
    from ctypes import wintypes

    from grok_assistant.ui import win_tray

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel.GetModuleHandleW.restype = wintypes.HMODULE
    full = int(kernel.GetModuleHandleW(None) or 0)
    seen = int(win_tray.kernel32.GetModuleHandleW(None) or 0)
    assert seen == full
    assert seen > 0
