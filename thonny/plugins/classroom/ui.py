from __future__ import annotations

import re
import tkinter as tk
from dataclasses import replace
from tkinter import messagebox, ttk

from thonny import get_shell, get_workbench
from thonny.codeview import get_syntax_options_for_tag
from thonny.plugins.classroom.adapters import (
    Diagnostic,
    PythonAdapter,
    normalize_error_type,
)
from thonny.plugins.classroom.tutor import (
    TutorAction,
    TutorContext,
    TutorLength,
    TutorTrigger,
    bounded_text,
    context_from_run,
    deterministic_response,
    looks_like_test_results,
    render_response,
    select_tutor_action,
)

RUN_COMMANDS = {"run", "debug", "fastdebug"}

ACTION_BUTTON_MODES = {
    "program": ("Explain this code", "#2563EB", "#1D4ED8"),
    "selected_code": ("Explain selected code", "#0F766E", "#115E59"),
    "selected_output": ("Explain selected output", "#B45309", "#92400E"),
    "hint": ("Give me one hint", "#7C3AED", "#6D28D9"),
}


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
        self._selection_origin: str | None = None
        self._detailed = tk.BooleanVar(value=False)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(9, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Python assistant", font="TkHeadingFont").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Checkbutton(
            header, text="Detailed", variable=self._detailed
        ).grid(row=0, column=1, sticky="e", padx=(0, 8))
        ttk.Button(header, text="● Private", command=self._show_privacy).grid(
            row=0, column=2, sticky="e"
        )
        ttk.Label(header, textvariable=self.status).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )

        self.tutor_text = tk.Text(
            self,
            height=12,
            wrap="word",
            state="disabled",
            **get_syntax_options_for_tag("TEXT"),
        )
        self.tutor_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 7))

        self.action_button = tk.Button(
            self,
            command=self._request_contextual_help,
            foreground="white",
            disabledforeground="#D1D5DB",
            relief="flat",
            borderwidth=0,
            pady=7,
            cursor="hand2",
        )
        self.action_button.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        workbench = get_workbench()
        workbench.bind("CommandAccepted", self._on_command_accepted, True)
        workbench.bind("ProgramOutput", self._on_program_output, True)
        workbench.bind("ToplevelResponse", self._on_toplevel_response, True)
        workbench.bind("NotebookTabChanged", self._on_editor_changed, True)
        for sequence in ("<ButtonRelease-1>", "<KeyRelease>", "<FocusIn>"):
            workbench.bind_class(
                "CodeViewText", sequence, self._on_editor_selection_event, True
            )
            workbench.bind_class(
                "ShellText", sequence, self._on_shell_selection_event, True
            )
        self._update_action_button()
        self._set_tutor(
            "Run your Python program with Thonny's normal Run button. "
            "If Python raises an error, a short explanation will appear here automatically."
        )
        self.status.set("Preparing local AI…")

    def _editor(self):
        return get_workbench().get_editor_notebook().get_current_editor()

    def _on_editor_selection_event(self, event) -> None:
        self.after_idle(self._remember_selection, "selected_code", event.widget)

    def _on_shell_selection_event(self, event) -> None:
        self.after_idle(self._remember_selection, "selected_output", event.widget)

    def _remember_selection(self, origin: str, widget) -> None:
        if self._read_selection(widget):
            self._selection_origin = origin
        elif self._selection_origin == origin:
            self._selection_origin = None
        self._update_action_button()

    @staticmethod
    def _read_selection(widget) -> str:
        try:
            if widget is not None and widget.has_selection():
                return str(widget.get("sel.first", "sel.last")).strip()
        except (AttributeError, tk.TclError):
            pass
        return ""

    def _active_selection(self):
        selection_origin = getattr(self, "_selection_origin", None)
        if selection_origin == "selected_code":
            editor = self._editor()
            if editor is not None:
                widget = editor.get_code_view().text
                selected = self._read_selection(widget)
                if selected:
                    return "selected_code", widget, selected
        elif selection_origin == "selected_output":
            shell = get_shell(create=False)
            if shell is not None:
                widget = shell.text
                selected = self._read_selection(widget)
                if selected:
                    return "selected_output", widget, selected
        return None

    def _update_action_button(self) -> None:
        selection = self._active_selection()
        mode = (
            selection[0]
            if selection is not None
            else "hint"
            if self._diagnostic
            else "program"
        )
        text, background, active_background = ACTION_BUTTON_MODES[mode]
        self.action_button.configure(
            text=text,
            background=background,
            activebackground=active_background,
            activeforeground="white",
        )

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
        self._selection_origin = None
        self._update_action_button()
        self.status.set("Watching this run…")

    def _on_program_output(self, event) -> None:
        if self._run_in_progress:
            self._last_output = (self._last_output + str(event.data))[-6000:]

    def _on_toplevel_response(self, response) -> None:
        command_name = str(response.get("command_name", "")).lower()
        user_exception = response.get("user_exception")
        if (
            not self._run_in_progress
            and command_name not in RUN_COMMANDS
            and not user_exception
        ):
            return
        self._run_in_progress = False
        editor = self._editor()
        if editor is not None:
            self._last_source = editor.get_content()

        if not user_exception:
            self._successful_runs += 1
            self._diagnostic = None
            self._update_action_button()
            self.status.set("Local AI ready")
            return

        raw_exception = "".join(
            str(item[0]) for item in user_exception.get("items", ())
        )
        type_name = str(user_exception.get("type_name", "PythonError"))
        message = str(user_exception.get("message", "Python reported an error"))
        if not raw_exception:
            raw_exception = f"{type_name}: {message}"
        parser = PythonAdapter()
        diagnostic = parser.parse_diagnostics(raw_exception, self._last_source)
        if diagnostic is None:
            diagnostic = Diagnostic(
                language="python",
                execution_phase="syntax"
                if type_name in {"SyntaxError", "IndentationError"}
                else "runtime",
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
        self._test_results = (
            self._last_output if looks_like_test_results(self._last_output) else ""
        )
        self._diagnostic_runs += 1
        self._highlight_line(diagnostic.line)
        self._update_action_button()
        self.status.set("Explaining the error…")
        self.request_tutor("run")

    @staticmethod
    def _exception_line(raw_exception: str) -> int | None:
        matches = re.findall(r"line (\d+)", raw_exception)
        return int(matches[-1]) if matches else None

    def _on_editor_changed(self, event=None) -> None:
        self._selection_origin = None
        self._update_action_button()

    def _request_contextual_help(self) -> None:
        selection = self._active_selection()
        if selection is not None:
            self.show_tutor("selection", self._tutor_context(selection))
            return
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
        if (
            not context.source_excerpt
            and not context.actual_output
            and not context.diagnostic
        ):
            self._set_tutor("Open a Python file or write a few lines first.")
            return
        response = deterministic_response(context, action)
        if action == "hint":
            self._hint_count += 1
        self._set_tutor(render_response(response, action))

    def _tutor_context(self, selection=None) -> TutorContext:
        editor = self._editor()
        source = editor.get_content() if editor is not None else self._last_source
        progress_parts = []
        if self._successful_runs:
            progress_parts.append(
                f"completed {self._successful_runs} successful run(s)"
            )
        if self._diagnostic_runs:
            progress_parts.append(
                f"investigated {self._diagnostic_runs} run(s) with diagnostics"
            )
        context = context_from_run(
            language="python",
            source=source,
            diagnostic=self._diagnostic,
            actual_output=self._last_output,
            test_results=self._test_results,
            session_progress=" and ".join(progress_parts),
        )
        if selection is None:
            return context

        origin, widget, selected = selection
        if origin == "selected_output":
            return replace(
                context,
                actual_output=bounded_text(selected, 700),
                test_results=(
                    bounded_text(selected, 700)
                    if looks_like_test_results(selected)
                    else ""
                ),
                focus="selected_output",
            )

        try:
            start_line = int(str(widget.index("sel.first")).split(".")[0])
            end_line = int(str(widget.index("sel.last")).split(".")[0])
            nearby = str(
                widget.get(
                    f"{max(1, start_line - 2)}.0",
                    f"{end_line + 2}.end",
                )
            ).strip()
        except (AttributeError, ValueError, tk.TclError):
            nearby = selected
        excerpt = f"Selected code:\n{bounded_text(selected, 800)}"
        if nearby and nearby != selected:
            excerpt += f"\n\nNearby code:\n{bounded_text(nearby, 1000)}"
        return replace(
            context,
            source_excerpt=bounded_text(excerpt, 1400),
            focus="selected_code",
        )

    def _set_tutor(self, text: str) -> None:
        self._set_tutor_partial(text)
        self._set_tutor_busy(False)

    def _set_tutor_partial(self, text: str) -> None:
        self.tutor_text.configure(state="normal")
        self.tutor_text.delete("1.0", "end")
        self.tutor_text.insert("1.0", text)
        self.tutor_text.configure(state="disabled")

    def _set_tutor_busy(self, busy: bool) -> None:
        self.action_button.configure(state="disabled" if busy else "normal")
        if not busy:
            self._update_action_button()

    def set_ai_status(self, text: str) -> None:
        self.status.set(text)

    def tutor_length(self) -> TutorLength:
        return "detailed" if self._detailed.get() else "concise"

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
