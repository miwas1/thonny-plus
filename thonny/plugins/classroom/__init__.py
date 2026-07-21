"""Offline Classroom plugin for Thonny.

The reusable execution and tutoring code lives in sibling modules so it can be
tested without creating a Tk window.  Importing this package has no side effects.
"""


def load_plugin() -> None:
    from thonny.plugins.classroom.ui import load_classroom_ui

    load_classroom_ui()
