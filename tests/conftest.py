"""Shared test helpers."""

from __future__ import annotations


def tk_root():
    """Open one Tk root.

    On the Windows CI image, Tcl sometimes fails a single read of a library
    file that is present (``button.tcl``, ``init.tcl``). The next ``Tk()`` in
    the same process succeeds. One retry covers that read. Any other Tcl
    error, and a library that is still unreadable on the second try, is raised.
    """
    import tkinter as tk

    last = None
    for attempt in range(2):
        try:
            return tk.Tk()
        except tk.TclError as exc:
            last = exc
            text = str(exc)
            transient = "usable tk.tcl" in text or "usable init.tcl" in text
            if attempt or not transient:
                raise
    raise last
