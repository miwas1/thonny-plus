"""Connect the Python assistant view to one persistent bundled Qwen worker."""

from __future__ import annotations

import os
import sys
import threading

from thonny import get_workbench
from thonny.plugins.classroom.runtime import application_root
from thonny.plugins.classroom.tutor import (
    TutorWorkerClient,
    deterministic_response,
    render_response,
)
from thonny.plugins.classroom.ui import ClassroomView

_worker_client: TutorWorkerClient | None = None


def _client() -> TutorWorkerClient | None:
    global _worker_client
    if _worker_client is not None:
        return _worker_client
    tutor_dir = application_root() / "tutor"
    suffix = ".exe" if os.name == "nt" else ""
    llama_server = tutor_dir / f"llama-server{suffix}"
    model = tutor_dir / "qwen-coder-1.5b-q4_k_m.gguf"
    if not llama_server.is_file() or not model.is_file():
        return None
    command = [
        sys.executable,
        "-m",
        "thonny.plugins.classroom.model_worker",
        "--llama-server",
        str(llama_server),
        "--model",
        str(model),
    ]
    _worker_client = TutorWorkerClient(command)
    return _worker_client


def _show_tutor(self: ClassroomView, action, context=None) -> None:
    context = context or self._tutor_context()
    if (
        not context.source_excerpt
        and not context.actual_output
        and context.diagnostic is None
    ):
        self._set_tutor("Open a Python file or write a few lines first.")
        return
    client = _client()
    hint_count = self._hint_count
    if action == "hint":
        self._hint_count += 1
    if client is None:
        self._set_tutor(
            render_response(deterministic_response(context, action), action)
        )
        self.set_ai_status("Built-in guidance · local model unavailable")
        return
    if not client.is_ready:
        self._set_tutor(
            render_response(deterministic_response(context, action), action)
        )
        self.set_ai_status("Instant guidance · local AI is still loading")
        return
    self._tutor_request_id += 1
    request_id = self._tutor_request_id
    self._set_tutor_partial("Preparing explanation…")
    self._set_tutor_busy(True)
    self.set_ai_status("Generating locally…")

    def stream_partial(text: str) -> None:
        get_workbench().after(
            0,
            _deliver_partial,
            self,
            request_id,
            text,
        )

    def ask() -> None:
        used_fallback = False
        try:
            response = client.ask(
                context,
                action,
                previous_hint_count=hint_count,
                timeout=180.0,
                on_partial=stream_partial,
            )
        except Exception:
            response = deterministic_response(context, action)
            used_fallback = True
        if request_id == self._tutor_request_id:
            get_workbench().after(
                0,
                _deliver_response,
                self,
                render_response(response, action),
                used_fallback,
            )

    threading.Thread(target=ask, daemon=True, name="local-tutor-request").start()


def _deliver_partial(view: ClassroomView, request_id: int, text: str) -> None:
    if request_id == view._tutor_request_id:
        view._set_tutor_partial(text)


def _deliver_response(view: ClassroomView, text: str, used_fallback: bool) -> None:
    view._set_tutor(text)
    view.set_ai_status(
        "Built-in guidance · local AI was unavailable"
        if used_fallback
        else "Local AI ready"
    )


def _prewarm(event=None) -> None:
    workbench = get_workbench()
    view = workbench.get_view("ClassroomView")
    client = _client()
    if client is None:
        view.set_ai_status("Built-in guidance · local model unavailable")
        return
    view.set_ai_status("Loading local AI once…")

    def warm() -> None:
        try:
            client.start(timeout=600.0)
            status = "Local AI ready"
        except Exception:
            status = "Built-in guidance · local AI was unavailable"
        workbench.after(0, view.set_ai_status, status)

    threading.Thread(target=warm, daemon=True, name="local-tutor-prewarm").start()


def load_plugin() -> None:
    ClassroomView.show_tutor = _show_tutor
    get_workbench().bind("WorkbenchReady", _prewarm, True)
