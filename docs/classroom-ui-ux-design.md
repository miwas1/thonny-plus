# Offline Classroom — UI/UX Design

Design specification for the beginner classroom edition of Thonny with Python,
JavaScript, and Go support plus a local Qwen-based tutor. This document defines
the *intended* experience. It is a design spec, not an implementation.

Scope decisions and open questions are listed at the end. Where this document
contradicts the current code, the design is the target and the code is the
starting point.

---

## 1. Who this is for

A **first-time programmer** — someone who has possibly never run a program
before. They are easily overwhelmed by IDE chrome, they read error messages as
"the computer is angry at me," and they will happily ask an AI to "just write
it" if given a chat box. Everything below optimizes for that person.

Secondary user: a **teacher/lab admin** who installs the app on offline machines
and wants zero accounts, zero network, and zero configuration surface.

Three truths that drive every decision:

1. **Calm over capable.** Fewer choices, larger targets, plain words.
2. **Private by construction, and visibly so.** Trust is a feature, not a footnote.
3. **The tutor guides, never solves.** The UI must make "give me the answer"
   structurally impossible, not merely discouraged.

---

## 2. Design principles

| Principle | What it means concretely |
|---|---|
| **One calm surface** | At most three zones visible at once: *Write*, *See*, *Understand*. No debugger, package manager, variables table, or shell unless summoned. |
| **Words + icons, never icons alone** | Every control is labeled. `▶ Run`, not `▶`. Beginners don't yet share our glyph vocabulary. |
| **Progressive disclosure** | Start minimal. The tutor reveals one layer at a time. Advanced surfaces stay hidden until needed. |
| **No dead ends** | Every error state names one next action the learner can take. |
| **Same shape in every language** | Python, JS, and Go share one layout, one Run button, one output console, one tutor. Only syntax coloring and samples differ. |
| **Guardrails, not walls** | The tutor won't write solutions, but the UI should never feel punitive. It's an encouraging coach, not a locked door. |
| **Theme-honest** | Everything adapts to light *and* dark. No hardcoded colors that break in the other theme (a current bug — see §11). |

---

## 3. Information architecture

The whole experience is four surfaces:

```
1. Welcome        →  one-time, "What do you want to learn?"
2. Workspace      →  the main screen: Write · See · Understand
3. Tutor          →  a contextual card inside the Workspace (not a separate page)
4. Privacy note   →  a dialog reachable from the always-visible offline badge
```

There is intentionally **no**: project explorer, settings-heavy preferences,
package installer, account screen, or free-form chat.

---

## 4. First launch — Welcome

Shown once per machine/user (persist a flag). Modal, centered, dismissible into
Python by default.

```
┌───────────────────────────────────────────────┐
│              What would you like to learn?      │
│                                                 │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│   │    🐍     │  │    JS     │  │    Go     │  │
│   │           │  │           │  │           │  │
│   │  Python   │  │JavaScript │  │    Go     │  │
│   └───────────┘  └───────────┘  └───────────┘  │
│                                                 │
│   ● Everything stays on this computer.          │
│     No account or internet needed.              │
└───────────────────────────────────────────────┘
```

Behavior:
- Three large, equal, keyboard-navigable cards (Tab / arrow keys, Enter to pick).
- Picking a language: opens the Workspace, inserts that language's Hello sample
  **only if the editor is empty**, and sets syntax coloring.
- The offline line is present here too — trust is established before the first keystroke.
- You can change language later; this is a starting point, not a lock-in.

Microcopy: title "What would you like to learn?" — not "Select a language."
The learner is choosing a subject, not configuring a tool.

---

## 5. Workspace layout

**Recommended layout: editor dominant on the left, a "Coach" rail on the right.**

```
┌─ Offline Classroom ─────────────────────────── ● Offline & private ─┐
│  Python ▾      ▶ Run   ■ Stop            Ready                       │  ← header
├───────────────────────────────────┬─────────────────────────────────┤
│  1  print("Hello!")                │  OUTPUT                         │
│  2                                 │  ┌───────────────────────────┐  │
│  3                                 │  │ Hello!                     │  │
│  4                                 │  │                            │  │
│                                    │  └───────────────────────────┘  │
│           EDITOR (the star)        │  Input ▸ [__________]  Send     │
│                                    │                                 │
│                                    │  ┌─ Coach ──────────────────┐   │
│                                    │  │ (appears when there's    │   │
│                                    │  │  something to explain)   │   │
│                                    │  └──────────────────────────┘   │
└───────────────────────────────────┴─────────────────────────────────┘
```

Why this over a bottom console (Thonny's default and the current `"s"` dock):

- **Eyes move naturally left→right:** write the code, glance right for the
  result and the help. The error line highlighted in the editor sits at the same
  vertical height as the explanation, so cause and consequence are visible together.
- The Coach lives at the bottom of the same rail as output, reinforcing "the
  computer responded" as one column of feedback.
- On narrow screens the rail collapses under the editor (responsive fallback to
  a stacked layout) — the design must not assume width.

The three zones, named for the learner's mental model:

| Zone | Learner reads it as | Contents |
|---|---|---|
| **Editor** | "Where I write" | Code, line numbers, error line highlight. No breakpoint gutter, no debug margin. |
| **Output** | "What my program said" | stdout + stderr, one-line stdin, run status. |
| **Coach** | "Help me understand" | The tutor card. Hidden until relevant. |

Everything else Thonny normally shows (Files, Shell, Variables, Assistant,
Outline, Help, plugin panels) is **hidden** in classroom mode.

### Header bar

Slim, friendly, not a dense IDE toolbar. Left to right:

- **Language selector** — shows current language (`Python ▾`). Auto-switches from
  the file's extension; manual change is possible but rarely needed.
- **▶ Run** — the primary action. Largest, accent-colored, always reachable.
- **■ Stop** — enabled only while running; visually quiet when idle.
- **Status text** — one calm word/phrase (`Ready`, `Running…`, `Finished`,
  `Stopped`, `Timed out`). Never a stack trace.
- **● Offline & private** (far right) — persistent trust badge; opens the privacy note.

Deliberately **absent** from the header: New/Open/Save clutter (save happens
automatically on Run), debugger controls, interpreter/runtime settings, zoom,
plugins. One job: write and run.

---

## 6. The Coach (tutor) — the heart of the design

This is where the product's philosophy lives. The tutor **explains and asks; it
never writes the solution.** The interface enforces that by giving no free-text
"generate code" affordance — only scoped actions.

### 6.1 When the Coach appears

- **Automatically** after a Run that produced an error (a diagnostic exists).
- **On request** via a `Help me understand` button (see §12 — this closes the
  current gap where the tutor only ever reacts to errors).
- Never as an always-open panel demanding attention. Empty attention is noise.

### 6.2 Card anatomy

```
┌─ Coach ──────────────────────────────────────────────┐
│ What happened                                          │
│   Python couldn't find a name your program used.       │
│ Where                                                  │
│   Line 3.  (also highlighted in your code →)           │
│                                                        │
│ [ One hint ]  [ Explain the concept ]  [ Ask me a Q ]  │
│                                                        │
│ · answered privately on this computer ·                │
└────────────────────────────────────────────────────────┘
```

Structure of every response (already the deterministic contract — keep it):

1. **What happened** — one plain sentence, no jargon, no stack trace.
2. **Where** — the line, cross-referenced with the editor highlight.
3. **One concept** — named, not lectured.
4. **One next action** — a thing to try, never the fixed code.

Kept under ~100 words. The learner is never handed a wall of text.

### 6.3 Progressive help (the anti-spoiler mechanic)

The learner controls depth. Each button reveals exactly one more layer:

| Button | Gives | Rule |
|---|---|---|
| **One hint** | A single nudge toward the fix | One hint per click; a hint counter tracks how many were shown. Later hints get warmer/more specific, never the full answer. |
| **Explain the concept** | The idea behind the error (e.g. "variables and names") | Teaching, not fixing. |
| **Ask me a question** | A Socratic prompt: "What do you predict happens if…?" | Puts the learner back in the driver's seat. |
| **Try again** | Dismisses the card, returns focus to the editor | The point is to go edit and re-run. |

There is **no** "show me the answer" button, and **no** free-text box. That
absence is the design.

### 6.4 Coach states

| State | What the learner sees |
|---|---|
| **Idle / no error** | Card hidden. If summoned with nothing to explain: "Run your program first — if something breaks, I'll help you understand it." |
| **Thinking** | "Thinking on this computer…" with a quiet indeterminate indicator. Buttons disabled. Editor stays fully usable (inference is off the UI thread). |
| **Answered (local model)** | Full card as above, footer "answered privately on this computer." |
| **Answered (fallback)** | Identical layout, sourced from the deterministic tutor when the model is missing/slow/malformed. The learner should **not** be able to tell the difference — no error, no downgrade banner. Same calm voice. |
| **Model absent** | Silent fallback. Never surface "model not found" to a learner. |

### 6.5 Tutor voice guidelines

- Second person, warm, present tense: "Python couldn't find…", not "A
  `NameError` was raised."
- Never blame: "your program tried…", not "you did wrong."
- Never sarcasm, never exclamation-mark cheerfulness overload.
- Always end pointing forward: a question or a small action.
- Plain nouns: "name," "value," "block," "line" — not "identifier," "token,"
  "scope," "exception."

---

## 7. Key flows

### 7.1 Happy path — run and succeed
1. Learner writes code → presses **▶ Run** (or F5).
2. File auto-saves silently. Status → `Running…`. Stop enabled.
3. Output streams into the Output panel.
4. Status → `Finished`. If there was no output: "Program finished with no output."
   (Reassure — silence isn't failure.)

### 7.2 Error path — run and learn
1. Run produces a diagnostic.
2. The failing line is highlighted in the editor **and** scrolled into view.
3. Status → `Finished` (calm — not "ERROR" in red caps).
4. Coach card slides in automatically with *What / Where*.
5. Learner explores hints/concept/question, edits, re-runs. Highlight clears on
   the next run.

### 7.3 Stop
- **■ Stop** sends a graceful terminate to the whole process group, then forces
  if needed. Status → `Stopping…` → `Stopped`. Output keeps whatever was printed.

### 7.4 Timeout (infinite loop)
- After the timeout, the process is killed automatically.
- Status → `Timed out`. Output ends with a gentle line: "Your program ran too
  long and was stopped. Look for a loop that never ends." This is itself a
  teaching moment — the Coach can open on it.

### 7.5 Switching language
- Open a `.py` / `.js` / `.go` file → language and coloring switch automatically;
  no dialog.
- Manual switch via the header selector: if the editor is empty, insert that
  language's Hello sample; if not, just switch coloring (never overwrite work).

### 7.6 Standard input
- One-line input field under Output with a **Send** button (and Enter to send).
- Visible only conceptually as "type here if your program asks a question."
- Captured on the UI thread before the run starts (current behavior — keep it).

---

## 8. Component specs

### Run button
- Primary accent fill, largest control, text `▶ Run`, shortcut F5 (and Ctrl/Cmd+R).
- Disabled with no editor open; tooltip "Open or start a file to run it."

### Stop button
- Secondary/quiet when idle (dimmed), becomes solid while running. `■ Stop`, Esc.

### Language selector
- Read-only dropdown, three items. Shows an icon + word (`🐍 Python`).
- Changing it is low-stakes and reversible; never triggers a run.

### Output console
- Read-only, monospace, word-wrapped, generous line height.
- **Empty state:** "▸ Your program's output will appear here."
- stdout and stderr both shown; stderr not visually screamed (see color roles).
- Auto-scrolls to newest line while running.

### Input field
- Single line, placeholder "Type input for your program, then Send."
- Disabled when no program is running *and* none is expected; enabled on run.

### Editor
- Line numbers on. Error line highlight = a soft background band **plus** a small
  margin marker (not color alone — accessibility).
- No debugger gutter, no breakpoint dots, no minimap.
- Respects the user's font-size setting; default one step larger than IDE default.

### Offline badge
- Always visible, top-right. A filled dot + `Offline & private`.
- Click → the privacy dialog (§9). Color: a calm confirming hue, never alarm red.

---

## 9. Privacy & trust surface

Trust is a first-class feature for an offline classroom tool.

- **Persistent badge** in the header (always visible).
- **One-time note** on first launch (embedded in Welcome).
- **On-demand dialog** from the badge:

  > **Offline & private**
  > Your code and your questions stay on this computer.
  > No account and no internet connection are needed.
  > The tutor runs on this machine — nothing is sent anywhere.
  >
  > This classroom edition uses standard libraries only. Installing extra
  > packages from the internet is turned off.

- The tutor card footer ("answered privately on this computer") reinforces it at
  the moment of use.

Tone: reassuring statement of fact, not legalese, not a scary warning.

---

## 10. Visual design system (within Tk/ttk reality)

Tkinter can't do CSS; style through `ttk` styles and Thonny's theme tokens. The
key rule: **define semantic color roles once, provide light + dark values, and
reference roles — never hardcode hex in widgets.**

### Color roles

| Role | Used for | Light | Dark |
|---|---|---|---|
| `surface` | panel backgrounds | `#FFFFFF` | `#1E1E1E` |
| `surface-2` | cards, output box | `#F4F5F7` | `#252526` |
| `on-surface` | primary text | `#1A1A1A` | `#E6E6E6` |
| `muted` | secondary text, status | `#5F6673` | `#9AA0A6` |
| `accent` | Run button, focus, links | `#2E7D32` | `#4CAF50` |
| `success` | finished OK | `#2E7D32` | `#66BB6A` |
| `error-line` | error highlight band | `#FFE3E3` | `#5A2A2A` |
| `error-text` | error labels | `#B00020` | `#FF6B6B` |
| `keyword` / `string` / `comment` | syntax coloring (JS/Go) | see below | dark variants |

> Note: the current syntax coloring and error highlight use fixed light-mode hex
> (`#7f0055`, `#2a00ff`, `#3f7f5f`, `#ffd7d7`). These are illegible in dark mode
> and must be replaced by role lookups. See §11.

### Typography
- **Editor:** the user's chosen monospace; default size ≥ IDE default.
- **UI:** the platform system sans; comfortable size, not tiny.
- **Line height:** generous in Output and Coach for readability.
- **Hierarchy in the Coach:** bold section labels ("What happened", "Where"),
  regular body.

### Spacing & shape
- Consistent 8px spacing scale (4/8/12/16/24).
- Cards and the output box get soft, consistent internal padding — beginners
  read padded text as friendlier than edge-to-edge.
- Buttons: comfortable hit targets (min ~36px tall), text + optional icon.

### Iconography
- Minimal, always paired with a word. Suggested set: ▶ Run, ■ Stop, ● offline,
  🐍/JS/Go language marks, ▸ output prompt. No icon-only controls.

---

## 11. Accessibility

- **Contrast:** all text meets WCAG AA against its surface in both themes
  (the role table above is chosen for this).
- **Never color alone:** error line = background band **+** margin marker **+**
  the Coach naming the line. Status = word, not just a colored dot.
- **Keyboard:** Run = F5 / Ctrl+R; Stop = Esc; Tab order = editor → Run → output →
  coach actions; Welcome cards fully arrow-navigable; Enter activates focused control.
- **Font scaling:** honor Thonny's zoom/font-size; layout must not break when text
  grows.
- **Focus visibility:** a clear focus ring (accent role) on every focusable control.
- **Screen reader:** meaningful accessible names on buttons and the status line;
  Coach content announced when it appears.
- **Language:** microcopy stays short and jargon-free — an accessibility feature
  for cognitive load, not just a nicety.

---

## 12. Closing the "assistant scope" gap

Today the tutor only reacts to *errors*. The stated goal is "all AI assistants
except code generation." To honor that without adding a solution-writing chat,
add **on-demand, scoped** entry points that reuse the same Coach card and the
same never-solve rules:

| Entry point | Trigger | What the Coach does |
|---|---|---|
| **Explain this code** | Select lines → "Explain this" | Plain-language walkthrough of *the learner's own* code. No rewrites. |
| **What does this error mean?** | Automatic on error (existing) | Current behavior. |
| **Stuck? Get a hint** | Button, no error required | Socratic nudge about the current goal/line, one hint at a time. |
| **Concept help** | Button | Teach the concept behind the current line/selection. |

All four are the *same* card, *same* voice, *same* 100-word cap, *same* absence of
a "write it for me" path. This turns one reactive tutor into a small suite of
guides — still explicitly **not** a code generator.

---

## 13. Concrete deltas from the current implementation

Actionable mapping from today's code to this design (for the eventual build):

| Area | Current | Proposed change |
|---|---|---|
| Dock position | `ClassroomView` docked south (`"s"`) with output+tutor stacked | Editor-dominant left, Output+Coach in a right rail; responsive stack fallback |
| Header | Combobox + Run/Stop/Explain crammed in one toolbar | Slim friendly header; language selector shows icon+word; Run is primary/accent |
| Error highlight | Hardcoded `#ffd7d7` (breaks in dark) | `error-line` role + margin marker |
| Syntax colors | Hardcoded `#7f0055 / #2a00ff / #3f7f5f` | Theme-role lookups, dark variants |
| Tutor trigger | Only on error | Add on-demand "Explain this / Get a hint / Concept" (§12) |
| Fallback visibility | Same card (good) | Keep; ensure zero visible "downgraded" signal |
| Status wording | "Stopped by timeout", "Could not run" | Calmer learner phrasing (§7) |
| Onboarding label | "JS / Go" text buttons | Larger equal cards, keyboard-navigable, offline line included |
| Timeout (10s) | Same for all languages | Consider a longer budget for Go's cold compile (design note, not UI) |

---

## 14. Open questions

1. **Learner age band?** Children vs. teens vs. adult beginners changes tone,
   iconography, and default font size. This spec targets "adult/teen first-timer";
   tell me if it's for younger kids and I'll adjust warmth and visuals.
2. **Single dedicated window vs. docked-in-Thonny?** This spec assumes a focused,
   distraction-free layout (you already hide other panels). Confirm you don't want
   an "advanced mode" escape hatch back to full Thonny.
3. **On-demand assistant scope (§12)** — do you want the non-error assistants now,
   or keep v1 strictly error-only?
4. **Localization** — offline classrooms are often non-English. Should microcopy
   and tutor output be localizable from the start?
5. **Multiple files / one file?** Design assumes a single-file learner flow. If
   multi-file projects are needed, the IA grows a lightweight file strip.

---

## 15. Summary

The experience is one calm screen — *Write · See · Understand* — wrapped in a
persistent promise of privacy, with a tutor that is generous with understanding
and structurally incapable of handing over the answer. Every visual and
interaction choice serves a nervous first-time programmer: labeled controls,
plain words, one next step, and nothing on screen that they didn't ask for.
