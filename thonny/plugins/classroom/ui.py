from __future__ import annotations

import os
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from thonny import get_thonny_user_dir, get_workbench
from thonny.plugins.classroom.adapters import Diagnostic, LanguageAdapter, RunResult
from thonny.plugins.classroom.runtime import SAMPLES, bundled_adapters, language_for_path
from thonny.plugins.classroom.tutor import TutorAction, deterministic_response, render_response


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
        ttk.Button(toolbar, text="▶ Run", command=self.run).pack(side="left", padx=3)
        ttk.Button(toolbar, text="■ Stop", command=self.stop).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Explain", command=lambda: self.show_tutor("explain")).pack(
            side="left", padx=3
        )
        ttk.Label(toolbar, textvariable=self.status).pack(side="left", padx=12)
        ttk.Button(toolbar, text="● Offline and private", command=self._show_privacy).pack(
            side="right"
        )
        ttk.Entry(toolbar, textvariable=self.standard_input, width=18).pack(
            side="right", padx=(4, 10)
        )
        ttk.Label(toolbar, text="Input:").pack(side="right")
        self.output = tk.Text(self, height=8, wrap="word", state="disabled")
        self.output.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 6))
        self.tutor = ttk.LabelFrame(self, text="Tutor")
        self.tutor_text = tk.Text(self.tutor, height=7, wrap="word", state="disabled")
        self.tutor_text.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=7, pady=7)
        actions = (
            ("Explain this", "explain"),
            ("Give me one hint", "hint"),
            ("Teach the concept", "concept"),
            ("Try again", "question"),
        )
        for column, (label, action) in enumerate(actions):
            ttk.Button(
                self.tutor, text=label, command=lambda value=action: self.show_tutor(value)
            ).grid(row=1, column=column, padx=4, pady=(0, 7))
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        get_workbench().bind("NotebookTabChanged", self._sync_language, True)

    def _editor(self):
        return get_workbench().get_editor_notebook().get_current_editor()

    def _sync_language(self, event=None) -> None:
        editor = self._editor()
        if editor and editor.get_target_path():
            self.language.set(language_for_path(editor.get_target_path(), self.language.get()))

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
        self.tutor.grid_remove()
        self._set_output("")
        self.status.set("Running…")
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
        self._set_output(result.stdout + result.stderr or "Program finished with no output.\n")
        self.status.set("Stopped by timeout" if result.timed_out else "Finished")
        if diagnostic:
            self.show_tutor("explain")
            self._highlight_line(diagnostic.line)

    def _run_failed(self, message: str) -> None:
        self._active = None
        self.status.set("Could not run")
        self._set_output(message)

    def stop(self) -> None:
        if self._active:
            self._active.stop_process()
            self.status.set("Stopping…")

    def show_tutor(self, action: TutorAction) -> None:
        if not self._diagnostic:
            self._set_tutor(
                "Run the program first. If it reports an error, I can explain it without writing the solution for you."
            )
            return
        response = deterministic_response(self._diagnostic, action)
        if action == "hint":
            self._hint_count += 1
        self._set_tutor(render_response(response, action))

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

    def _highlight_line(self, line: int | None) -> None:
        editor = self._editor()
        if editor is None or line is None:
            return
        text = editor.get_text_widget()
        text.tag_configure("classroom_error", background="#ffd7d7")
        text.tag_remove("classroom_error", "1.0", "end")
        text.tag_add("classroom_error", f"{line}.0", f"{line}.end")
        text.see(f"{line}.0")

    def _show_privacy(self) -> None:
        messagebox.showinfo(
            "Offline and private",
            "Your code and questions stay on this computer.\n"
            "No account or internet connection is required.\n\n"
            "This classroom edition supports standard libraries only. External package installation is not enabled in offline mode.",
        )


def load_classroom_ui() -> None:
    get_workbench().add_view(
        ClassroomView, "Classroom", "s", visible_by_default=True, default_position_key="000"
    )
