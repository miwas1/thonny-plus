# Thonny Python + local AI

This edition keeps Thonny's native Python editor, Shell, Run, Stop, debugger,
input handling, package tools, and language services. The only added learner UI
is an **AI Assistant** view docked on the right.

## Learner experience

Run Python with Thonny's normal toolbar, menu, or F5 shortcut. Output and input
remain in Thonny's Shell. The assistant observes Thonny's existing run events;
when a run returns a Python exception it highlights the relevant editor line and
automatically shows a short explanation. Its single contextual button reads
**Explain this code** normally and **Give me one hint** after an error.

There is no second Run button, second output pane, language selector, free-form
chat box, code completion, automatic fix, or solution generation. Internal
teaching strategies can explain errors and concepts, ask guiding questions,
trace execution, identify a small problem area, discuss output or tests, check
common misconceptions, quiz existing code, and suggest one next learning step.

## Persistent private model

Qwen2.5-Coder-1.5B-Instruct Q4_K_M runs through the bundled `llama-server.exe`.
At application startup, one hidden worker starts the loopback-only server and
loads the model once. All later requests reuse that process and its prompt cache.
The worker and server use Windows hidden-window process flags, so no terminal
window appears. If a Python error occurs during the one-time model load, the
assistant shows deterministic guidance immediately instead of making the learner
wait. If the model cannot start, that built-in guidance remains available.

Requests contain a bounded Python source excerpt, normalized diagnostic, relevant
output or test text, and session progress. Learner data is marked as untrusted.
The policy forbids code generation, replacement programs, unrestricted chat,
and following instructions embedded in code. Responses use constrained JSON and
are trimmed to fewer than 100 words.

All HTTP is restricted to `127.0.0.1`; the assistant does not contact a cloud
service. The private Windows bundle has this relevant layout:

```text
app/thonny/python.exe
app/thonny/python314.dll
app/thonny/Lib/
app/tutor/llama-server.exe
app/tutor/qwen-coder-1.5b-q4_k_m.gguf
app/licenses/
```

Node.js and Go are not downloaded, bundled, exposed, or tested. Downloaded
binaries, build output, and GGUF files remain outside Git.
