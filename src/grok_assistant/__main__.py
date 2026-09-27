"""Grok Assistant, the PC body of the experiment."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from grok_assistant.paths import bundle_root, load_lines


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check" in args:
        _write_check()
        return
    if "--console" in args:
        from grok_assistant.console import run
        run()
        return
    from grok_assistant.setup_grok import ensure_grok
    from grok_assistant.tray import run

    ensure_grok()
    run()


def _write_check() -> None:
    from grok_assistant import __version__
    from grok_assistant.grok_cli import GrokCLI
    from grok_assistant.setup_grok import probe

    status = probe()
    lines = [
        f"version={__version__}",
        f"hellos={len(load_lines('hellos-es.txt'))}",
        f"scripts={(bundle_root() / 'scripts' / 'speak.ps1').exists()}",
        f"listeners={(bundle_root() / 'listeners' / 'dictation.ps1').exists()}",
        f"grok={GrokCLI.find() or ''}",
        f"state={status.state}",
    ]
    Path(tempfile.gettempdir(), "GrokAssistant-check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
