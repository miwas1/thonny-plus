"""Validate an assembled Windows x86-64 Classroom portable bundle.

This script performs no downloads. Release builders first obtain and checksum
the pinned upstream archives, then run this gate before creating the ZIP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = (
    "thonny/thonny.exe",
    "thonny/python.exe",
    "thonny/python314.dll",
    "thonny/Lib",
    "runtimes/node/node.exe",
    "runtimes/go/bin/go.exe",
    "runtimes/go/bin/gofmt.exe",
    "runtimes/go/src",
    "tutor/llama-server.exe",
    "tutor/qwen-coder-1.5b-q4_k_m.gguf",
    "licenses",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(root: Path, checksums: dict[str, str]) -> list[str]:
    errors = [f"Missing {relative}" for relative in REQUIRED if not (root / relative).exists()]
    for relative, expected in checksums.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"Checksum target is missing: {relative}")
        elif sha256(path).lower() != expected.lower():
            errors.append(f"Checksum mismatch: {relative}")
    if not any((root / "licenses").glob("*")):
        errors.append("licenses/ contains no upstream notices")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument(
        "checksums", type=Path, help="JSON object mapping bundle-relative paths to SHA-256 digests"
    )
    args = parser.parse_args()
    errors = verify(args.bundle.resolve(), json.loads(args.checksums.read_text(encoding="utf-8")))
    if errors:
        print("\n".join(errors))
        return 1
    print("Classroom bundle layout, notices, and pinned checksums verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
