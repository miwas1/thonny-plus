"""Connect the Classroom tutor card to the bundled Qwen worker when available."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from thonny import get_workbench
from thonny.plugins.classroom.runtime import application_root
from thonny.plugins.classroom.tutor import TutorWorkerClient, deterministic_response, render_response
from thonny.plugins.classroom.ui import ClassroomView


def _client() -> TutorWorkerClient | None:
    tutor_dir = application_root() / "tutor"
    suffix = ".exe" if os.name == "nt" else ""
    llama_cli = tutor_dir / f"llama-cli{suffix}"
    model = tutor_dir / "qwen-coder-1.5b-q4_k_m.gguf"
    if not llama_cli.is_file() or not model.is_file():
        return None
    command = [sys.executable, "-m", "thonny.plugins.classroom.model_worker",
               "--llama-cli", str(llama_cli), "--model", str(model)]
    return TutorWorkerClient(command)


def _show_tutor(self: ClassroomView, action) -> None:
    diagnostic = self._diagnostic
    if diagnostic is None:
        self._set_tutor("Run the program first. If it reports an error, I can explain it "
                        "without writing the solution for you.")
        return
    client = _client()
    hint_count = self._hint_count
    if action == "hint":
        self._hint_count += 1
    if client is None:
        self._set_tutor(render_response(deterministic_response(diagnostic, action), action))
        return
    self._set_tutor("Thinking on this computer…")

    def ask() -> None:
        try:
            response = client.ask(diagnostic, action, previous_hint_count=hint_count, timeout=150.0)
        except Exception:
            response = deterministic_response(diagnostic, action)
        get_workbench().after(0, self._set_tutor, render_response(response, action))

    threading.Thread(target=ask, daemon=True, name="classroom-tutor-request").start()


def load_plugin() -> None:
    ClassroomView.show_tutor = _show_tutor
