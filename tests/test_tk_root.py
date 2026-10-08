"""The Tk opener retries one broken library read and still reports a real failure."""

import tkinter

import pytest

from conftest import tk_root


def test_tk_root_retries_one_broken_library_read(monkeypatch):
    calls = []

    class Root:
        def __init__(self):
            calls.append(1)
            if len(calls) == 1:
                raise tkinter.TclError("Can't find a usable tk.tcl in the following directories: button.tcl")
            self.opened = True

    monkeypatch.setattr(tkinter, "Tk", Root)
    root = tk_root()
    assert root.opened is True
    assert calls == [1, 1]


def test_tk_root_does_not_hide_another_tcl_error(monkeypatch):
    def boom(*_args, **_kwargs):
        raise tkinter.TclError("bad window path name")

    monkeypatch.setattr(tkinter, "Tk", boom)
    with pytest.raises(tkinter.TclError, match="bad window path name"):
        tk_root()


def test_tk_root_reports_a_library_that_stays_unreadable(monkeypatch):
    calls = []

    def boom(*_args, **_kwargs):
        calls.append(1)
        raise tkinter.TclError("Can't find a usable init.tcl")

    monkeypatch.setattr(tkinter, "Tk", boom)
    with pytest.raises(tkinter.TclError, match="usable init.tcl"):
        tk_root()
    assert calls == [1, 1]
