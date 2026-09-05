# Judge testing guide

## Fast path: use the packaged application

1. Use a 64-bit Windows 10 or Windows 11 computer.
2. Visit https://thonny-plus.odebunmiwasiu124.chatgpt.site and download the
   installer.
3. Install and launch Thonny Plus. The installer is self-contained; no Python,
   account, API key, or sample dataset is required.
4. Observe the right-hand **AI Assistant** and **Private** indicator.
5. Run the following with Thonny's green Run button or `F5`:

   ```python
   def greet(name):
       return "Hello " + name

   print(greet())
   ```

6. Confirm all of the following:

   * the traceback appears in the ordinary Thonny Shell;
   * the relevant source line is highlighted;
   * a short explanation appears automatically in the AI Assistant;
   * the contextual action becomes **Give me one hint**;
   * ticking **Detailed** in the header yields a longer answer, and the streamed
     text matches the final answer;
   * no browser, login, API key, second Run button, or second output pane appears.

7. Select `return "Hello " + name` in the editor. Confirm the assistant action
   changes text and colour, then request an explanation.
8. Select part of the traceback in the Shell and repeat. Confirm that the action
   indicates selected output rather than selected code.
9. Disconnecting the computer from the internet does not affect inference; all
   model traffic is loopback-only.

The first local model load is CPU-dependent. The application provides immediate
deterministic guidance during warmup, then reuses the loaded process and prompt
cache for subsequent model requests.

## Source-only verification

The repository intentionally excludes the GGUF model and downloaded Windows
runtimes. Source tests do not require them:

```bash
python -m unittest -v test_classroom.py test_classroom_model.py test_classroom_packaging.py
python -m compileall -q thonny/plugins
```

Expected result: 40 focused tests pass.

## Rebuild verification

Rebuilding is not required for judging. If desired, use a Windows x64 host with
Python 3.13 x64, pip, and Inno Setup 6:

```powershell
.\build-windows-classroom.ps1 -ReleaseVersion "6.0.0-classroom.1"
```

The command downloads and checksum-verifies every private artifact, runs the
source suite, validates the staged release, runs bundled Python and two real Qwen
requests through one worker, then creates the installer and its SHA-256 file.

## Privacy boundary to inspect

* `thonny/plugins/classroom/ui.py` — contextual learner interface
* `thonny/plugins/classroom/tutor.py` — bounded context and teaching policy
* `thonny/plugins/classroom/model_worker.py` — loopback server and streaming
* `packaging/windows/classroom/artifacts.json` — pinned private artifacts
* `packaging/windows/classroom/smoke_bundle.py` — runtime/model smoke test
* `test_classroom*.py` — focused regression suite
