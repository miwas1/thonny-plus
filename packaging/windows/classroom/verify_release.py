"""Authoritative release gate for the Windows Classroom portable ZIP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from verify_bundle import verify

EXTRA_REQUIRED = (
    "tutor/llama-server.exe",
    "licenses/THIRD_PARTY_NOTICES.md",
    "licenses/THONNY-LICENSE.txt",
    "licenses/LLAMA-CPP-LICENSE.txt",
    "licenses/QWEN-LICENSE.txt",
    "thonny/Lib/site-packages/basedpyright/langserver.py",
    "thonny/Lib/site-packages/ruff/__main__.py",
    "thonny/Scripts/ruff.exe",
)


def verify_release(root: Path, checksums: dict[str, str]) -> list[str]:
    errors = verify(root, checksums)
    errors.extend(
        f"Missing {relative}"
        for relative in EXTRA_REQUIRED
        if not (root / relative).is_file()
    )
    metadata_files = list(
        (root / "thonny" / "Lib" / "site-packages").glob("thonny-*.dist-info/METADATA")
    )
    if len(metadata_files) != 1:
        errors.append("Missing or ambiguous Thonny package metadata")
    required_checksums = (
        "thonny/python.exe",
        "tutor/llama-server.exe",
        "tutor/qwen-coder-0.5b-q8_0.gguf",
    )
    errors.extend(
        f"No pinned checksum for {relative}"
        for relative in required_checksums
        if relative not in checksums
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("checksums", type=Path)
    args = parser.parse_args()
    root = args.bundle.resolve()
    checksums = json.loads(args.checksums.read_text(encoding="utf-8"))
    errors = verify_release(root, checksums)
    if errors:
        print("\n".join(errors))
        return 1
    print("Windows x86-64 Classroom release is complete and checksum-verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
