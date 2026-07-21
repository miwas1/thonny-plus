# Thonny Offline Classroom MVP

This repository is an MIT-licensed Thonny foundation with an added
`thonny.plugins.classroom` plugin. Thonny's original copyright and license are
preserved in `LICENSE.txt` and `CREDITS.rst`. The classroom plugin, unified
language adapters, diagnostic normalizer, restricted tutor, and Windows bundle
layout are additions made for this project.

## Learner experience

The Classroom view provides a Python / JavaScript / Go selector, Run and Stop,
captured output, an **Offline and private** badge, and a tutor card. The card is
hidden until an error occurs or **Explain** is requested. It has no unrestricted
chat input and offers only Explain this, Give me one hint, Teach the concept, and
Try again. Common errors are explained immediately with deterministic rules.

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
app/tutor/llama-server.exe
app/tutor/qwen-coder-1.5b-q4_k_m.gguf
app/licenses/
```

Set `THONNY_CLASSROOM_ROOT` to `app` when needed. Runtime discovery never changes
PATH, the registry, or a global installation. The Run button reuses the complete
private Python distribution that launches Thonny. Go uses its private GOROOT, a
per-user GOCACHE, `GO111MODULE=off`, `GOPROXY=off`, and `GOSUMDB=off`. Node is
called by its exact bundled path. Python uses the bundled interpreter when
present and Thonny's interpreter in development builds.

The application makes no network requests. Do not commit downloaded binaries or
the model. During release preparation, verify publisher checksums and place them
in the layout above. Copy `THIRD_PARTY_NOTICES.md` and exact upstream notices into
`app/licenses`. A portable ZIP is the MVP artifact; other platforms and a full
installer are future work.

## Local tutor worker

Qwen2.5-Coder-1.5B-Instruct Q4_K_M is the only runtime AI. Run llama.cpp in a
separate local process through `TutorWorkerClient`. Requests contain only the
language, normalized diagnostic, relevant 5–9 numbered lines, lesson level,
action, and previous hint count—not the full editor. Its system policy forbids
solutions and replacement programs. Responses are structured JSON and responses
over 100 words are rejected.

External npm, pip, and Go package installation is not exposed. The classroom
edition supports standard libraries only and works without internet or accounts.
