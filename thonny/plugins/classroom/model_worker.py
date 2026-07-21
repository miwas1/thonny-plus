"""One-request local Qwen worker used outside the Tk process.

The worker communicates with the UI over stdin/stdout and invokes llama.cpp by
an exact private path. It never opens a socket or contacts an external service.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

FIELDS = ("explanation", "concept", "question", "hint")


def make_prompt(request: dict[str, Any]) -> str:
    diagnostic = request["diagnostic"]
    safe_input = {
        "action": request["action"],
        "lesson_level": request["lesson_level"],
        "previous_hint_count": request["previous_hint_count"],
        "language": diagnostic["language"],
        "execution_phase": diagnostic["execution_phase"],
        "error_type": diagnostic["error_type"],
        "line": diagnostic["line"],
        "column": diagnostic["column"],
        "raw_message": diagnostic["raw_message"],
        "relevant_code": diagnostic["relevant_code"],
    }
    return (
        request["policy"]
        + "\n\nTutor request:\n"
        + json.dumps(safe_input, ensure_ascii=False)
        + "\nReturn one JSON object now. Do not use Markdown fences."
    )


def extract_response(output: str) -> dict[str, str]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(output):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and all(field in value for field in FIELDS):
            return {field: str(value[field]).strip() for field in FIELDS}
    raise ValueError("Local tutor did not return the required structured response")


def run(llama_cli: str, model: str, request: dict[str, Any], timeout: float) -> dict[str, str]:
    command = [
        llama_cli,
        "-m",
        model,
        "-p",
        make_prompt(request),
        "-n",
        "300",
        "--temp",
        "0.2",
        "--no-display-prompt",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=True)
    return extract_response(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llama-cli", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    request = json.loads(sys.stdin.readline())
    response = run(args.llama_cli, args.model, request, args.timeout)
    print(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
