from __future__ import annotations

import os
import shutil
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
    # Thonny's Windows launcher is linked against the complete Python
    # distribution beside it. Reuse that distribution for learner programs;
    # copying python.exe alone into runtimes/ would not be runnable.
    python_candidates = (root / "thonny" / "python.exe", root / "thonny" / "python")
    python_exe = next((path for path in python_candidates if path.is_file()), Path(sys.executable))
    node_candidates = (runtimes / "node" / "node.exe", runtimes / "node" / "node")
    go_candidates = (runtimes / "go" / "bin" / "go.exe", runtimes / "go" / "bin" / "go")
    node_exe = next((path for path in node_candidates if path.is_file()), node_candidates[0])
    go_exe = next((path for path in go_candidates if path.is_file()), go_candidates[0])
    # Development checkouts may use installed runtimes on macOS/Linux. A
    # packaged Windows classroom build remains locked to its private bundle.
    if os.name != "nt":
        node_exe = Path(shutil.which("node") or node_exe)
        go_exe = Path(shutil.which("go") or go_exe)
    go_root = runtimes / "go"
    if not go_root.is_dir() and go_exe.is_file():
        go_root = go_exe.resolve().parent.parent
    return {
        "python": PythonAdapter(python_exe),
        "javascript": JavaScriptAdapter(node_exe),
        "go": GoAdapter(
            go_exe,
            go_root,
            Path(user_data_dir) / "go-cache",
            timeout=60.0,
        ),
    }


def language_for_path(path: str | Path | None, fallback: str = "python") -> str:
    return EXTENSION_LANGUAGES.get(Path(path).suffix.lower(), fallback) if path else fallback
