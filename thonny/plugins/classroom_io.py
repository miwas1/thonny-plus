"""Thread-safe standard-input handoff for the Classroom process worker."""

from __future__ import annotations

from thonny import get_workbench
from thonny.plugins.classroom.ui import ClassroomView

_input_init = ClassroomView.__init__


def _init(self, master) -> None:
    _input_init(self, master)
    self._classroom_input_text = self.classroom_input.get()
    self.classroom_input.trace_add(
        "write", lambda *_: setattr(self, "_classroom_input_text", self.classroom_input.get())
    )


def _run_worker(self, adapter, path, source) -> None:
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
