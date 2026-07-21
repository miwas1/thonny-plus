"""Exercise bundled Python and the persistent offline Qwen service."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY))

from thonny.plugins.classroom.adapters import Diagnostic
from thonny.plugins.classroom.runtime import bundled_adapters
from thonny.plugins.classroom.tutor import TutorWorkerClient


def exercise_python(app: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as directory:
        working = Path(directory)
        adapter = bundled_adapters(working / "user-data", app)["python"]
        hello = working / "hello.py"
        hello.write_text('print("Hello!")\n', encoding="utf-8")
        hello_result = adapter.run_file(hello)
        if hello_result.returncode != 0 or hello_result.stdout.strip() != "Hello!":
            raise RuntimeError(f"Python Hello failed: {hello_result}")

        input_program = working / "input.py"
        input_program.write_text("print(input())\n", encoding="utf-8")
        input_result = adapter.run_file(input_program, input_text="student\n")
        if input_result.returncode != 0 or input_result.stdout.strip() != "student":
            raise RuntimeError(f"Python input failed: {input_result}")

        adapter.timeout = 3.0
        loop = working / "loop.py"
        loop.write_text("while True:\n    pass\n", encoding="utf-8")
        timeout_result = adapter.run_file(loop)
        if not timeout_result.timed_out:
            raise RuntimeError("Python timeout did not stop the program")
        return {
            "executable": str(adapter.executable),
            "hello": "passed",
            "input": "passed",
            "timeout": "passed",
        }


def exercise_language_services(app: Path) -> dict[str, str]:
    python = app / "thonny" / "python.exe"
    initialize = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"processId": None, "rootUri": None, "capabilities": {}},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    shutdown = json.dumps(
        {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None},
        separators=(",", ":"),
    ).encode("utf-8")
    exit_notification = json.dumps(
        {"jsonrpc": "2.0", "method": "exit", "params": None}, separators=(",", ":")
    ).encode("utf-8")

    def frame(body: bytes) -> bytes:
        return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body

    basedpyright = subprocess.run(
        [
            str(python),
            "-c",
            "from basedpyright.langserver import main; main()",
            "--stdio",
        ],
        input=frame(initialize) + frame(shutdown) + frame(exit_notification),
        capture_output=True,
        timeout=30.0,
    )
    if (
        basedpyright.returncode != 0
        or b"Content-Length:" not in basedpyright.stdout
        or b'"capabilities"' not in basedpyright.stdout
    ):
        detail = basedpyright.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"Basedpyright language-server startup failed: {detail}")
    ruff = subprocess.run(
        [str(python), "-m", "ruff", "--version"],
        text=True,
        capture_output=True,
        timeout=30.0,
    )
    if ruff.returncode != 0:
        raise RuntimeError(f"Ruff startup failed: {ruff.stderr}")
    return {"basedpyright": "passed", "ruff": ruff.stdout.strip()}


def exercise_model(app: Path) -> dict[str, object]:
    llama_server = app / "tutor" / "llama-server.exe"
    print("Checking bundled llama.cpp server…", flush=True)
    version = subprocess.run(
        [str(llama_server), "--version"],
        text=True,
        capture_output=True,
        timeout=30.0,
        check=True,
    )
    command = [
        str(app / "thonny" / "python.exe"),
        "-m",
        "thonny.plugins.classroom.model_worker",
        "--llama-server",
        str(llama_server),
        "--model",
        str(app / "tutor" / "qwen-coder-1.5b-q4_k_m.gguf"),
        "--timeout",
        "540",
    ]
    diagnostic = Diagnostic(
        language="python",
        execution_phase="runtime",
        error_type="undefined_name",
        line=1,
        column=None,
        raw_message="NameError: name 'total' is not defined",
        relevant_code="1: print(total)",
    )
    client = TutorWorkerClient(command)
    print("Loading Qwen once and running two in-process requests…", flush=True)
    try:
        first_started = time.monotonic()
        first = client.ask(diagnostic, "explain", timeout=600.0)
        first_seconds = time.monotonic() - first_started
        warm_started = time.monotonic()
        second = client.ask(diagnostic, "hint", timeout=180.0)
        warm_seconds = time.monotonic() - warm_started
        if client.start_count != 1:
            raise RuntimeError("Qwen worker restarted between requests")
    finally:
        client.close()
    version_text = (version.stdout or version.stderr).strip()
    return {
        "status": "passed",
        "llama_cpp": version_text.splitlines()[0]
        if version_text
        else "version unavailable",
        "worker_starts": 1,
        "cold_seconds": round(first_seconds, 2),
        "warm_seconds": round(warm_seconds, 2),
        "first_word_count": len(" ".join(first.__dict__.values()).split()),
        "second_word_count": len(" ".join(second.__dict__.values()).split()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--with-model", action="store_true")
    args = parser.parse_args()
    app = args.bundle.resolve()
    report: dict[str, object] = {
        "python": exercise_python(app),
        "language_services": exercise_language_services(app),
    }
    if args.with_model:
        report["model"] = exercise_model(app)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
