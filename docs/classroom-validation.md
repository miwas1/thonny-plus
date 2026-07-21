# Classroom MVP validation

Validated on 2026-07-21 from a Linux development checkout.

## Completed locally

- `python -m unittest -v test_classroom.py test_classroom_model.py test_classroom_packaging.py`: 22/22 passed.
- Ruff format check: passed for the classroom plugin, packaging scripts, and focused tests.
- Ruff lint: no issues in the classroom plugin, packaging scripts, or focused tests.
- Python compile check: passed for the classroom plugin and Windows staging scripts.
- Runtime smoke test: Python, Node.js, and Go each passed hello-world, standard-input, and forced-timeout scenarios.
- Headless Tk launch: Thonny loaded the plugin and created `ClassroomView`. The source checkout also reported unrelated missing `minny` and package-metadata errors; the Windows staging job installs `minny` and the bundle dependencies before launch.
- Model-independent tutor coverage: all 13 scoped tutor strategies produced non-generative responses below 100 words, and contextual routing tests confirm they are not exposed as an activity menu.

## Deliberately deferred to the Windows release job

The Qwen GGUF was not downloaded locally and is ignored by Git. The manual
`release-windows-classroom.yml` workflow is the authoritative environment for
the remaining checks:

1. Download every pinned runtime and Qwen artifact and verify its SHA-256.
2. Install dependencies into the private embeddable Python `site-packages`.
3. Verify the complete private Windows x86-64 bundle and upstream notices.
4. Run Python, Node.js, and Go from their bundled `.exe` paths.
5. Run a real Qwen request through bundled `llama-cli.exe` and enforce the JSON/100-word contract.
6. Build the Inno Setup installer and publish its checksum and release metadata.

An installer should not be published unless all six workflow checks pass.

The same six gates are available for a Windows Server build through
`build-windows-classroom.ps1`. Both PowerShell build scripts pass the Windows
PowerShell parser; downloading and installer creation remain intentionally
deferred until that entry point runs on the build server.

The Windows Server and GitHub Actions build entry points use Python 3.13 x64.
After staging the separately pinned learner runtime, the build Python bootstraps
pip into that private runtime so dependency wheels are resolved by the bundled
interpreter rather than by the build interpreter.
