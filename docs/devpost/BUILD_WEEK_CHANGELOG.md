# Build Week scope and Codex/GPT-5.6 evidence

## Eligibility statement

Thonny Plus is based on the pre-existing open-source Thonny IDE. The fork was
started during the OpenAI Build Week submission period. From the first fork
feature commit onward, Codex with GPT-5.6 was used for every custom feature
added to the upstream base.

The human builder selected the problem and audience, directed product decisions,
tested Windows bundles, supplied logs and screenshots, evaluated responses, and
accepted or rejected changes. Codex/GPT-5.6 acted as the implementation,
research, debugging, test, packaging, and documentation partner.

## Timestamp evidence

The first Thonny Plus feature commit is:

```text
commit: 0d34c396a5ab61a1531974df79b679731c94fdb2
time:   2026-07-21T09:44:34+00:00
title:  started the llm integration
```

This is after the official submission period opened on July 13, 2026 at 9:00 AM
Pacific Time. The repository contains 13 feature and stabilization commits dated
July 21, 2026, from `0d34c396` through `fb770e87`.

Judges can reproduce the evidence with:

```bash
git show -s --format=fuller 0d34c396
git log --since=2026-07-13 --date=iso-strict --pretty=fuller
git diff --stat 0d34c396^..HEAD
```

The feature implementation through commit `fb770e87` spans 58 files, with
approximately 4,348 insertions and 3,997 deletions relative to the parent of the
first feature commit. Deletions include removal of the inherited/cloud Codeium
integration and the abandoned multi-language prototype surface. Later
submission-documentation commits are intentionally not included in those
implementation figures.

## Pre-existing foundation

The following came from upstream Thonny and is not presented as new Build Week
work:

* the Python editor and syntax highlighting;
* Shell, native Python execution, Run/Stop, debugger, and input handling;
* workbench, plugin architecture, preferences, package tools, and existing
  language-service integration;
* upstream icons, translations, documentation, and packaging foundations.

Thonny is credited in the main README and its MIT licence is preserved.

## New work created during Build Week

### Product and interaction design

* Defined the private beginner-learning use case and “explain, don't solve”
  teaching policy.
* Prototyped a classroom surface, tested it against the normal Thonny workflow,
  and removed duplicated Run/output controls and the internal activity menu.
* Narrowed the initial Python/JavaScript/Go concept to a coherent native Python
  experience.
* Added the docked AI Assistant, automatic exception response, relevant-line
  highlighting, selection-aware editor/Shell context, mode colours, status
  messages, cancellation, and streamed rendering.

### Local AI system

* Added bounded diagnostic and source-context normalization.
* Added task-specific teaching strategies with deterministic fallbacks.
* Added prompt-injection boundaries that treat learner code as untrusted data.
* Added response schemas, structured parsing/recovery, short-answer enforcement,
  and protection against displaying partial malformed output.
* Added a persistent local worker and loopback-only llama.cpp server, hidden
  Windows subprocesses, single model load, prompt-cache reuse, prewarming, and
  streaming updates.
* Integrated Qwen2.5-Coder-1.5B-Instruct Q4_K_M without an account, API key, or
  cloud request.

### Windows distribution

* Added the Python 3.13 x64 build-server entry point.
* Added revision- and SHA-256-pinned artifact manifests for the embedded Python
  runtime, llama.cpp, and Qwen GGUF.
* Added dependency staging, licence collection, private bundle verification,
  release metadata, and Inno Setup generation.
* Added real bundled-Python and persistent-model smoke tests.
* Added safe resumable builds and Git ignores for models, downloads, caches, and
  release output.
* Added a manual GitHub Actions release path using AWS OIDC and protected
  environment controls.

### Reliability fixes driven by real Windows tests

* Staged discoverable Thonny package metadata to prevent the first-launch
  “No package metadata was found for thonny” error.
* Preserved Windows console scripts so Ruff's binary is available.
* Fixed Basedpyright discovery and startup diagnostics.
* Prevented stale callbacks from using a language server after it closes.
* Recovered structured fields from noisy local-model output and rejected truly
  incomplete responses.
* Enforced the short teaching response at field level rather than failing a
  successful inference because wrapper text exceeded a global word count.
* Kept model processes hidden and persistent to avoid terminal popups and repeat
  cold loads.

### Verification

The focused source suite has 40 passing tests across:

* native Thonny event integration and fallback execution;
* policy, bounded context, activity selection, and response limits;
* streaming, cancellation, structured-output recovery, and worker reuse;
* hidden Windows process flags and model prewarming;
* package metadata, Ruff/Basedpyright staging, artifact checksums, release gates,
  Git exclusions, and release workflow safety.

Run it with:

```bash
python -m unittest -v test_classroom.py test_classroom_model.py test_classroom_packaging.py
```

## Key decisions made with Codex/GPT-5.6

| Decision | Evidence in the finished project |
| --- | --- |
| Preserve Thonny instead of building a second IDE inside it | One native Run path and one native Shell; the assistant only observes events |
| Ship Python deeply instead of three languages shallowly | Node.js/Go adapters and bundle artifacts were removed from the final product |
| Embed AI actions instead of exposing an activity menu | One contextual, colour-coded action changes from explanation to hint or selection mode |
| Keep inference private | Bundled Qwen + llama.cpp, loopback-only HTTP, no account or API key |
| Teach without solving | No code generation, replacement programs, automatic fixes, or unrestricted chat |
| Optimize perceived wait safely | Immediate fallback during warmup, persistent worker, prompt caching, streaming, and cancellation |
| Treat packaging as part of functionality | Checksum verification, real-model smoke tests, licences, metadata, and installer release gates |

## Primary Codex session

The Devpost form requires the `/feedback` session ID from the primary Codex
thread. It is intentionally not invented or committed here. The submitter must
run `/feedback` in that thread and paste the returned identifier directly into
the form.
