from grok_assistant.grok_cli import interpret_models
from grok_assistant.paths import bundle_root


def test_a_logged_in_model_list_is_ready():
    text = "You are logged in with grok.com.\nAvailable models:\n  * grok-4.7\n"
    assert interpret_models(text, "", 0) == "ready"


def test_a_sign_in_prompt_is_not_ready():
    assert interpret_models("", "Please sign in with grok login", 1) == "signed_out"


def test_bundle_root_is_the_checkout_when_not_frozen():
    assert (bundle_root() / "scripts" / "speak.ps1").exists()
    assert (bundle_root() / "listeners" / "dictation.ps1").exists()
