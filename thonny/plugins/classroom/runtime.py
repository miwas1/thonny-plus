from __future__ import annotations

import os
import sys
from pathlib import Path

from thonny.plugins.classroom.adapters import LanguageAdapter, PythonAdapter

SAMPLES = {"python": 'print("Hello!")\n'}


def application_root() -> Path:
    override = os.environ.get("THONNY_CLASSROOM_ROOT")
    if override:
        return Path(override).resolve()
    return Path(sys.executable).resolve().parent.parent


def bundled_adapters(
    user_data_dir: str | Path, root: Path | None = None
) -> dict[str, LanguageAdapter]:
    del user_data_dir
    root = root or application_root()
    candidates = (root / "thonny" / "python.exe", root / "thonny" / "python")
    executable = next((path for path in candidates if path.is_file()), Path(sys.executable))
    return {"python": PythonAdapter(executable)}


def language_for_path(path: str | Path | None, fallback: str = "python") -> str:
    del path, fallback
    return "python"
