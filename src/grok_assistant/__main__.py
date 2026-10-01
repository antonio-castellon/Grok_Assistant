"""Grok Assistant, the PC body of the experiment."""

from __future__ import annotations

import faulthandler
import sys
import tempfile
import traceback
from pathlib import Path

from grok_assistant.paths import bundle_root, default_data_dir, load_lines

_FAULT_LOG = None


def main(argv: list[str] | None = None) -> None:
    try:
        folder = default_data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        crash = folder / "crash.log"
        # The file has to stay referenced or a later native fault has nowhere to land.
        global _FAULT_LOG
        _FAULT_LOG = crash.open("a", encoding="utf-8")
        faulthandler.enable(_FAULT_LOG, all_threads=True)
    except OSError:
        pass
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
    from grok_assistant.cloud.setup_grok import ensure_grok
    from grok_assistant.ui.app import run

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


def _importable(name: str) -> bool:
    try:
        __import__(name)
    except Exception:
        return False
    return True


def _kroko_ready() -> bool:
    from grok_assistant.listening.kroko_ear import kroko_dir

    return kroko_dir() is not None


def _write_check() -> None:
    from grok_assistant import __version__
    from grok_assistant.cloud.grok_cli import GrokCLI
    from grok_assistant.cloud.setup_grok import probe

    status = probe()
    lines = [
        f"version={__version__}",
        "channel=release-candidate",
        f"hellos={len(load_lines('hellos-es.txt'))}",
        f"scripts={(bundle_root() / 'scripts' / 'speak.ps1').exists()}",
        f"listeners={(bundle_root() / 'listeners' / 'dictation.ps1').exists()}",
        f"grok={GrokCLI.find() or ''}",
        f"state={status.state}",
        f"kroko_model={_kroko_ready()}",
        f"sherpa={_importable('sherpa_onnx')}",
        f"mic={_importable('sounddevice')}",
    ]
    Path(tempfile.gettempdir(), "GrokAssistant-check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
