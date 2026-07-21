from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, ttk

from thonny import get_workbench
from thonny.codeview import get_syntax_options_for_tag
from thonny.plugins.classroom.adapters import Diagnostic, PythonAdapter, normalize_error_type
from thonny.plugins.classroom.tutor import (
    TutorAction,
    TutorContext,
    TutorTrigger,
    context_from_run,
    deterministic_response,
    looks_like_test_results,
    render_response,
    select_tutor_action,
)

RUN_COMMANDS = {"run", "debug", "fastdebug"}


class ClassroomView(ttk.Frame):
    """A small AI companion for Thonny's native Python workflow."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.status = tk.StringVar(value="Local AI is starting…")
        self._diagnostic: Diagnostic | None = None
        self._hint_count = 0
        self._last_source = ""
        self._last_output = ""
        self._test_results = ""
        self._successful_runs = 0
        self._diagnostic_runs = 0
        self._tutor_request_id = 0
        self._run_in_progress = False

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(9, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Python assistant", font="TkHeadingFont").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(header, text="● Private", command=self._show_privacy).grid(
            row=0, column=1, sticky="e"
        )
        ttk.Label(header, textvariable=self.status).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        self.tutor_text = tk.Text(
            self,
            height=12,
            wrap="word",
            state="disabled",
            **get_syntax_options_for_tag("TEXT"),
        )
        self.tutor_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 7))

        self.action_button = ttk.Button(
            self, text="Explain this code", command=self._request_contextual_help
        )
        self.action_button.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        workbench = get_workbench()
        workbench.bind("CommandAccepted", self._on_command_accepted, True)
        workbench.bind("ProgramOutput", self._on_program_output, True)
        workbench.bind("ToplevelResponse", self._on_toplevel_response, True)
        workbench.bind("NotebookTabChanged", self._on_editor_changed, True)
        self._set_tutor(
            "Run your Python program with Thonny's normal Run button. "
            "If Python raises an error, a short explanation will appear here automatically."
        )
        self.status.set("Preparing local AI…")

    def _editor(self):
        return get_workbench().get_editor_notebook().get_current_editor()

    def _on_command_accepted(self, event) -> None:
        command = getattr(event, "command", None)
        name = str(getattr(command, "name", "")).lower()
        if name not in RUN_COMMANDS:
            return
        editor = self._editor()
        self._last_source = editor.get_content() if editor is not None else ""
        self._last_output = ""
        self._test_results = ""
        self._diagnostic = None
        self._hint_count = 0
        self._run_in_progress = True
        self._clear_error_highlight()
        self.action_button.configure(text="Explain this code")
        self.status.set("Watching this run…")

    def _on_program_output(self, event) -> None:
        if self._run_in_progress:
            self._last_output = (self._last_output + str(event.data))[-6000:]

    def _on_toplevel_response(self, response) -> None:
        command_name = str(response.get("command_name", "")).lower()
        user_exception = response.get("user_exception")
        if not self._run_in_progress and command_name not in RUN_COMMANDS and not user_exception:
            return
        self._run_in_progress = False
        editor = self._editor()
        if editor is not None:
            self._last_source = editor.get_content()

        if not user_exception:
            self._successful_runs += 1
            self._diagnostic = None
            self.action_button.configure(text="Explain this code")
            self.status.set("Local AI ready")
            return

        raw_exception = "".join(str(item[0]) for item in user_exception.get("items", ()))
        type_name = str(user_exception.get("type_name", "PythonError"))
        message = str(user_exception.get("message", "Python reported an error"))
        if not raw_exception:
            raw_exception = f"{type_name}: {message}"
        parser = PythonAdapter()
        diagnostic = parser.parse_diagnostics(raw_exception, self._last_source)
        if diagnostic is None:
            diagnostic = Diagnostic(
                language="python",
                execution_phase="syntax" if type_name in {"SyntaxError", "IndentationError"} else "runtime",
                error_type=normalize_error_type(type_name, message),
                line=self._exception_line(raw_exception),
                column=None,
                raw_message=f"{type_name}: {message}",
                relevant_code=parser.extract_relevant_context(
                    self._last_source, self._exception_line(raw_exception)
                ),
            )
        self._diagnostic = diagnostic
        self._last_output = (self._last_output + "\n" + raw_exception).strip()
        self._test_results = self._last_output if looks_like_test_results(self._last_output) else ""
        self._diagnostic_runs += 1
        self._highlight_line(diagnostic.line)
        self.action_button.configure(text="Give me one hint")
        self.status.set("Explaining the error…")
        self.request_tutor("run")

    @staticmethod
    def _exception_line(raw_exception: str) -> int | None:
        matches = re.findall(r"line (\d+)", raw_exception)
        return int(matches[-1]) if matches else None

    def _on_editor_changed(self, event=None) -> None:
        if self._diagnostic is None:
            self.action_button.configure(text="Explain this code")

    def _request_contextual_help(self) -> None:
        self.request_tutor("hint" if self._diagnostic else "help")

    def request_tutor(self, trigger: TutorTrigger) -> None:
        context = self._tutor_context()
        action = select_tutor_action(
            context,
            trigger,
            hint_count=self._hint_count,
            successful_runs=self._successful_runs,
            diagnostic_runs=self._diagnostic_runs,
        )
        self.show_tutor(action, context)

    def show_tutor(
        self, action: TutorAction, context: TutorContext | None = None
    ) -> None:
        context = context or self._tutor_context()
        if not context.source_excerpt and not context.diagnostic:
            self._set_tutor("Open a Python file or write a few lines first.")
            return
        response = deterministic_response(context, action)
        if action == "hint":
            self._hint_count += 1
        self._set_tutor(render_response(response, action))

    def _tutor_context(self) -> TutorContext:
        editor = self._editor()
        source = editor.get_content() if editor is not None else self._last_source
        progress_parts = []
        if self._successful_runs:
            progress_parts.append(f"completed {self._successful_runs} successful run(s)")
        if self._diagnostic_runs:
            progress_parts.append(
                f"investigated {self._diagnostic_runs} run(s) with diagnostics"
            )
        return context_from_run(
            language="python",
            source=source,
            diagnostic=self._diagnostic,
            actual_output=self._last_output,
            test_results=self._test_results,
            session_progress=" and ".join(progress_parts),
        )

    def _set_tutor(self, text: str) -> None:
        self.tutor_text.configure(state="normal")
        self.tutor_text.delete("1.0", "end")
        self.tutor_text.insert("1.0", text)
        self.tutor_text.configure(state="disabled")
        self._set_tutor_busy(False)

    def _set_tutor_busy(self, busy: bool) -> None:
        self.action_button.configure(state="disabled" if busy else "normal")

    def set_ai_status(self, text: str) -> None:
        self.status.set(text)

    def _highlight_line(self, line: int | None) -> None:
        editor = self._editor()
        if editor is None or line is None:
            return
        text = editor.get_text_widget()
        text.tag_configure(
            "classroom_error", **get_syntax_options_for_tag("exception_focus")
        )
        text.tag_remove("classroom_error", "1.0", "end")
        text.tag_add("classroom_error", f"{line}.0", f"{line}.end")
        text.see(f"{line}.0")

    def _clear_error_highlight(self) -> None:
        editor = self._editor()
        if editor is not None:
            editor.get_text_widget().tag_remove("classroom_error", "1.0", "end")

    def _show_privacy(self) -> None:
        messagebox.showinfo(
            "Offline and private",
            "The assistant runs from a model stored on this computer.\n"
            "Your Python code and errors are not sent over the internet.",
        )


def load_classroom_ui() -> None:
    get_workbench().add_view(
        ClassroomView,
        "AI Assistant",
        "e",
        visible_by_default=True,
        default_position_key="000",
    )
