from grok_assistant.grok_cli import interpret_models
from grok_assistant.helptext import HELP_TOPICS
from grok_assistant.paths import bundle_root


def test_a_logged_in_model_list_is_ready():
    text = "You are logged in with grok.com.\nAvailable models:\n  * grok-4.7\n"
    assert interpret_models(text, "", 0) == "ready"


def test_a_sign_in_prompt_is_not_ready():
    assert interpret_models("", "Please sign in with grok login", 1) == "signed_out"


def test_every_help_topic_has_an_example():
    titles = []
    for title, body, example in HELP_TOPICS:
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
    from grok_assistant.account_usage import percent_used

    assert percent_used({"config": {"creditUsagePercent": 79.4}}) == 79
    assert percent_used({"config": {}}) is None
    assert percent_used({}) is None


def test_bundle_root_is_the_checkout_when_not_frozen():
    assert (bundle_root() / "scripts" / "speak.ps1").exists()
    assert (bundle_root() / "listeners" / "dictation.ps1").exists()


def test_tray_keeps_the_full_module_handle():
    import ctypes
    from ctypes import wintypes

    from grok_assistant import win_tray

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel.GetModuleHandleW.restype = wintypes.HMODULE
    full = int(kernel.GetModuleHandleW(None) or 0)
    seen = int(win_tray.kernel32.GetModuleHandleW(None) or 0)
    assert seen == full
    assert seen > 0
