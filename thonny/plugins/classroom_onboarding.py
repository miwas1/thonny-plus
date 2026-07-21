"""Three-choice opening screen for first-time classroom learners."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from thonny import get_workbench
from thonny.plugins.classroom.runtime import SAMPLES

ONBOARDING_OPTION = "classroom.onboarding_complete"


def _open(event=None) -> None:
    workbench = get_workbench()
    if workbench.get_option(ONBOARDING_OPTION):
        return
    dialog = tk.Toplevel(workbench)
    dialog.title("Choose what to learn")
    dialog.transient(workbench)
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", lambda: choose("python"))
    ttk.Label(dialog, text="What would you like to learn?", font="TkHeadingFont").grid(
        row=0, column=0, columnspan=3, padx=28, pady=(24, 18)
    )

    def choose(language: str) -> None:
        view = workbench.show_view("ClassroomView", False)
        view.language.set(language)
        editor = workbench.get_editor_notebook().get_current_editor()
        if editor is not None and not editor.get_content().strip():
            editor.get_text_widget().insert("1.0", SAMPLES[language])
        workbench.set_option(ONBOARDING_OPTION, True)
        dialog.destroy()

    choices = (
        ("🐍\nLearn Python", "python"),
        ("JS\nLearn JavaScript", "javascript"),
        ("Go\nLearn Go", "go"),
    )
    for column, (label, language) in enumerate(choices):
        ttk.Button(
            dialog, text=label, width=18, command=lambda value=language: choose(value)
        ).grid(row=1, column=column, padx=10, pady=(0, 25), ipady=18)
    ttk.Label(
        dialog,
        text="● Everything stays on this computer. No account or internet needed.",
    ).grid(row=2, column=0, columnspan=3, padx=28, pady=(0, 22))
    dialog.update_idletasks()
    x = workbench.winfo_rootx() + max(
        0, (workbench.winfo_width() - dialog.winfo_width()) // 2
    )
    y = workbench.winfo_rooty() + max(
        0, (workbench.winfo_height() - dialog.winfo_height()) // 3
    )
    dialog.geometry(f"+{x}+{y}")
    dialog.grab_set()


def load_plugin() -> None:
    workbench = get_workbench()
    workbench.set_default(ONBOARDING_OPTION, False)
    workbench.bind("WorkbenchReady", _open, True)
