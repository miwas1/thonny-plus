# Python + local AI validation

The focused source suite covers Python diagnostics and execution, all bounded
tutor strategies, the persistent worker protocol, Windows hidden-process setup,
Python-only artifact manifests, package metadata, release gates, and build entry
points.

The Windows release gate additionally proves:

1. The pinned private Python distribution runs hello-world, standard input, and
   timeout termination scenarios.
2. `llama-server.exe` and the pinned Qwen GGUF pass checksum and layout checks.
3. Two real tutor requests use one worker/model load; cold and warm timings are
   recorded in the smoke report.
4. The complete installer contains Thonny package metadata, language-server
   dependencies, licenses, and no Node.js or Go runtime.

The Windows Server and GitHub Actions entry points require Python 3.13 x64.
Downloaded artifacts and installer output remain Git-ignored.
