"""Grok Assistant, the PC body of the experiment."""

from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path

from grok_assistant.paths import bundle_root, default_data_dir, load_lines


def main(argv: list[str] | None = None) -> None:
    try:
        _main(argv)
    except Exception:
        path = _crash_log()
        _tell_crash(path)
        raise SystemExit(1)


def _main(argv: list[str] | None) -> None:
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


def _crash_log() -> Path:
    folder = default_data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "crash.log"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(traceback.format_exc())
        handle.write("\n")
    return path


def _tell_crash(path: Path) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Grok Assistant", f"Se cerró por un error.\n{path}")
        root.destroy()
    except Exception:
        return


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
