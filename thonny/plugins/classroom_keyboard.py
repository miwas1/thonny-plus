"""Final Classroom stdin wiring, independent of plugin import/load ordering."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from thonny import get_workbench
from thonny.plugins.classroom.ui import ClassroomView
from thonny.plugins.classroom_input import _original_init


def _init(self: ClassroomView, master: tk.Misc) -> None:
    _original_init(self, master)
    self._classroom_input_text = ""
    input_var = tk.StringVar(value="")
    input_var.trace_add(
        "write", lambda *_: setattr(self, "_classroom_input_text", input_var.get())
    )
    self.classroom_input = input_var
    toolbar = self.grid_slaves(row=0, column=0)[0]
    ttk.Entry(toolbar, textvariable=input_var, width=18).pack(side="right", padx=(4, 10))
    ttk.Label(toolbar, text="Input:").pack(side="right")


def _run_worker(self: ClassroomView, adapter, path, source) -> None:
    try:
        entered = self._classroom_input_text
        input_text = entered + ("\n" if entered and not entered.endswith("\n") else "")
        result = adapter.run_file(path, input_text=input_text)
        diagnostic = adapter.parse_diagnostics(result.stderr, source)
        get_workbench().after(0, self._finish_run, result, diagnostic)
    except Exception as exc:
        get_workbench().after(0, self._run_failed, str(exc))


def load_plugin() -> None:
    ClassroomView.__init__ = _init
    ClassroomView._run_worker = _run_worker
