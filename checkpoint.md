# Current implementation checkpoint

The product is Python-only and intentionally reuses Thonny's native editor,
Shell, Run/Stop commands, debugger, input handling, package tools, and language
services. JavaScript and Go adapters, syntax support, onboarding choices,
runtimes, licenses, smoke cases, and bundle requirements have been removed.

The right-side **AI Assistant** listens to `CommandAccepted`, `ProgramOutput`,
and `ToplevelResponse`. Python exceptions are normalized, the relevant line is
highlighted, and an explanation is requested automatically. The assistant has
no language selector, duplicate runner, duplicate output console, unrestricted
chat, code completion, code generation, or automatic fix action.

The bundled Qwen model is served by one hidden `llama-server.exe` process owned
by one persistent Python worker. It is prewarmed after `WorkbenchReady`, binds
only to `127.0.0.1`, uses constrained JSON output, and is reused for every tutor
request. An error encountered during prewarming receives deterministic guidance
immediately; deterministic guidance also remains available if startup or
inference fails.

The Windows build requires Python 3.13 x64, downloads pinned Python, llama.cpp,
and Qwen artifacts into Git-ignored directories, installs normal Thonny bundle
dependencies plus basedpyright and Ruff, verifies package metadata and notices,
smoke-tests Python, then sends two real requests through one model load before
building the installer.
