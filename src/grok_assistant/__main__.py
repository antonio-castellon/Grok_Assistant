"""Grok Assistant, the PC body of the experiment."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--console" in args:
        from grok_assistant.console import run
        run()
        return
    from grok_assistant.tray import run
    run()


if __name__ == "__main__":
    main()
