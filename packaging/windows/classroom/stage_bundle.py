"""Reproducibly stage the pinned Windows x86-64 Classroom bundle.

Downloads are cached and checked before extraction. The resulting app directory
is intentionally ignored by Git and must pass verify_release.py before use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[2]
MANIFEST = HERE / "artifacts.json"
CHECKSUM_TARGETS = (
    "thonny/python.exe",
    "tutor/llama-server.exe",
    "tutor/qwen-coder-1.5b-q4_k_m.gguf",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path, expected: str) -> Path:
    if target.is_file() and sha256(target) == expected:
        print(f"Using verified cache: {target.name}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    partial.unlink(missing_ok=True)
    print(f"Downloading {target.name}")
    with urllib.request.urlopen(url) as response, partial.open("wb") as destination:
        shutil.copyfileobj(response, destination, 1024 * 1024)
    actual = sha256(partial)
    if actual != expected:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum mismatch for {target.name}: {actual}")
    partial.replace(target)
    return target


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            target = (destination / member.filename).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
        source.extractall(destination)


def copy_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def install_thonny_metadata(site_packages: Path) -> Path:
    version = (REPOSITORY / "thonny" / "VERSION").read_text(encoding="ascii").strip()
    for previous in site_packages.glob("thonny-*.dist-info"):
        shutil.rmtree(previous)
    dist_info = site_packages / f"thonny-{version}.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.4\n"
        "Name: thonny\n"
        f"Version: {version}\n"
        "Summary: Python IDE for beginners\n",
        encoding="utf-8",
    )
    (dist_info / "WHEEL").write_text(
        "Wheel-Version: 1.0\n"
        "Generator: thonny-classroom-stage\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n",
        encoding="utf-8",
    )
    (dist_info / "top_level.txt").write_text("thonny\n", encoding="utf-8")
    (dist_info / "INSTALLER").write_text("thonny-classroom-stage\n", encoding="utf-8")
    (dist_info / "RECORD").write_text("", encoding="utf-8")
    return dist_info


def prune_removed_components(app: Path) -> None:
    for obsolete in (
        app / "runtimes" / "node",
        app / "runtimes" / "go",
    ):
        if obsolete.exists():
            shutil.rmtree(obsolete)
    for obsolete in (
        app / "licenses" / "NODE-LICENSE.txt",
        app / "licenses" / "GO-LICENSE.txt",
        app / "licenses" / "GO-PATENTS.txt",
        app / "tutor" / "llama-cli.exe",
    ):
        obsolete.unlink(missing_ok=True)


def install_thonny(app: Path) -> None:
    thonny_root = app / "thonny"
    site_packages = thonny_root / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    # The official Windows embeddable distribution disables site-packages by
    # default. Enable only this private install; no global PATH or Python state
    # is changed on the build machine or learner computer.
    for pth in thonny_root.glob("python*._pth"):
        lines = [
            line
            for line in pth.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if "Lib/site-packages" not in lines:
            lines.append("Lib/site-packages")
        lines = ["import site" if line == "#import site" else line for line in lines]
        if "import site" not in lines:
            lines.append("import site")
        pth.write_text("\n".join(lines) + "\n", encoding="utf-8")
    installed_package = site_packages / "thonny"
    if installed_package.exists():
        shutil.rmtree(installed_package)
    shutil.copytree(REPOSITORY / "thonny", installed_package)
    install_thonny_metadata(site_packages)
    for filename in ("VERSION", "LICENSE.txt", "CREDITS.rst", "README.rst"):
        source = REPOSITORY / filename
        if source.is_file():
            shutil.copy2(source, site_packages / "thonny" / filename)
    shutil.copy2(
        REPOSITORY
        / "packaging"
        / "windows"
        / "ThonnyRunner314"
        / "x64"
        / "Release"
        / "thonny.exe",
        thonny_root / "thonny.exe",
    )
    shutil.copy2(
        REPOSITORY / "packaging" / "windows" / "thonny_python.ini", thonny_root
    )
    shutil.copy2(REPOSITORY / "packaging" / "portable_thonny.ini", thonny_root)
    prune_removed_components(app)


def install_dependencies(app: Path) -> None:
    thonny_root = app / "thonny"
    site_packages = thonny_root / "Lib" / "site-packages"
    embedded_python = thonny_root / "python.exe"
    requirements = REPOSITORY / "packaging" / "requirements-regular-bundle.txt"
    # The build entry point intentionally requires Python 3.13, while the
    # learner runtime is the separately pinned embeddable Python distribution.
    # Bootstrap pip as pure Python, then let the embedded interpreter resolve
    # its own compatible wheels and environment markers.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--upgrade",
            "--target",
            str(site_packages),
            "pip",
        ],
        check=True,
    )
    subprocess.run(
        [
            str(embedded_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--upgrade",
            "--force-reinstall",
            "--prefix",
            str(thonny_root),
            "-r",
            str(requirements),
        ],
        check=True,
    )
    subprocess.run(
        [
            str(embedded_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--upgrade",
            "--force-reinstall",
            "--prefix",
            str(thonny_root),
            "minny==0.0.1a2",
        ],
        check=True,
    )


def write_licenses(
    app: Path, extracted: Path, manifest: dict[str, dict[str, str]]
) -> None:
    licenses = app / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPOSITORY / "THIRD_PARTY_NOTICES.md", licenses)
    shutil.copy2(REPOSITORY / "LICENSE.txt", licenses / "THONNY-LICENSE.txt")
    pinned_licenses = {
        "LLAMA-CPP-LICENSE.txt": (
            "https://raw.githubusercontent.com/ggml-org/llama.cpp/"
            f"{manifest['llama_cpp']['commit']}/LICENSE"
        ),
        "QWEN-LICENSE.txt": (
            "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/"
            f"{manifest['qwen']['revision']}/LICENSE?download=true"
        ),
    }
    for name, url in pinned_licenses.items():
        target = licenses / name
        print(f"Downloading {name}")
        with urllib.request.urlopen(url) as response, target.open("wb") as destination:
            shutil.copyfileobj(response, destination)


def stage(app: Path, cache: Path, install_deps: bool, resume: bool = False) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    downloads = {
        name: download(
            item["url"], cache / Path(item["url"].split("?")[0]).name, item["sha256"]
        )
        for name, item in manifest.items()
    }
    if app.exists() and not resume:
        raise RuntimeError(f"Refusing to overwrite existing bundle: {app}")
    extracted = cache / "extracted"
    if extracted.exists():
        shutil.rmtree(extracted)
    for name in ("python", "llama_cpp"):
        safe_extract(downloads[name], extracted / name)

    copy_contents(extracted / "python", app / "thonny")
    copy_contents(extracted / "llama_cpp", app / "tutor")
    shutil.copy2(downloads["qwen"], app / "tutor" / "qwen-coder-1.5b-q4_k_m.gguf")
    install_thonny(app)
    if install_deps:
        install_dependencies(app)
    write_licenses(app, extracted, manifest)

    write_bundle_metadata(app, manifest)


def write_bundle_metadata(app: Path, manifest: dict[str, dict[str, str]]) -> None:
    checksums = {relative: sha256(app / relative) for relative in CHECKSUM_TARGETS}
    (app.parent / "checksums.json").write_text(
        json.dumps(checksums, indent=2) + "\n", encoding="utf-8"
    )
    (app / "COMPONENTS.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, default=REPOSITORY / "app")
    parser.add_argument("--cache", type=Path, default=REPOSITORY / ".classroom-cache")
    parser.add_argument("--skip-dependencies", action="store_true")
    parser.add_argument(
        "--refresh-source",
        action="store_true",
        help="Refresh only Thonny source and launch files in an existing staged bundle",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse an existing partial bundle after a failed run",
    )
    args = parser.parse_args()
    if args.refresh_source:
        app = args.app.resolve()
        if not app.is_dir():
            parser.error(f"Cannot refresh missing staged bundle: {app}")
        install_thonny(app)
        if not args.skip_dependencies:
            install_dependencies(app)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        write_bundle_metadata(app, manifest)
        print(f"Refreshed application source: {app}")
        return 0
    stage(
        args.app.resolve(),
        args.cache.resolve(),
        not args.skip_dependencies,
        args.resume,
    )
    print(f"Staged bundle: {args.app.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
