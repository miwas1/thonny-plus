# Thonny Offline Classroom MVP

This repository is an MIT-licensed Thonny foundation with an added
`thonny.plugins.classroom` plugin. Thonny's original copyright and license are
preserved in `LICENSE.txt` and `CREDITS.rst`. The classroom plugin, unified
language adapters, diagnostic normalizer, restricted tutor, and Windows bundle
layout are additions made for this project.

## Learner experience

The Classroom view provides a Python / JavaScript / Go selector, Run and Stop,
captured output, an **Offline and private** badge, and a Coach rail. The Coach is
hidden until an error occurs or the learner chooses a scoped learning activity.
It has no unrestricted chat input. In addition to error explanations and one
hint at a time, it can explain a concept, ask guiding questions, identify a
small likely problem area, trace execution, compare output, check common
misconceptions, suggest one next topic, quiz existing code, guide a rubber-duck
explanation, explain teacher test results, and acknowledge specific session
progress. Every mode has a deterministic offline fallback.

These modes are internal teaching strategies, not a menu the learner must
understand. A contextual router chooses among them from the latest run,
diagnostic, test output, hint history, and session progress. The visible UI has
one **Help me understand** entry point, followed only by **One hint**, a
contextual **Quiz me**, and **Try again** when those actions are relevant.

Files select their language automatically (`.py`, `.js`, `.go`). For an empty,
untitled editor, choosing a language inserts its Hello sample. JavaScript and Go
support deliberately covers highlighting, run/stop, input/output capture,
error-line highlighting, and explanations—not debugging or package management.

## Private Windows x86-64 bundle

Build one Windows 10/11 x86-64 portable directory with this layout:

```
app/thonny/
app/thonny/python.exe
app/thonny/python314.dll
app/thonny/Lib/
app/runtimes/node/node.exe
app/runtimes/go/bin/go.exe
app/runtimes/go/bin/gofmt.exe
app/runtimes/go/src/
app/tutor/llama-cli.exe
app/tutor/qwen-coder-1.5b-q4_k_m.gguf
app/licenses/
```

Set `THONNY_CLASSROOM_ROOT` to `app` when needed. Runtime discovery never changes
PATH, the registry, or a global installation. The Run button reuses the complete
private Python distribution that launches Thonny. Go uses its private GOROOT, a
per-user GOCACHE, `GO111MODULE=off`, `GOPROXY=off`, and `GOSUMDB=off`. Node is
called by its exact bundled path. Python uses the bundled interpreter when
present and Thonny's interpreter in development builds.

The installed application makes no network requests. Do not commit downloaded
binaries or the model. The manual Windows release workflow downloads the pinned
archives and Qwen GGUF only on its GitHub Actions runner, verifies SHA-256
digests, stages the private bundle, runs real runtime/model smoke tests, and then
builds an Inno Setup installer. Exact upstream notices are copied into
`app/licenses/` before the release gate runs.

## Local tutor worker

Qwen2.5-Coder-1.5B-Instruct Q4_K_M is the only runtime AI. Run llama.cpp in a
separate local process through `TutorWorkerClient`. Error requests contain the
normalized diagnostic and its relevant 5–9 numbered lines. On-demand requests
contain a bounded excerpt of at most 80 numbered lines plus only the relevant
actual/expected output, teacher test text, and session progress. Learner data is
explicitly treated as untrusted prompt data. The system policy forbids code
generation, solutions, replacement programs, instruction-following from code,
and unrestricted conversation. Responses are structured JSON; empty fields and
responses over 100 words are rejected.

External npm, pip, and Go package installation is not exposed. The classroom
edition supports standard libraries only and works without internet or accounts.
