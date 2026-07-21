"""Exercise bundled Python and the persistent offline Qwen service."""

from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import BinaryIO

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


def _send_lsp_message(
    process: subprocess.Popen[bytes], message: dict[str, object]
) -> None:
    if process.stdin is None:
        raise RuntimeError("language server stdin is unavailable")
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    process.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    process.stdin.flush()


def _read_lsp_message(stream: BinaryIO) -> dict[str, object]:
    content_length = None
    while True:
        line = stream.readline()
        if not line:
            raise EOFError("language server closed its output")
        if line == b"\r\n":
            break
        name, value = line.decode("ascii").split(":", 1)
        if name.lower() == "content-length":
            content_length = int(value.strip())

    if content_length is None:
        raise ValueError("language server response had no Content-Length header")
    message = json.loads(stream.read(content_length).decode("utf-8"))
    if not isinstance(message, dict):
        raise TypeError("language server response was not an object")
    return message


def _wait_for_lsp_response(
    process: subprocess.Popen[bytes], request_id: int, timeout: float
) -> dict[str, object]:
    if process.stdout is None:
        raise RuntimeError("language server stdout is unavailable")
    result: queue.Queue[object] = queue.Queue(maxsize=1)

    def read_until_response() -> None:
        try:
            while True:
                message = _read_lsp_message(process.stdout)
                if message.get("id") == request_id:
                    result.put(message)
                    return
        except Exception as exc:
            result.put(exc)

    threading.Thread(target=read_until_response, daemon=True).start()
    try:
        response = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise TimeoutError(
            f"language server did not answer request {request_id} within {timeout:g} seconds"
        ) from exc
    if isinstance(response, Exception):
        raise response
    if not isinstance(response, dict):
        raise TypeError("language server reader returned an invalid result")
    return response


def _exercise_basedpyright(python: Path) -> None:
    process = subprocess.Popen(
        [
            str(python),
            "-c",
            "from basedpyright.langserver import main; main()",
            "--stdio",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    failure: Exception | None = None
    try:
        _send_lsp_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"processId": None, "rootUri": None, "capabilities": {}},
            },
        )
        initialized = _wait_for_lsp_response(process, 1, 30.0)
        initialization_result = initialized.get("result")
        if (
            not isinstance(initialization_result, dict)
            or "capabilities" not in initialization_result
        ):
            raise RuntimeError(f"invalid initialize response: {initialized!r}")

        _send_lsp_message(
            process,
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
        )
        _send_lsp_message(
            process,
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None},
        )
        _wait_for_lsp_response(process, 2, 10.0)
        _send_lsp_message(
            process,
            {"jsonrpc": "2.0", "method": "exit", "params": None},
        )
        process.wait(timeout=10.0)
        if process.returncode != 0:
            raise RuntimeError(f"language server exited with code {process.returncode}")
    except Exception as exc:
        failure = exc
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)

        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.stdout is not None:
            process.stdout.close()

    detail = ""
    if process.stderr is not None:
        detail = process.stderr.read().decode("utf-8", errors="replace").strip()
        process.stderr.close()
    if failure is not None:
        raise RuntimeError(
            "Basedpyright language-server startup failed: "
            f"{failure}; exit={process.returncode}; stderr={detail!r}"
        ) from failure


def exercise_language_services(app: Path) -> dict[str, str]:
    python = app / "thonny" / "python.exe"
    _exercise_basedpyright(python)
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
