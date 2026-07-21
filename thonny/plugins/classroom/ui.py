from __future__ import annotations

import os
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from thonny import get_thonny_user_dir, get_workbench
from thonny.codeview import get_syntax_options_for_tag
from thonny.plugins.classroom.adapters import Diagnostic, LanguageAdapter, RunResult
from thonny.plugins.classroom.runtime import (
    SAMPLES,
    bundled_adapters,
    language_for_path,
)
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


class ClassroomView(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.adapters = bundled_adapters(get_thonny_user_dir())
        self.language = tk.StringVar(value="python")
        self.standard_input = tk.StringVar(value="")
        self.status = tk.StringVar(value="Ready")
        self._active: LanguageAdapter | None = None
        self._diagnostic: Diagnostic | None = None
        self._hint_count = 0
        self._last_source = ""
        self._last_output = ""
        self._expected_output = ""
        self._test_results = ""
        self._successful_runs = 0
        self._diagnostic_runs = 0
        self._tutor_request_id = 0
        self._stop_requested = False
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        ttk.Label(toolbar, text="Language:").pack(side="left")
        selector = ttk.Combobox(
            toolbar,
            textvariable=self.language,
            state="readonly",
            width=14,
            values=("python", "javascript", "go"),
        )
        selector.pack(side="left", padx=(5, 12))
        selector.bind("<<ComboboxSelected>>", self._language_changed)
        self.run_button = ttk.Button(toolbar, text="▶ Run", command=self.run)
        self.run_button.pack(side="left", padx=3, ipady=3)
        self.stop_button = ttk.Button(
            toolbar, text="■ Stop", command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=3, ipady=3)
        ttk.Button(
            toolbar,
            text="Help me understand",
            command=lambda: self.request_tutor("help"),
        ).pack(side="left", padx=(8, 3))
        ttk.Label(toolbar, textvariable=self.status).pack(side="left", padx=12)
        ttk.Button(
            toolbar, text="● Offline and private", command=self._show_privacy
        ).pack(side="right")
        ttk.Entry(toolbar, textvariable=self.standard_input, width=18).pack(
            side="right", padx=(4, 10)
        )
        ttk.Label(toolbar, text="Input:").pack(side="right")
        self.output = tk.Text(
            self,
            height=8,
            wrap="word",
            state="disabled",
            **get_syntax_options_for_tag("TEXT"),
        )
        self.output.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 6))
        self.tutor = ttk.LabelFrame(self, text="Coach")
        self.tutor_text = tk.Text(
            self.tutor,
            height=7,
            wrap="word",
            state="disabled",
            **get_syntax_options_for_tag("TEXT"),
        )
        self.tutor_text.grid(
            row=0, column=0, columnspan=3, sticky="nsew", padx=7, pady=7
        )
        self._tutor_buttons: list[ttk.Button] = []
        self.hint_button = ttk.Button(
            self.tutor,
            text="One hint",
            command=lambda: self.request_tutor("hint"),
        )
        self.hint_button.grid(row=1, column=0, padx=4, pady=(0, 7), ipady=2)
        self.quiz_button = ttk.Button(
            self.tutor,
            text="Quiz me",
            command=lambda: self.request_tutor("quiz"),
        )
        self.quiz_button.grid(row=1, column=1, padx=4, pady=(0, 7), ipady=2)
        self.try_again_button = ttk.Button(
            self.tutor,
            text="Try again",
            command=self._try_again,
        )
        self.try_again_button.grid(row=1, column=2, padx=4, pady=(0, 7), ipady=2)
        self._tutor_buttons.extend(
            (self.hint_button, self.quiz_button, self.try_again_button)
        )
        ttk.Label(self.tutor, text="· answered privately on this computer ·").grid(
            row=2, column=0, columnspan=3, pady=(0, 7)
        )
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        get_workbench().bind("NotebookTabChanged", self._sync_language, True)
        get_workbench().bind("<F5>", self._run_shortcut, True)
        get_workbench().bind("<Control-r>", self._run_shortcut, True)
        get_workbench().bind("<Escape>", self._stop_shortcut, True)
        self._set_output("▸ Your program's output will appear here.\n")

    def _editor(self):
        return get_workbench().get_editor_notebook().get_current_editor()

    def _sync_language(self, event=None) -> None:
        editor = self._editor()
        if editor and editor.get_target_path():
            self.language.set(
                language_for_path(editor.get_target_path(), self.language.get())
            )

    def _language_changed(self, event=None) -> None:
        editor = self._editor()
        if editor and not editor.get_content().strip():
            editor.get_text_widget().insert("1.0", SAMPLES[self.language.get()])

    def run(self) -> None:
        editor = self._editor()
        if editor is None:
            messagebox.showinfo("Classroom", "Open an editor before running a program.")
            return
        language = language_for_path(editor.get_target_path(), self.language.get())
        self.language.set(language)
        adapter = self.adapters[language]
        if not adapter.detect_runtime():
            messagebox.showerror(
                "Runtime unavailable",
                f"The bundled {language} runtime is missing.\n"
                "Runtime settings are intentionally hidden in classroom mode.",
            )
            return
        source = editor.get_content()
        self._last_source = source
        path = editor.get_target_path()
        if path and editor.save_file_enabled():
            path = editor.save_file()
            if not path:
                return
        if not path:
            suffix = {"python": ".py", "javascript": ".js", "go": ".go"}[language]
            temp_dir = Path(get_thonny_user_dir()) / "classroom-programs"
            temp_dir.mkdir(parents=True, exist_ok=True)
            handle, path = tempfile.mkstemp(suffix=suffix, dir=temp_dir, text=True)
            os.close(handle)
            Path(path).write_text(source, encoding="utf-8")
        self._active, self._diagnostic, self._hint_count = adapter, None, 0
        self._test_results = ""
        self._stop_requested = False
        self._clear_error_highlight()
        self.tutor.grid_remove()
        self._set_output("")
        self.status.set("Running…")
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        entered = self.standard_input.get()
        input_text = entered + ("\n" if entered and not entered.endswith("\n") else "")
        threading.Thread(
            target=self._run_worker,
            args=(adapter, Path(path), source, input_text),
            daemon=True,
        ).start()

    def _run_worker(
        self, adapter: LanguageAdapter, path: Path, source: str, input_text: str
    ) -> None:
        try:
            result = adapter.run_file(path, input_text=input_text)
            diagnostic = adapter.parse_diagnostics(result.stderr, source)
            get_workbench().after(0, self._finish_run, result, diagnostic)
        except Exception as exc:
            get_workbench().after(0, self._run_failed, str(exc))

    def _finish_run(self, result: RunResult, diagnostic: Diagnostic | None) -> None:
        self._active, self._diagnostic = None, diagnostic
        self._last_output = result.stdout + result.stderr
        if result.timed_out:
            self._last_output += (
                "\nYour program ran too long and was stopped. "
                "Look for a loop that never ends.\n"
            )
        self._set_output(self._last_output or "Program finished with no output.\n")
        self.status.set(
            "Timed out"
            if result.timed_out
            else "Stopped"
            if self._stop_requested
            else "Finished"
        )
        self.run_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        if looks_like_test_results(self._last_output):
            self._test_results = self._last_output
        if diagnostic:
            self._diagnostic_runs += 1
            self._highlight_line(diagnostic.line)
            self.request_tutor("run")
        elif result.timed_out or self._test_results:
            self.request_tutor("run")
        elif result.returncode == 0 and not result.timed_out:
            self._successful_runs += 1
            self.tutor.grid_remove()

    def _run_failed(self, message: str) -> None:
        self._active = None
        self.status.set("Could not run")
        self._set_output(message)
        self.run_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def stop(self) -> None:
        if self._active:
            self._stop_requested = True
            self._active.stop_process()
            self.status.set("Stopping…")

    def _run_shortcut(self, event=None):
        if str(self.run_button.cget("state")) != "disabled":
            self.run()
        return "break"

    def _stop_shortcut(self, event=None):
        self.stop()
        return "break"

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
        if context is None:
            return
        if not context.source_excerpt and not context.diagnostic:
            self._set_tutor(
                "Open or run a program first. I use your existing code to guide you without writing a solution."
            )
            return
        if action in {"explain", "problem_area"} and not context.diagnostic:
            self._set_tutor(
                "Run the program again so I can connect the explanation to a specific error."
            )
            return
        response = deterministic_response(context, action)
        if action == "hint":
            self._hint_count += 1
        self._set_tutor(render_response(response, action))

    def _try_again(self) -> None:
        self.tutor.grid_remove()
        editor = self._editor()
        if editor is not None:
            editor.get_text_widget().focus_set()

    def _tutor_context(self) -> TutorContext:
        editor = self._editor()
        source = editor.get_content() if editor is not None else self._last_source
        language = self.language.get()
        progress_parts = []
        if self._successful_runs:
            progress_parts.append(
                f"completed {self._successful_runs} successful run(s)"
            )
        if self._diagnostic_runs:
            progress_parts.append(
                f"investigated {self._diagnostic_runs} run(s) with diagnostics"
            )
        return context_from_run(
            language=language,
            source=source,
            diagnostic=self._diagnostic,
            actual_output=self._last_output,
            expected_output=self._expected_output,
            test_results=self._test_results,
            session_progress=" and ".join(progress_parts),
            timed_out=self.status.get() == "Timed out",
        )

    def _set_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _set_tutor(self, text: str) -> None:
        self.tutor.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 7))
        self.tutor_text.configure(state="normal")
        self.tutor_text.delete("1.0", "end")
        self.tutor_text.insert("1.0", text)
        self.tutor_text.configure(state="disabled")
        self._update_coach_controls()
        self._set_tutor_busy(False)

    def _update_coach_controls(self) -> None:
        if self._diagnostic or self.status.get() == "Timed out":
            self.hint_button.grid()
        else:
            self.hint_button.grid_remove()
        if self._successful_runs and not self._diagnostic:
            self.quiz_button.grid()
        else:
            self.quiz_button.grid_remove()

    def _set_tutor_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in self._tutor_buttons:
            button.configure(state=state)

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
            "Your code and questions stay on this computer.\n"
            "No account or internet connection is required.\n\n"
            "This classroom edition supports standard libraries only. External package installation is not enabled in offline mode.",
        )


def load_classroom_ui() -> None:
    get_workbench().add_view(
        ClassroomView,
        "Classroom",
        "e",
        visible_by_default=True,
        default_position_key="000",
    )
