from __future__ import annotations

import re
from pathlib import Path

from thonny import get_workbench
from thonny.codeview import get_syntax_options_for_tag

KEYWORDS = {
    "javascript": "break case catch class const else for function if let new return switch throw try var while",
    "go": "break case chan const continue default defer else fallthrough for func go goto if import interface map package range return select struct switch type var",
}


def install_cross_language_coloring() -> None:
    get_workbench().bind("EditorTextCreated", _attach, True)


def _attach(event) -> None:
    text = event.text_widget
    text.bind("<<TextChange>>", lambda ignored=None: _color(text), True)
    text.bind("<<UpdateAppearance>>", lambda ignored=None: _color(text), True)
    _color(text)


def _color(text) -> None:
    editor = getattr(text, "master", None)
    while editor is not None and not hasattr(editor, "get_target_path"):
        editor = getattr(editor, "master", None)
    path = editor.get_target_path() if editor is not None else None
    language = {".js": "javascript", ".go": "go"}.get(Path(path).suffix.lower()) if path else None
    if language is None:
        return
    content = text.get("1.0", "end-1c")
    patterns = {
        "classroom_keyword": r"\b(?:" + "|".join(KEYWORDS[language].split()) + r")\b",
        "classroom_string": r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
        "classroom_comment": r"//[^\n]*|/\*[\s\S]*?\*/",
    }
    theme_tags = {
        "classroom_keyword": "keyword",
        "classroom_string": "string",
        "classroom_comment": "comment",
    }
    for tag, pattern in patterns.items():
        text.tag_remove(tag, "1.0", "end")
        text.tag_configure(tag, **get_syntax_options_for_tag(theme_tags[tag]))
        for match in re.finditer(pattern, content):
            text.tag_add(tag, f"1.0+{match.start()}c", f"1.0+{match.end()}c")
