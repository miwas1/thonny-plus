from __future__ import annotations

import os
import sys
from pathlib import Path

from thonny.plugins.classroom.adapters import (
    GoAdapter,
    JavaScriptAdapter,
    LanguageAdapter,
    PythonAdapter,
)

EXTENSION_LANGUAGES = {".py": "python", ".js": "javascript", ".go": "go"}
SAMPLES = {
    "python": 'print("Hello!")\n',
    "javascript": 'console.log("Hello!");\n',
    "go": 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello!")\n}\n',
}


def application_root() -> Path:
    override = os.environ.get("THONNY_CLASSROOM_ROOT")
    if override:
        return Path(override).resolve()
    return Path(sys.executable).resolve().parent.parent


def bundled_adapters(
    user_data_dir: str | Path, root: Path | None = None
) -> dict[str, LanguageAdapter]:
    root = root or application_root()
    runtimes = root / "runtimes"
    suffix = ".exe" if os.name == "nt" else ""
    # Thonny's Windows launcher is linked against the complete Python
    # distribution beside it. Reuse that distribution for learner programs;
    # copying python.exe alone into runtimes/ would not be runnable.
    python_exe = root / "thonny" / f"python{suffix}"
    if not python_exe.exists():
        python_exe = Path(sys.executable)
    return {
        "python": PythonAdapter(python_exe),
        "javascript": JavaScriptAdapter(runtimes / "node" / f"node{suffix}"),
        "go": GoAdapter(
            runtimes / "go" / "bin" / f"go{suffix}",
            runtimes / "go",
            Path(user_data_dir) / "go-cache",
        ),
    }


def language_for_path(path: str | Path | None, fallback: str = "python") -> str:
    return EXTENSION_LANGUAGES.get(Path(path).suffix.lower(), fallback) if path else fallback
