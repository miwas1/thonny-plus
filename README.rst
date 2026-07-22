===========
Thonny Plus
===========

**A private, offline Python learning assistant that explains errors without
writing the answer.**

Thonny Plus extends the beginner-friendly `Thonny IDE <https://thonny.org/>`_
with an embedded AI Assistant. A learner writes and runs ordinary Python using
Thonny's editor, Shell, Run button, input handling, and debugger. When Python
raises an exception, the assistant automatically provides a short explanation
and one useful next step. Learners can also select code or Shell output and ask
for a focused explanation.

The assistant runs entirely on the learner's Windows computer. It uses a
bundled Qwen2.5-Coder 1.5B model through llama.cpp, requires no account or API
key, and does not send code to a cloud service.

* Download / project site: https://thonny-plus.odebunmiwasiu124.chatgpt.site
* Source: https://github.com/miwas1/thonny-plus
* OpenAI Build Week track: **Education**


Why it exists
=============

Beginner error messages are precise but rarely beginner-friendly. General AI
chat tools can explain them, but they introduce copy-pasting, context switching,
accounts, internet access, privacy concerns, and a strong temptation to request
the finished solution. Thonny Plus keeps the learning loop inside the IDE:

``write -> run -> understand -> try again``

It is intentionally an assistant rather than a code generator. The model policy
forbids replacement programs, automatic fixes, unrestricted chat, and solution
generation. Its job is to help the learner reason about their own program.


What works
==========

* Native Thonny Python editor, Shell, Run/Stop controls, debugger, standard
  input, and package tools remain the primary interface.
* Python exceptions trigger a concise explanation automatically.
* The relevant source line is highlighted after an error.
* Selecting editor code changes the action to a focused **Explain selected
  code** mode.
* Selecting Shell text changes the action to **Explain selected output**.
* After an exception, the contextual action becomes **Give me one hint**.
* Button colour indicates which context and assistant mode are active.
* Responses stream into the panel and are capped to a short classroom-sized
  answer without cutting off the completed message.
* A persistent hidden llama.cpp server loads the model once and reuses prompt
  cache across requests.
* Deterministic guidance appears immediately while the model is warming up or
  if local inference is unavailable.
* The Windows bundle includes Python, llama.cpp, the quantized Qwen model,
  Basedpyright, Ruff, licences, and package metadata.
* There is no duplicate Run button, second output pane, language selector,
  free-form chat, cloud request, or account sign-in.


Quickest setup for judges
========================

Supported release platform
--------------------------

The ready-to-test release targets **64-bit Windows 10 or Windows 11**. The
installer contains its own Python runtime and local model; end users do not need
to install Python, llama.cpp, or Qwen separately.

1. Open https://thonny-plus.odebunmiwasiu124.chatgpt.site.
2. Download the Windows x64 installer.
3. Run the installer and launch Thonny Plus.
4. Wait for the right-hand AI Assistant to report that local AI is ready. The
   first model load is slower than later requests and depends on CPU speed.
5. Enter this program and press Thonny's normal green Run button or ``F5``::

       def greet(name):
           return "Hello " + name

       print(greet())

6. Python reports the missing argument in the Shell. The AI Assistant explains
   the error automatically and offers **Give me one hint**.
7. Select a line in the editor or text in the Shell to see the contextual action
   and its colour change, then request the focused explanation.

No sample data, account, network connection, or API key is required after the
installer has been downloaded.


Run and test from source
========================

The source project requires Python 3.11 or newer. A system Tk installation is
also required on Linux. The complete local-model experience is easiest to test
with the Windows installer because the multi-gigabyte model and downloaded
runtime binaries are deliberately excluded from Git.

.. code-block:: console

   git clone https://github.com/miwas1/thonny-plus.git
   cd thonny-plus
   python -m venv .venv

On Windows:

.. code-block:: powershell

   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -e .
   python -m thonny

On Linux or macOS:

.. code-block:: console

   . .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e .
   python -m thonny

Run the focused validation suite:

.. code-block:: console

   python -m unittest -v test_classroom.py test_classroom_model.py test_classroom_packaging.py
   python -m compileall -q thonny/plugins

The suite currently contains 40 passing tests covering the assistant policy,
bounded context, selection-aware actions, streaming, persistent inference,
fallback behaviour, language-service failures, installer staging, artifact
checksums, release gates, and Windows hidden-process behaviour.


Build the complete Windows installer
====================================

The installer build host must be 64-bit Windows with **Python 3.13 x64**, pip,
and Inno Setup 6. From the repository root in PowerShell:

.. code-block:: powershell

   .\build-windows-classroom.ps1 -ReleaseVersion "6.0.0-classroom.1"

The script:

1. runs the source tests and compile checks;
2. downloads checksum-pinned Python, llama.cpp, and Qwen artifacts;
3. assembles and verifies the private bundle;
4. starts the real bundled model and performs two persistent-worker smoke tests;
5. creates the signed-input-ready Inno Setup executable and SHA-256 file.

The output is written under the Git-ignored directory::

   .classroom-build\6.0.0-classroom.1\release\
   thonny-classroom-6.0.0-classroom.1-windows-x64-setup.exe

The Qwen model, downloaded runtimes, caches, and installer are never committed.
See `packaging/windows/classroom/README.md
<packaging/windows/classroom/README.md>`_ for the release and optional S3 upload
workflow.


Architecture and privacy
========================

The classroom plugin observes Thonny's existing run events instead of replacing
the editor or execution backend. It normalizes the Python diagnostic and sends
only a bounded, task-specific excerpt to a persistent local worker. The worker
starts ``llama-server.exe`` on a random loopback port, constrains output with a
JSON schema, and streams the structured response back to the Tk UI.

Only ``127.0.0.1`` HTTP is used. Source code, errors, selections, and model
responses stay on the computer. User code is treated as untrusted data, so text
inside a program cannot override the teaching policy. See
`docs/offline-classroom.md <docs/offline-classroom.md>`_ for the detailed data
flow and policy.


How Codex and GPT-5.6 were used
===============================

Thonny Plus was forked and developed during OpenAI Build Week. From the first
fork commit onward, **Codex with GPT-5.6 was used for every feature added to the
upstream Thonny base**. The human builder directed product scope, tested the
real Windows builds, supplied failure logs and screenshots, and made the final
product decisions. Codex/GPT-5.6 served as the implementation and debugging
partner across the repository.

The collaboration directly produced:

* the initial Python, JavaScript, and Go classroom prototype, followed by the
  deliberate decision to narrow the finished product to one excellent native
  Python learning flow;
* the redesign from four Coach buttons and an internal activity menu to one
  contextual assistant action embedded in the learner's normal workflow;
* automatic exception capture, editor-line highlighting, focused editor/Shell
  selection context, mode colours, bounded prompts, and streamed responses;
* the local-model protocol, structured-output recovery, deterministic fallback,
  hidden Windows processes, persistent model loading, and prompt caching;
* the reproducible Python 3.13 Windows build entry point, pinned artifact
  manifest, licence staging, smoke tests, release verification, and manual OIDC
  release workflow; and
* investigation and fixes for real packaged-app failures involving missing
  Thonny distribution metadata, Ruff executables, Basedpyright startup, closed
  language servers, malformed model output, inference timeouts, and response
  length enforcement.

Codex was most valuable in keeping the fixes connected across UI, subprocess,
model, packaging, and test layers. GPT-5.6 helped reason from each Windows log to
the affected implementations, propose the smallest coherent correction, and
add regression coverage instead of treating each symptom in isolation.

Build Week evidence
-------------------

The first Thonny Plus feature commit is
``0d34c396a5ab61a1531974df79b679731c94fdb2``, timestamped
**2026-07-21 09:44:34 UTC**, inside the official submission period. The public
history then records the local-model integration, bundling, Python-only product
decision, Ruff/Basedpyright packaging fixes, persistent worker, streaming, and
UI refinements. The Build Week change record is documented in
`docs/devpost/BUILD_WEEK_CHANGELOG.md
<docs/devpost/BUILD_WEEK_CHANGELOG.md>`_.

Submission materials
--------------------

The repository includes a complete judge and submission pack:

* `paste-ready Devpost project story
  <docs/devpost/DEVPOST_PROJECT_STORY.md>`_;
* `field-by-field submission form answers
  <docs/devpost/DEVPOST_SUBMISSION_FORM.md>`_;
* `Build Week scope and timestamp evidence
  <docs/devpost/BUILD_WEEK_CHANGELOG.md>`_;
* `judge testing guide <docs/devpost/JUDGE_TESTING_GUIDE.md>`_; and
* `deadline and final submission checklist
  <docs/devpost/SUBMISSION_CHECKLIST.md>`_.


Known limitations and next steps
================================

The distributed build currently targets Windows x64. CPU speed and available
memory affect the first model load and token rate. The next engineering target
is a measured sub-five-second first visible token on typical classroom PCs using
smaller prompt prefixes, cache-aware prewarming, hardware-tuned llama.cpp
settings, and explicit low-memory profiles. Linux and macOS bundles, broader
accessibility testing, multilingual explanations, and educator-controlled
teaching profiles are planned after the Windows release is hardened.


Attribution and licence
=======================

Thonny Plus is a modification of Thonny, the Python IDE created by Aivar
Annamaa and contributors. The project source remains under the MIT License in
`LICENSE.txt <LICENSE.txt>`_. Bundled third-party components retain their own
licences and notices; see `THIRD_PARTY_NOTICES.md <THIRD_PARTY_NOTICES.md>`_.
The Windows build stages the exact Python, llama.cpp, and Qwen notices beside
the corresponding artifacts.

This project is an independent OpenAI Build Week submission and is not endorsed
by or affiliated with OpenAI, Thonny's upstream maintainers, Qwen, or llama.cpp.
