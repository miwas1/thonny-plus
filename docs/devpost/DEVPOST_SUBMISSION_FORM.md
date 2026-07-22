# OpenAI Build Week submission form — paste-ready pack

This is the single working document for filling the Devpost form. It covers
everything except the content of the required demo video. Replace every item
marked **REPLACE BEFORE SUBMITTING**.

## Core project details

| Field | Paste-ready answer |
| --- | --- |
| Project name | **Thonny Plus** |
| One-line tagline | **A private, offline Python learning assistant that explains errors without writing the answer.** |
| Track/category | **Education** |
| Project website / try-it-out URL | **https://thonny-plus.odebunmiwasiu124.chatgpt.site** |
| Code repository | **https://github.com/miwas1/thonny-plus** |
| Repository visibility | **Public** |
| Licence | **MIT** (upstream Thonny attribution and third-party notices are included) |
| Supported release platform | **Windows 10/11 x86-64** |
| Account or API key required | **No** |
| Internet required after installation | **No** |
| Sample data required | **No** |

## Why the track is Education

Choose **Education**, not Developer Tools. Thonny Plus is technically an IDE,
but the specific audience and impact are beginner learners. Its core innovation
is pedagogical: it interprets errors, gives bounded hints, avoids solution
generation, and keeps learner code private. “Developer Tools” is a plausible
secondary description of the software form; “Education” is the closest match
to the problem it solves and the users it serves.

## Short description options

### One sentence

Thonny Plus adds a private, offline AI Assistant to the beginner-friendly Thonny
IDE, automatically explaining Python errors and selected code without generating
the learner's solution.

### Two sentences

Thonny Plus turns Python errors into short, private learning guidance inside the
beginner-friendly Thonny IDE. A bundled Qwen model runs entirely on Windows, so
students get contextual explanations and hints without an account, internet
connection, cloud upload, or answer generator.

### Elevator pitch

Beginner programmers should not need to leave their IDE, upload their code, or
ask a chatbot for the answer just to understand an error. Thonny Plus embeds a
fully offline AI Assistant in Thonny's normal Python workflow: run code, see the
exception in the Shell, and receive a concise explanation automatically. Select
code or output for focused help; the model never writes a replacement solution.

## About the project

Paste the complete Markdown from
[`DEVPOST_PROJECT_STORY.md`](DEVPOST_PROJECT_STORY.md) into the **About the
project** field. It already uses Devpost's requested headings:

* Inspiration
* What it does
* How we built it
* Challenges we ran into
* Accomplishments that we're proud of
* What we learned
* What's next for Thonny Plus

## Built with / technologies

Use the tags the form accepts, prioritizing the first eight:

1. Codex
2. GPT-5.6
3. Python
4. Tkinter
5. Thonny
6. llama.cpp
7. Qwen2.5-Coder
8. Offline AI
9. GGUF
10. Inno Setup
11. PowerShell
12. Basedpyright
13. Ruff
14. GitHub Actions
15. AWS OIDC

## Installation and testing instructions

Paste this wherever Devpost asks judges how to access or test the project:

> Open https://thonny-plus.odebunmiwasiu124.chatgpt.site on a 64-bit Windows
> 10/11 computer and download the installer. Install and launch Thonny Plus; no
> account, API key, sample data, or additional runtime is required. Enter
> `def greet(name): return "Hello " + name` followed by `print(greet())`, then
> press the normal green Run button or F5. The Python exception appears in the
> Shell and the local AI Assistant explains it automatically. Select code in the
> editor or text in the Shell to test the focused, colour-coded explanation
> modes. The first local model load depends on CPU speed; later requests reuse
> the same process and prompt cache. Full source, tests, build instructions, and
> architecture notes are in the repository README.

## How Codex and GPT-5.6 were used

Paste this into any dedicated tool-usage field:

> Thonny Plus was forked during OpenAI Build Week, and Codex with GPT-5.6 was
> used for every feature added after the fork. I directed the product, tested
> real Windows builds, supplied screenshots and failure logs, and made the final
> scope decisions. Codex/GPT-5.6 implemented and refined the native Thonny event
> integration, contextual AI UI, exception capture, selection-aware bounded
> prompts, local Qwen worker, structured streaming, deterministic fallback,
> persistent model loading, hidden subprocesses, checksum-pinned Windows
> packaging, release automation, and 40-test regression suite. It was especially
> useful in tracing packaged-only failures across metadata, language servers,
> subprocesses, parsing, and Tk callbacks, then converting each finding into a
> coherent fix and a regression test.

## Codex session ID

**REPLACE BEFORE SUBMITTING:** run `/feedback` in the primary Codex build thread
and paste the returned session ID into Devpost's required field.

Value: `[PASTE /feedback CODEX SESSION ID HERE]`

## Links

| Link type | Value |
| --- | --- |
| Project / download website | https://thonny-plus.odebunmiwasiu124.chatgpt.site |
| Source repository | https://github.com/miwas1/thonny-plus |
| Setup and judge walkthrough | https://github.com/miwas1/thonny-plus#quickest-setup-for-judges |
| Build Week change evidence | https://github.com/miwas1/thonny-plus/blob/master/docs/devpost/BUILD_WEEK_CHANGELOG.md |
| Demo video | **Excluded from this pack; a public YouTube URL under three minutes is still required.** |

## Suggested gallery assets and captions

Devpost may allow multiple images even when only the video is required. Use
screenshots that prove the complete experience rather than architecture slides.

1. **Hero image:** editor, Python traceback, and completed AI explanation visible
   together. Caption: “One private learning loop: write, run, understand, try
   again.”
2. **Automatic error help:** missing-argument exception with the highlighted
   source line. Caption: “Python errors trigger a short explanation without a
   separate AI command.”
3. **Selection-aware help:** selected editor code and the active coloured action.
   Caption: “The assistant uses the learner's selection, not an activity menu.”
4. **Privacy proof:** AI panel with the Private indicator. Caption: “Qwen runs
   locally through loopback-only llama.cpp—no account or cloud upload.”
5. **Installer/release proof:** successful bundle verification and persistent
   Qwen smoke report. Caption: “Pinned artifacts, real-model smoke tests, and a
   reproducible Windows installer.”

Recommended hero image aspect ratio: 16:9, with readable text at thumbnail size
and no Task Manager or unrelated desktop windows behind the app.

## Submitter and team fields

These are personal facts that cannot be inferred from the repository:

* **REPLACE:** submitter's full legal name
* **REPLACE:** Devpost username
* **REPLACE:** email attached to Devpost/OpenAI Build Week
* **REPLACE:** country of residence
* **REPLACE:** solo entry or teammate names and Devpost usernames
* **REPLACE:** confirm every entrant is above the legal age of majority and
  eligible under the rules

Suggested team role if entering solo: **Product designer and developer**.

## Disclosure of pre-existing and third-party work

Paste this where disclosure is requested:

> This project is a Build Week fork of Thonny, the existing open-source Python
> IDE by Aivar Annamaa and contributors. The upstream Thonny base is pre-existing
> third-party work under the MIT License. The Thonny Plus fork and every custom
> feature described in this submission were started during the submission period
> and developed with Codex and GPT-5.6; the first feature commit is timestamped
> 2026-07-21 09:44:34 UTC. Bundled Python, llama.cpp, Qwen, and other dependencies
> retain their respective licences and notices. The repository's Build Week
> changelog distinguishes upstream functionality from the new work.

## Final declarations to verify personally

Before checking Devpost's legal boxes, confirm that:

* all team members meet age and country eligibility requirements;
* the public repository contains the MIT licence and third-party notices;
* you have the right to use every submitted screenshot, logo, voice, and sound;
* the demo accurately matches the downloadable build;
* the website's download button works without requesting access;
* the repository and website will remain available throughout judging;
* no secret, personal data, private model artifact, or API credential is present;
* the `/feedback` Codex session ID is correct; and
* every **REPLACE BEFORE SUBMITTING** marker in this document has been resolved.
