# Verbic

**Verbic** is a Windows system-tray app that helps you write better in *any*
application — Word, Chrome, Slack, Discord, Notepad, Gmail, anywhere you can
type. It fixes grammar inline as you pause, rewrites tone on demand, drafts
whole replies from context you give it, and can even predict how you'd finish a
sentence. Everything surfaces as a suggestion you explicitly accept — Verbic
never silently rewrites your words.

Published by **Sand Castle LLC**. Current version: **1.2.6**.

> ### 🔑 You need an AI provider before Verbic can do anything
> Verbic doesn't ship with its own AI — it connects to one you choose. Pick one:
> - **A cloud provider** (OpenAI, Claude, DeepSeek, Grok, Groq) — sign up, copy a
>   free **API key**, and paste it into **Settings**. Best quality, takes 2 minutes.
> - **Ollama** (local) — install it and pull a model. **No API key, no internet,
>   fully private**, but quality depends on your computer.
>
> Without one of these configured, suggestions won't appear. See
> [AI providers](#ai-providers) and [Using Ollama](#using-ollama-free-fully-local).

---

## Table of contents

- [What Verbic does](#what-verbic-does)
- [Quick start](#quick-start)
- [Hotkeys](#hotkeys)
- [Tray menu](#tray-menu)
- [Features in depth](#features-in-depth)
  - [Grammar & tone correction](#grammar--tone-correction)
  - [Writing context](#writing-context)
  - [Draft answer](#draft-answer)
  - [Floating selection toolbar](#floating-selection-toolbar)
  - [Predictive (Flow) Mode](#predictive-flow-mode)
  - [Shortcuts & Buttons window](#shortcuts--buttons-window)
- [AI providers](#ai-providers)
- [Using Ollama (free, fully local)](#using-ollama-free-fully-local)
- [Settings & testing](#settings--testing)
- [Installation](#installation)
- [Building from source](#building-from-source)
- [Configuration file](#configuration-file)
- [Project layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [Privacy](#privacy)
- [Requirements](#requirements)
- [Legal & license](#legal--license)

---

## What Verbic does

- **Inline grammar fixes** — pause while typing and a small overlay shows a
  corrected version near your caret. **Apply** it (Ctrl+Space), **Copy** it to
  the clipboard, or **Dismiss** it.
- **Tone rewrites** — formal, casual, professional, friendly, confident,
  concise, persuasive, empathetic, academic, or playful — plus 19 **accent/
  dialect** tones (British, Aussie, Scottish, Irish, Texan/cowboy, pirate,
  surfer, Shakespearean, redneck, and more).
- **Expand** — elaborate a terse note into something fuller.
- **Writing context** — pin a question, email, or topic so every suggestion is
  shaped to what you're actually responding to.
- **Draft answer** — let the AI write a complete reply to a selected message or
  your pinned context, then insert it at the caret.
- **Floating toolbar** — highlight text with the mouse and a little action bar
  pops up next to it (Set context · Answer · Fix) — no keyboard needed.
- **Predictive (Flow) Mode** — predicts how you'd continue a sentence and
  pre-drafts answers in the background so they appear instantly.
- **Customizable everything** — rebind every hotkey and choose which toolbar
  buttons appear.

Verbic runs entirely on the **AI provider you configure** — local (Ollama) or
cloud (OpenAI, Claude, DeepSeek, Grok, Groq, or any OpenAI-compatible endpoint).

---

## Quick start

**Step 1 — Install & launch.** Run `VerbicSetup.exe`. A small **V** icon appears
in your system tray (the little icons next to the clock, bottom-right). A
**Welcome** dialog walks you through the basics.

**Step 2 — Connect an AI provider (required).** Right-click the **V** icon →
**Settings**:

- *Easiest (cloud):* choose **OpenAI**, **Claude**, **DeepSeek**, **Grok**, or
  **Groq**, paste your **API key** (see the links under
  [AI providers](#ai-providers)), and click **Save**. Use **Run test** to confirm
  it works.
- *Private (local):* choose **Ollama**, after installing it and pulling a model —
  no API key needed. See [Using Ollama](#using-ollama-free-fully-local).

**Step 3 — Start writing.** In any app:

- **Type normally.** After you pause, a suggestion appears near your cursor —
  press **Ctrl+Space** or click **Apply** to accept it.
- **Fix on demand:** select text (or just finish a sentence) and press
  **Ctrl+Shift+G**.
- **Get a reply written for you:** highlight a question, press **Ctrl+Alt+X** to
  set it as context, then **Ctrl+Alt+A** to draft an answer.

> 💡 If nothing happens when you type, you almost certainly haven't finished
> Step 2 — open Settings and make sure a provider is configured and **Run test**
> succeeds.

---

## Hotkeys

All four hotkeys are **rebindable** (tray → **Shortcuts & Buttons**). Defaults:

| Shortcut | Action |
|----------|--------|
| **Ctrl+Shift+G** | Fix typed text / selection / whole field |
| **Ctrl+`** | Fixed alias for Fix (not rebindable) |
| **Ctrl+Space** | Apply the visible suggestion — otherwise fix selection / typed text |
| **Ctrl+Alt+X** | Set the highlighted text as your writing context |
| **Ctrl+Alt+A** | Draft an answer from the context / selection |
| **Apply** button (auto-suggest only) | Apply the suggestion in place |
| **Copy** button (in overlay) | Copy the suggestion to the clipboard |
| **Dismiss** button / ✕ | Discard the suggestion |
| Double-click tray icon | Open Settings |
| Keep typing | Dismiss the overlay (a new suggestion fires after you pause) |

---

## Tray menu

Right-click the tray icon:

- **Pause / Resume corrections** — disable everything without quitting
- **Fix Grammar** — spelling, punctuation, grammar (on by default)
- **Tone** / **Accents** — two submenus of mutually-exclusive rewrites (10
  writing styles + 19 accents/dialects)
- **Expand** — elaborate the text
- **Auto Suggest (typing)** — inline overlay while you type
- **Predictive (Flow) Mode** — sentence prediction + eager answer pre-draft
- **Context: …** — shows the active writing context (or "none")
- **Set Clipboard as Context** — pin whatever is on the clipboard
- **Draft Answer from Context** — generate a reply now
- **Clear Context** — drop the pinned context
- **Show button on selection** — toggle the floating toolbar
- **Settings** — provider, model, API key, live test
- **Shortcuts & Buttons** — rebind hotkeys, pick toolbar buttons
- **Check for Updates** — manual update check
- **About** — version, license, hotkeys
- **Quit**

The active provider is shown as a dim line in the menu and on the tray-icon
hover tooltip, along with the current context (if any).

---

## Features in depth

### Grammar & tone correction

With **Fix Grammar** (and optionally a **Tone** or **Expand**) enabled, Verbic
sends your text to the provider and shows a cleaned-up version. Tones are
mutually exclusive — picking one clears the others so the model gets a single,
unambiguous instruction. Suggestions appear automatically while you type (if
**Auto Suggest** is on) or on demand via the Fix hotkey.

The overlay never steals focus and is positioned at your caret using, in order:
the Win32 caret, UI Automation text selection (for Electron/Chromium apps), the
focused control bounds, the mouse cursor, and finally the window rectangle.

Each overlay shows a header describing what it is (e.g. *✦ Grammar ·
Professional*, *✦ Draft answer*) and action buttons:

- **Auto-suggest / prediction** popups (the caret is in the field) offer
  **Apply (Ctrl+Space)**, **Copy**, and **Dismiss**.
- **Draft answer** and **toolbar Fix** popups are **copy-only** — **Copy** and
  **Dismiss** (no Apply). Applying in place is unreliable once focus has moved,
  so you copy the result and paste it where you want it.

### Writing context

Pin a piece of text — a question someone asked, an email you're replying to, the
topic you're writing about — and every suggestion is shaped to it (tone, format,
vocabulary). Set it three ways:

- **Highlight text → Ctrl+Alt+X**
- **Highlight text → click "✎ Context"** on the floating toolbar
- **Copy text → tray → Set Clipboard as Context**

The context persists across restarts and is shown in the tray menu and tooltip.
Clear it from the tray when you're done. With **no** context set, Verbic behaves
exactly like a plain grammar fixer — the context block is simply omitted.

### Draft answer

Press **Ctrl+Alt+A** (or tray → **Draft Answer from Context**) and Verbic writes
a complete, ready-to-send reply. It chooses what to answer in this order:

1. A live text selection
2. The pinned writing context
3. Whatever you've typed so far

The draft appears in the overlay; **Apply** (Ctrl+Space) inserts it at your
caret, or **Copy** puts it on the clipboard to paste elsewhere. This is *insert*
mode — nothing is replaced, the answer is dropped in where you are.

### Floating selection toolbar

Highlight text with the mouse — by dragging **or** double-clicking a word — and a
small action bar appears next to it. All three buttons show by default; pick
which appear in tray → Shortcuts & Buttons:

- **✎ Context** — set the selection as writing context
- **✦ Answer** — draft a reply to the selection
- **✓ Fix** — reformat the selection using your active toggles (grammar +
  whatever tone is set, e.g. *Professional*); accepting pastes it over the
  selection. The button shows the active tone, e.g. **✓ Fix · Professional**.

The bar never steals focus (so your selection stays intact), has a **✕** to
dismiss it, auto-dismisses after ~8 seconds, and disappears when you start
typing. Turn the whole thing off with **Show button on selection** in the tray.

### Predictive (Flow) Mode

A single toggle (tray → **Predictive (Flow) Mode**) that turns on two "work
ahead" behaviors:

- **Next-sentence prediction** — when you pause mid-thought, Verbic predicts how
  you'd continue and offers it as an insert-at-caret suggestion (Ctrl+Space to
  accept). In this mode the typing-pause slot is used for prediction; grammar
  fixes remain available via the Fix hotkey.
- **Eager answer pre-draft** — the moment you set a context, Verbic drafts the
  answer in the background, so pressing the answer hotkey returns instantly.

Off by default. Prediction quality depends heavily on your model — cloud
providers and larger Ollama models give noticeably better continuations.

### Shortcuts & Buttons window

Tray → **Shortcuts & Buttons** opens a window where you can:

- **Rebind any hotkey** — click a shortcut, then press the combination you want.
  It captures the exact key + modifiers. **Esc** cancels a capture.
- **Restore defaults** — reset all four bindings.
- **Pick toolbar buttons** — toggle the master "Show toolbar when I select text"
  and choose which of Context / Answer / Fix appear.

Changes apply live — no restart needed.

---

## AI providers

| Provider | API key | Notes |
|----------|:---:|-------|
| **Ollama** (local) | — | Free, runs on your CPU/GPU, fully offline |
| **OpenAI** | ✓ | gpt-4o-mini, gpt-4o, gpt-4.1-nano, gpt-4.1-mini |
| **Claude** | ✓ | claude-sonnet-4, claude-haiku-4.5 |
| **DeepSeek** | ✓ | deepseek-chat, deepseek-reasoner |
| **Grok (xAI)** | ✓ | grok-3-mini, grok-3 |
| **Groq** | ✓ | llama-3.3-70b, mixtral, gemma2 — fast, free tier |
| **Custom** | ✓ | Any OpenAI-compatible `/chat/completions` endpoint |

API-key links: [OpenAI](https://platform.openai.com/api-keys) ·
[Claude](https://console.anthropic.com/settings/keys) ·
[DeepSeek](https://platform.deepseek.com/api_keys) ·
[Grok](https://console.x.ai) · [Groq](https://console.groq.com/keys)

Requests use a low temperature (0.2) for consistent edits. Reasoning-model
output (`<think>…</think>` blocks), code fences, preambles, and wrapping quotes
are stripped automatically from responses.

---

## Using Ollama (free, fully local)

1. Install Ollama from <https://ollama.com>.
2. Pull a small instruct model. For the **fastest** live suggestions:
   ```
   ollama pull llama3.2:1b
   ```
   ⚡ ~1.3 GB; sub-second per correction on most CPUs — the recommended default.
   For a bit more quality at some speed cost: `llama3.2:3b`. Bigger models
   (`llama3.1:8b`, `70b`) are noticeably slower and not needed for grammar.

   > ⚠ Avoid reasoning models (`deepseek-r1`, `qwq`, `o1`-style) — they spend
   > 30+ seconds "thinking" before answering, which breaks live auto-suggest
   > and Predictive (Flow) Mode.
3. Tray → **Settings** → Provider: **Ollama (Local)**.
4. The model dropdown auto-detects pulled models — `● installed`,
   `○ pull required`. Click **Refresh** if you pulled one after opening
   Settings.

Ollama models are pre-warmed at launch so the first suggestion doesn't pay the
cold-start penalty.

---

## Settings & testing

The **Settings** window configures the provider, model, API key, and (for
custom) base URL. It includes a **Test** field with a sample sentence and a
**Run test** button so you can see exactly what the active provider produces
before saving — useful for tuning a model or verifying an API key.

---

## Installation

### Option 1 — Installer (recommended)

Run `VerbicSetup.exe`:

- **All-users install** to `C:\Program Files\Verbic\` — a known, reviewable
  location (requires admin/UAC; expected for managed/corporate endpoints)
- **Optional desktop shortcut** (checkbox during install)
- **Optional auto-start on login** (checkbox, off by default)
- **EULA** shown on the License page
- **Auto-kills** any running Verbic before overwriting (safe re-install)
- Appears in *Add or Remove Programs* under publisher *Sand Castle LLC*

Settings and logs are stored under `%APPDATA%\Verbic\` (never in the program
folder or Temp). See [SECURITY.md](SECURITY.md) for network destinations and
data handling.

> **Windows SmartScreen** may warn the first time if the build isn't yet
> code-signed. Click **More info → Run anyway**.

### Option 2 — Standalone

Run `Verbic\Verbic.exe` from the build folder directly (keep the `_internal\`
folder next to it). No install, no Start-menu shortcut, no auto-start.

### Option 3 — From source

Requires Python 3.10+ on Windows.

```powershell
git clone <repo-url>
cd grammar-tool
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

---

## Building from source

### Build the EXE

```powershell
python build.py
```

Produces a `dist\Verbic\` folder (`Verbic.exe` + an `_internal\` folder with
`python3xx.dll` and dependencies) with publisher metadata embedded
(CompanyName: Sand Castle LLC). It's a `--onedir` build — the DLLs sit next to
the exe instead of being unpacked to a temp folder on each launch, which avoids
the "Failed to load Python DLL" error during auto-update.

### Build the installer

Requires [Inno Setup 6](https://jrsoftware.org/isdl.php).

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Or open `installer.iss` in the Inno Setup Compiler and press **F9**.
Output: `installer_output\VerbicSetup.exe`.

### Run tests

```powershell
python -m pytest tests\ -q
```

### Debug logging

Set `GRAMMAR_DEBUG=1` before launching to write a diagnostic log to
`%TEMP%\verbic.log`:

```powershell
$env:GRAMMAR_DEBUG="1"
.\dist\Verbic.exe
```

The log shows provider choice, suggest-thread lifecycle, focus changes, and
suggestion decisions.

---

## Configuration file

Settings persist to `config.json` in your user profile —
`%APPDATA%\Verbic\config.json` — so they survive app updates (older builds kept
it next to the executable, which the installer could overwrite, wiping the saved
API key; that config is migrated automatically on first launch). Notable keys:

| Key | Meaning |
|-----|---------|
| `provider` | Active AI provider |
| `providers` | Per-provider `model`, `api_key`, `base_url` |
| `options` | Toggles: `grammar`, tones, `expand`, `auto_suggest`, `speculation` (Predictive Mode) |
| `hotkeys` | Per-action bindings (`ctrl`/`shift`/`alt`/`vk`/`label`) |
| `toolbar` | Which floating-toolbar buttons are enabled |
| `selection_button` | Master on/off for the floating toolbar |
| `writing_context` | The pinned writing context (persists across restarts) |

API keys are stored locally in this file and are never transmitted by Verbic
itself (only sent to the provider you chose, as part of a request).

---

## Project layout

```
grammar-tool/
├── main.py                 # entry point; redirects stdout/stderr in --noconsole builds
├── tray_app.py             # tray icon + orchestration of every feature
├── keyboard_monitor.py     # global hotkeys (configurable), typing buffer, mouse selection
├── focus_watcher.py        # SetWinEventHook to react to foreground-window changes
├── suggestion_window.py    # inline suggestion overlay (frameless, non-focus-stealing)
├── selection_button.py     # floating selection toolbar (Context / Answer / Fix)
├── shortcuts_window.py     # rebind hotkeys + pick toolbar buttons
├── welcome_window.py       # first-run welcome / provider picker
├── settings_window.py      # provider/model/API-key config + live test
├── text_replacer.py        # ctypes clipboard + Shift+Left / Ctrl+A / insert injection
├── text_reader.py          # reads focused field via Windows UI Automation
├── prompt_builder.py       # builds correction / answer / prediction prompts
├── ollama_client.py        # Ollama HTTP client + status/list-models + warm-up
├── openai_client.py        # OpenAI-compatible client (also DeepSeek, Grok, Groq, Custom)
├── claude_client.py        # Anthropic API client
├── text_utils.py           # response cleanup (<think> stripping, quote unwrapping)
├── debug_log.py            # opt-in diagnostic logger (GRAMMAR_DEBUG=1)
├── config.py               # provider catalog, defaults, persistent settings (config.json)
├── updater.py              # self-update check/install
├── version.py              # single source of truth for APP_VERSION
├── build.py                # PyInstaller build with embedded version info
├── installer.iss           # Inno Setup script
├── version_info.txt        # Windows EXE metadata (Sand Castle LLC)
├── EULA.txt                # end-user license agreement (bundled with installer)
├── PRIVACY.md              # privacy policy
├── tests/                  # unit tests
└── icon.png / icon.ico     # V app icon
```

---

## Troubleshooting

| Problem | Try |
|---|---|
| No suggestion overlay appears | Tray → confirm **Auto Suggest (typing)** is checked. The threshold is ≥15 chars ending in `.!?`, or ≥30 chars otherwise. |
| Auto-suggest with Ollama feels slow | Use a small instruct model (`llama3.2:3b`). Reasoning models take 30+ s. |
| A hotkey does nothing | It may clash with the app you're in. Tray → **Shortcuts & Buttons** → rebind it to a free combo. |
| Floating toolbar doesn't appear | Tray → enable **Show button on selection**; check at least one button is enabled in Shortcuts & Buttons. |
| "No text selected" when setting context | The app's selection collapsed before the copy. Try selecting again; the toolbar/Ctrl+Alt+X both copy the live selection. |
| Settings won't open | Right-click the tray icon → Settings (or double-click the icon). The window comes to the front automatically. |
| Overlay shows but Ctrl+Space does nothing | Click the **Apply** button instead. If neither works, quit and relaunch to re-arm the global keyboard hook. |
| Antivirus flags the app | The global keyboard hook (pynput) is the same mechanism AutoHotkey and text expanders use. Add an exception for `Verbic.exe`. |

---

## Privacy

- Sand Castle LLC operates **no servers** that receive your text. The app runs
  entirely on your machine.
- Verbic sends your typed/selected text to whichever **provider** you configure.
  Ollama is local; all other providers are cloud services with their own privacy
  policies — review them before sending sensitive content.
- API keys are stored locally in `config.json` and are never transmitted by
  Verbic itself.
- See [PRIVACY.md](PRIVACY.md) for the full policy.

---

## Requirements

- Windows 10 or 11
- For cloud providers: an internet connection and a valid API key
- For local AI: [Ollama](https://ollama.com) running, with at least one model
  pulled

---

## Legal & license

This software is provided **AS IS, without warranty**. Always review automated
changes before relying on them. **Not for safety-critical, legal, medical, or
regulated use without independent review.**

© Sand Castle LLC. All rights reserved. Verbic is licensed, not sold — see
[EULA.txt](EULA.txt) for the full agreement (also shown during install).
