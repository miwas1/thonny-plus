from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class Diagnostic:
    language: str
    execution_phase: str
    error_type: str
    line: int | None
    column: int | None
    raw_message: str
    relevant_code: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RunResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class LanguageAdapter(ABC):
    language: str
    extensions: tuple[str, ...]

    def __init__(self, executable: str | Path, timeout: float = 10.0) -> None:
        self.executable = Path(executable)
        self.timeout = timeout
        self._process: subprocess.Popen[str] | None = None

    def detect_runtime(self) -> bool:
        return self.executable.is_file()

    @abstractmethod
    def build_command(self, path: Path) -> Sequence[str]: ...

    def build_environment(self, path: Path) -> Mapping[str, str]:
        return {}

    def run_file(
        self,
        path: str | Path,
        input_text: str = "",
        on_started: Callable[[subprocess.Popen[str]], None] | None = None,
    ) -> RunResult:
        source = Path(path).resolve()
        command = tuple(map(str, self.build_command(source)))
        env = os.environ.copy()
        env.update(self.build_environment(source))
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        start_new_session = os.name != "nt"
        self._process = subprocess.Popen(
            command,
            cwd=source.parent,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            start_new_session=start_new_session,
        )
        if on_started:
            on_started(self._process)
        timed_out = False
        try:
            stdout, stderr = self._process.communicate(input_text, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self.stop_process()
            stdout, stderr = self._process.communicate()
            stderr += f"\nProgram stopped after {self.timeout:g} seconds."
        returncode = self._process.returncode or 0
        self._process = None
        return RunResult(command, returncode, stdout, stderr, timed_out)

    def stop_process(self) -> None:
        process = self._process
        if process is None or process.poll() is not None:
            return
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            process.kill()

    @abstractmethod
    def parse_diagnostics(self, output: str, source: str) -> Diagnostic | None: ...

    @staticmethod
    def extract_relevant_context(source: str, line: int | None, radius: int = 4) -> str:
        lines = source.splitlines()
        if not lines:
            return ""
        center = max(1, min(line or 1, len(lines)))
        first, last = max(1, center - radius), min(len(lines), center + radius)
        return "\n".join(f"{number:>4} | {lines[number - 1]}" for number in range(first, last + 1))

    def _diagnostic(
        self, phase: str, error_type: str, line: int | None, column: int | None,
        message: str, source: str,
    ) -> Diagnostic:
        return Diagnostic(self.language, phase, error_type, line, column, message.strip(),
                          self.extract_relevant_context(source, line))


class PythonAdapter(LanguageAdapter):
    language = "python"
    extensions = (".py",)

    def __init__(self, executable: str | Path = sys.executable, timeout: float = 10.0) -> None:
        super().__init__(executable, timeout)

    def build_command(self, path: Path) -> Sequence[str]:
        return (str(self.executable), "-I", str(path))

    def parse_diagnostics(self, output: str, source: str) -> Diagnostic | None:
        matches = list(re.finditer(r'File "[^"]+", line (\d+)(?:.*\n\s*(.*?)\n)?', output))
        line = int(matches[-1].group(1)) if matches else None
        final = next((item for item in reversed(output.splitlines()) if item.strip()), "")
        error_match = re.match(r"([\w.]+(?:Error|Exception)):\s*(.*)", final)
        if not error_match:
            return None
        error = error_match.group(1)
        phase = "syntax" if error in {"SyntaxError", "IndentationError", "TabError"} else "runtime"
        column = None
        caret = next((item for item in output.splitlines() if "^" in item), None)
        if caret:
            column = caret.index("^") + 1
        return self._diagnostic(phase, normalize_error_type(error, final), line, column, final, source)


class JavaScriptAdapter(LanguageAdapter):
    language = "javascript"
    extensions = (".js",)

    def build_command(self, path: Path) -> Sequence[str]:
        return (str(self.executable), str(path))

    def parse_diagnostics(self, output: str, source: str) -> Diagnostic | None:
        location = re.search(r"(?:file://)?[^\s:]+\.js:(\d+)(?::(\d+))?", output)
        error = re.search(r"((?:Syntax|Reference|Type|Range)Error):\s*([^\n]+)", output)
        if not error:
            return None
        line = int(location.group(1)) if location else None
        column = int(location.group(2)) if location and location.group(2) else None
        phase = "syntax" if error.group(1) == "SyntaxError" else "runtime"
        message = f"{error.group(1)}: {error.group(2)}"
        return self._diagnostic(phase, normalize_error_type(error.group(1), message), line, column, message, source)


class GoAdapter(LanguageAdapter):
    language = "go"
    extensions = (".go",)

    def __init__(self, executable: str | Path, goroot: str | Path, cache_dir: str | Path,
                 timeout: float = 10.0) -> None:
        super().__init__(executable, timeout)
        self.goroot = Path(goroot)
        self.cache_dir = Path(cache_dir)

    def build_command(self, path: Path) -> Sequence[str]:
        return (str(self.executable), "run", str(path))

    def build_environment(self, path: Path) -> Mapping[str, str]:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return {"GOROOT": str(self.goroot), "GOCACHE": str(self.cache_dir),
                "GO111MODULE": "off", "GOPROXY": "off", "GOSUMDB": "off"}

    def parse_diagnostics(self, output: str, source: str) -> Diagnostic | None:
        match = re.search(r"(?:^|\n)(?:[^\n:]+\.go):(\d+):(\d+):\s*(.+)", output)
        if not match:
            return None
        line, column, message = int(match.group(1)), int(match.group(2)), match.group(3)
        return self._diagnostic("compile", normalize_error_type("compile error", message),
                                line, column, message, source)


def normalize_error_type(error: str, message: str) -> str:
    lower = message.lower()
    if "undefined" in lower or "not defined" in lower or "is not defined" in lower:
        return "undefined_name"
    if "syntax" in error.lower() or "expected" in lower or "unexpected" in lower:
        return "syntax_error"
    if "indent" in error.lower():
        return "indentation_error"
    if "type" in error.lower() or "cannot use" in lower:
        return "type_error"
    if "zero" in lower:
        return "division_by_zero"
    return re.sub(r"(?<!^)(?=[A-Z])", "_", error).lower().replace(" ", "_")
