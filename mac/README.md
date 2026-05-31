# Verbic Mac Lite

Clipboard-based grammar / tone fixes for macOS. A tray app that lets you
correct any text by copying it, pressing a hotkey, and pasting the result.
No inline overlay yet — that comes in the full Verbic-Mac port (see
`../VERBIC-MAC-PLAN.md`).

## Why "Lite"

The full Windows Verbic reads and writes the focused control directly via
UI Automation. The macOS equivalent (NSAccessibility) needs a lot more
plumbing and a system-level Accessibility permission. The Lite version
skips all of that — it works the same way as built-in macOS Services:
**copy → hotkey → paste**.

## Features

- 🔁 Three correction engines, switchable from the tray menu:
  - **AI** — OpenAI, Claude, DeepSeek, Grok, Groq, custom endpoints, or
    a local Ollama model
  - **LanguageTool** — offline, ~5,000 grammar rules, needs Java
  - **Local Rules** — instant, fully offline, fixes capitalization,
    spacing, punctuation
- ⌨️ Global hotkey **Cmd+Shift+G** — copy text, press hotkey, copy what
  comes out
- 🎚️ Tone toggles (Formal / Casual / Expand) for the AI engine
- 🔒 Settings & API keys live in `~/Library/Application Support/Verbic/`
  and never leave your machine except as part of the API call to your
  chosen provider

## First-time setup

```bash
# 1. Install Python 3.10+ (the system Python on recent macOS works)
python3 --version

# 2. Install dependencies
cd ~/Git/grammar-tool/mac
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. (Optional) install Java if you want the LanguageTool engine
brew install openjdk

# 4. (Optional) install Ollama if you want a local LLM
brew install ollama
ollama pull llama3.1:8b

# 5. Run it
python3 main.py
```

A Verbic icon appears in the menu bar. Right-click → Settings to enter
your API key (if using the AI engine).

## Granting Accessibility permission

`pynput` listens for the global hotkey. macOS requires Accessibility
permission for that:

1. The first time you press Cmd+Shift+G, macOS shows a dialog asking
   for permission.
2. Click **Open System Settings**.
3. Toggle **Verbic** (or `Python.app`/`Terminal` if you ran it from
   there) ON in Privacy & Security → Accessibility.
4. Restart the app.

If you don't see the dialog, open System Settings → Privacy & Security
→ Accessibility manually and add Verbic.

## Hotkeys

| Key combo            | Action                                         |
|----------------------|-----------------------------------------------|
| `⌘ + ⇧ + G`          | Fix the current clipboard contents in place    |
| (tray menu)          | Same as above, plus engine / settings access   |

## Packaging into a .app

```bash
pip install pyinstaller
pyinstaller --windowed --name Verbic --osx-bundle-identifier com.fhintegrant.verbic main.py
# Output: dist/Verbic.app
```

For distribution outside your own machine you'll need to either:

- Ship unsigned (`right-click → Open` to bypass Gatekeeper), or
- Sign + notarize with an Apple Developer account ($99/year).

## Status

This Lite version is the seed for the full Verbic-Mac. See
`../VERBIC-MAC-PLAN.md` for the architecture plan and effort estimate for
the inline-overlay version.
