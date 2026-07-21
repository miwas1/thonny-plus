# Thonny Offline Classroom — Development Checkpoint

## Current status

The source-level MVP and source cleanup have been completed in this repository.
The remaining work is Windows x86-64 bundle assembly and end-to-end validation
with the real bundled runtimes and Qwen model.

The source cleanup and formatting changes described below are currently
uncommitted. Preserve the complete working tree when transferring or committing
the work.

## What has been implemented

### Beginner classroom interface

- Python, JavaScript, and Go language selection.
- Three-choice opening screen:
  - Learn Python
  - Learn JavaScript
  - Learn Go
- Hello-world starter program for each language.
- Automatic language selection for `.py`, `.js`, and `.go` files.
- Unified Run and Stop controls.
- Captured standard output and standard error.
- Simple one-line standard input.
- Process timeout support for infinite loops.
- Focused classroom workspace that hides unrelated Thonny panels.
- Visible **Offline and private** indicator and privacy explanation.
- Clear standard-library-only/offline package limitation.
- JavaScript and Go syntax coloring.
- Error-line highlighting.

### Shared execution architecture

Implemented in `thonny/plugins/classroom/adapters.py`:

- `LanguageAdapter`
- `detect_runtime()`
- `run_file()`
- `stop_process()`
- `parse_diagnostics()`
- `extract_relevant_context()`
- `PythonAdapter`
- `JavaScriptAdapter`
- `GoAdapter`
- Unified process results and process-group termination.

Runtime behavior:

- Python uses the private bundled interpreter when present and the current
  interpreter during development.
- JavaScript calls the exact bundled `node.exe` path without modifying PATH.
- Go calls the exact bundled `go.exe` path.
- Go receives private `GOROOT` and per-user `GOCACHE` values.
- Go module/network access is disabled with `GO111MODULE=off`, `GOPROXY=off`,
  and `GOSUMDB=off`.

### Diagnostic normalization

Python, JavaScript, and Go errors are normalized to:

```text
language
execution_phase
error_type
line
column
raw_message
relevant_code
```

Only a bounded window of relevant numbered lines is passed to tutoring code,
instead of the complete editor contents.

### Beginner tutor

- No unrestricted chatbot input.
- Tutor card appears only after an error or an explicit help request.
- Actions include:
  - Explain this
  - Give me one hint
  - Teach the concept
  - Try again
- Deterministic explanations cover common errors immediately.
- Explanations identify what happened, where it happened, one concept, and one
  next action.
- Responses are restricted to roughly 100 words.
- Only one hint is exposed at a time.
- The policy prohibits complete solutions and replacement programs.

### Local Qwen integration

- `TutorWorkerClient` sends line-delimited structured JSON to a separate worker.
- `model_worker.py` invokes `llama-cli` through its exact private path.
- Inference runs outside the Tk/UI process so it cannot freeze the editor.
- The worker receives only the normalized diagnostic, relevant context, lesson
  level, action, and previous hint count.
- Structured output requires:

```json
{
  "explanation": "...",
  "concept": "...",
  "question": "...",
  "hint": "..."
}
```

- Invalid, slow, missing, or oversized model responses fall back to the
  deterministic tutor.
- The worker does not contact an external service or open a network socket.

### Packaging and licensing preparation

- Windows bundle layout is documented in `docs/offline-classroom.md`.
- Third-party licensing responsibilities are documented in
  `THIRD_PARTY_NOTICES.md`.
- `packaging/windows/classroom/verify_bundle.py` validates the basic layout.
- `packaging/windows/classroom/verify_release.py` is the authoritative release
  gate and checks:
  - Required runtime/model files
  - Pinned checksums
  - Thonny notice
  - Node.js notice
  - Go notice
  - llama.cpp notice
  - Qwen notice

## Verification completed

Eleven automated tests pass on Windows:

```text
python -m unittest -v \
  test_classroom.py \
  test_classroom_model.py \
  test_classroom_packaging.py
```

Coverage includes:

- Extension-to-language selection.
- Starter samples.
- Python, JavaScript, and Go diagnostic normalization.
- Bounded relevant-code extraction.
- Offline Go environment variables.
- Tutor request restrictions and response length.
- Infinite-loop timeout and termination.
- Standard-input delivery to a running program.
- Structured llama.cpp response extraction.
- Rejection of incomplete model output.
- Detection of incomplete Windows bundles and missing notices.

All classroom Python files pass `compileall` and the Black formatter check, and
`git diff --check` reports no whitespace errors.

GUI behavior has been source-reviewed but not launched with the bundled app.
Node.js and Go adapter smoke tests remain unavailable because the private bundle
has not been staged.

## Work remaining on Windows

Target only Windows 10/11 x86-64 for this MVP.

### Completed Windows source work

- Consolidated standard-input UI and worker handoff directly into
  `thonny/plugins/classroom/ui.py`.
- Removed the redundant `classroom_input.py`, `classroom_io.py`, and
  `classroom_keyboard.py` loader plugins, eliminating import-order-dependent
  monkey patches.
- Captured Tk input state on the UI thread before starting the process worker.
- Added an automated standard-input delivery test.
- Applied Black and passed the source verification commands on Windows.

### 1. Stage the private Windows bundle

Create this structure outside normal Git history:

```text
app/
  thonny/
    thonny.exe
    python.exe
    python314.dll
    Lib/
  runtimes/
    node/node.exe
    go/bin/go.exe
    go/bin/gofmt.exe
    go/src/
  tutor/
    llama-cli.exe
    llama-server.exe
    qwen-coder-1.5b-q4_k_m.gguf
  licenses/
```

Use official Windows x86-64 artifacts only. Do not install Node.js or Go globally,
change PATH, write registry entries, or put the GGUF in Git.

### 2. Pin and verify artifacts

Create `checksums.json` containing official SHA-256 values for at least:

```text
thonny/python.exe
runtimes/node/node.exe
runtimes/go/bin/go.exe
tutor/llama-cli.exe
tutor/qwen-coder-1.5b-q4_k_m.gguf
```

Copy exact upstream notices into `app/licenses/` using the filenames required by
`verify_release.py`.

Run:

```powershell
python packaging/windows/classroom/verify_release.py app checksums.json
```

Do not produce the release ZIP until this succeeds.

### 3. Re-run source verification before release

```powershell
python -m unittest -v test_classroom.py test_classroom_model.py test_classroom_packaging.py
python -m compileall thonny/plugins/classroom thonny/plugins/classroom_*.py
python -m black --check thonny/plugins/classroom thonny/plugins/classroom_*.py test_classroom*.py
git diff --check
```

Install the development formatter only if needed for source development; it must
not become a learner-facing dependency.

### 4. Perform real learner-flow testing

Launch the bundled application without relying on globally installed runtimes.
Verify:

- The opening screen shows the three large language choices.
- Each choice inserts the correct Hello program.
- `.py`, `.js`, and `.go` files select the correct runtime.
- Python, JavaScript, and Go Hello programs run successfully.
- Standard input and output work for all three languages.
- Stop terminates an infinite loop in all three languages.
- Automatic timeout terminates an infinite loop.
- Syntax and compile/runtime errors highlight the correct line.
- Common errors produce immediate deterministic explanations.
- Each tutor response remains below approximately 100 words.
- Give me one hint reveals only one hint per click.
- Qwen inference does not freeze the editor.
- Qwen receives only normalized/relevant context.
- Removing or breaking the model triggers deterministic fallback.
- The application works with networking disabled.
- No runtime is added to PATH or installed globally.
- npm, pip, Go module downloads, accounts, unrestricted chat, and cloud features
  are not exposed.

Test at least these failures:

- Python undefined name and syntax/indentation error.
- JavaScript `ReferenceError` and `SyntaxError`.
- Go undefined name and compile syntax error.

### 5. Produce and validate the portable ZIP

- Create the Windows x86-64 portable ZIP only after all gates pass.
- Extract it into a clean directory on a clean Windows 10/11 machine or VM.
- Run the entire learner-flow test again from the extracted copy.
- Confirm clean removal requires deleting only the extracted application and its
  documented per-user cache directory.
- Record exact component versions, SHA-256 values, ZIP size, extracted size, and
  test results in release notes.

## Completion criteria

This effort is complete only when:

1. Source cleanup and formatting are complete.
2. All automated tests pass on Windows.
3. The authoritative release verifier passes.
4. The three bundled runtimes are exercised successfully.
5. Stop and timeout behavior are verified for each language.
6. Offline Qwen inference is exercised successfully.
7. The portable ZIP passes testing on a clean Windows 10/11 x86-64 environment.
8. Required licenses and checksums ship with the release.

Until those checks are complete, treat the project as a source-level MVP rather
than a finished Windows release.
