"""Exercise every private runtime and, optionally, real offline Qwen inference."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY))

from thonny.plugins.classroom.adapters import Diagnostic
from thonny.plugins.classroom.runtime import bundled_adapters
from thonny.plugins.classroom.tutor import TutorWorkerClient

HELLO = {
    "python": 'print("Hello!")\n',
    "javascript": 'console.log("Hello!");\n',
    "go": 'package main\nimport "fmt"\nfunc main() { fmt.Println("Hello!") }\n',
}
INPUT = {
    "python": "print(input())\n",
    "javascript": "process.stdin.once('data', data => console.log(data.toString().trim()));\n",
    "go": (
        'package main\nimport "fmt"\nfunc main() { var value string; fmt.Scanln(&value); '
        "fmt.Println(value) }\n"
    ),
}
LOOPS = {
    "python": "while True:\n    pass\n",
    "javascript": "while (true) {}\n",
    "go": "package main\nfunc main() { for {} }\n",
}
SUFFIXES = {"python": ".py", "javascript": ".js", "go": ".go"}


def exercise_runtimes(app: Path) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory() as directory:
        working = Path(directory)
        adapters = bundled_adapters(working / "user-data", app)
        for language, adapter in adapters.items():
            # A pristine Go build cache may spend over 30 seconds compiling the
            # standard library on slower classroom hardware.
            adapter.timeout = 120.0
            suffix = SUFFIXES[language]
            hello = working / f"hello{suffix}"
            hello.write_text(HELLO[language], encoding="utf-8")
            hello_result = adapter.run_file(hello)
            if hello_result.returncode != 0 or hello_result.stdout.strip() != "Hello!":
                raise RuntimeError(f"{language} Hello failed: {hello_result}")

            input_program = working / f"input{suffix}"
            input_program.write_text(INPUT[language], encoding="utf-8")
            input_result = adapter.run_file(input_program, input_text="student\n")
            if input_result.returncode != 0 or input_result.stdout.strip() != "student":
                raise RuntimeError(f"{language} input failed: {input_result}")

            adapter.timeout = 3.0
            loop = working / f"loop{suffix}"
            loop.write_text(LOOPS[language], encoding="utf-8")
            timeout_result = adapter.run_file(loop)
            if not timeout_result.timed_out:
                raise RuntimeError(f"{language} timeout did not stop the program")
            results[language] = {
                "executable": str(adapter.executable),
                "hello": "passed",
                "input": "passed",
                "timeout": "passed",
            }
    return results


def exercise_model(app: Path) -> dict[str, object]:
    llama_cli = app / "tutor" / "llama-cli.exe"
    print("Checking bundled llama.cpp executable…", flush=True)
    version = subprocess.run(
        [str(llama_cli), "--version"],
        text=True,
        capture_output=True,
        timeout=30.0,
        check=True,
    )
    command = [
        str(app / "thonny" / "python.exe"),
        "-m",
        "thonny.plugins.classroom.model_worker",
        "--llama-cli",
        str(llama_cli),
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
    print(
        "Loading Qwen and running the first offline inference. This may take several minutes on a CPU-only server…",
        flush=True,
    )
    response = TutorWorkerClient(command).ask(diagnostic, "hint", timeout=600.0)
    version_text = (version.stdout or version.stderr).strip()
    return {
        "status": "passed",
        "llama_cpp": version_text.splitlines()[0]
        if version_text
        else "version unavailable",
        "word_count": len(" ".join(response.__dict__.values()).split()),
        "fields": list(response.__dict__),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--with-model", action="store_true")
    args = parser.parse_args()
    app = args.bundle.resolve()
    report: dict[str, object] = {"runtimes": exercise_runtimes(app)}
    if args.with_model:
        report["model"] = exercise_model(app)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
