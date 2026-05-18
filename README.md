# Grammar Tool

A Windows system tray app that corrects grammar and rewrites text in any application — Word, Chrome, Slack, Discord, Notepad, you name it. Powered by your choice of local Ollama or cloud LLM (OpenAI, Claude, DeepSeek, Grok, Groq).

Published by **Sand Castle LLC**.

---

## Quick start

1. Run `GrammarToolSetup.exe` (or `GrammarTool.exe` if you have the standalone) — the icon appears in your system tray near the clock.
2. Right-click the tray icon → **Settings** → pick a provider and model → **Save**.
3. Type anywhere. Either:
   - Press **Ctrl+Shift+G** to correct what you just typed (or your selection / the whole field), or
   - Wait for the inline yellow suggestion overlay → click it or press **Ctrl+Tab** to apply.

---

## Hotkeys

| Shortcut | Action |
|----------|--------|
| **Ctrl+Shift+G** | Correct typed text / current selection / full field |
| **Ctrl+\`** | Same as above (alternate hotkey) |
| **Ctrl+Tab** | Apply the inline auto-suggest overlay |
| **Click overlay** | Same — apply the suggestion |
| Keep typing | Dismisses the overlay; new suggestion fires after you pause |

---

## Features

Toggle via right-click on the tray icon:

- **Fix Grammar** — spelling, punctuation, grammar (on by default)
- **Formal Tone** — rewrite in professional language
- **Casual Tone** — rewrite in friendly, conversational style
- **Concise** — shorten while keeping meaning
- **Expand** — add detail and elaboration
- **Auto Suggest (typing)** — silent inline overlay near your caret while typing

The auto-suggest overlay reads the surrounding document via Windows UI Automation (Word, Chrome, Slack, VS Code, etc.) and uses it as context, so suggestions match the tone of what's already on the page.

---

## Supported AI providers

| Provider | API key | Notes |
|----------|:---:|-------|
| **Ollama (local)** | — | Free, runs on your CPU/GPU. Requires [Ollama](https://ollama.com). |
| OpenAI | ✓ | gpt-4o-mini, gpt-4o, gpt-4.1-mini |
| Claude | ✓ | Sonnet 4, Haiku 4 |
| DeepSeek | ✓ | deepseek-chat, deepseek-reasoner |
| Grok (xAI) | ✓ | grok-3-mini, grok-3 |
| Groq | ✓ | Fast inference, free tier |
| Custom | ✓ | Any OpenAI-compatible endpoint |

### Where to get API keys

| Provider | Link |
|----------|------|
| OpenAI | https://platform.openai.com/api-keys |
| Claude | https://console.anthropic.com/settings/keys |
| DeepSeek | https://platform.deepseek.com/api_keys |
| Grok | https://console.x.ai |
| Groq | https://console.groq.com/keys |

---

## Using Ollama (free, fully local)

1. Install Ollama from https://ollama.com
2. Pull a model — recommended for grammar correction:
   ```
   ollama pull llama3.2:3b
   ```
   (~2 GB; runs in ~1 second per correction on most modern CPUs)

   Heavier alternatives: `qwen2.5:7b`, `llama3.1:8b`.

   ⚠ Avoid reasoning models (`deepseek-r1`, `qwq`, `o1`-style) — they take 30+ seconds and break live auto-suggest.
3. Right-click the tray icon → **Settings** → Provider: **Ollama (Local)**.
4. The model dropdown auto-detects what you've pulled (● installed, ○ pull-required). Pick one → **Save**.

---

## Installation

### Option 1 — Installer (recommended)

Run **GrammarToolSetup.exe**:

- Per-user install (no UAC prompt)
- Optional desktop shortcut
- Optional auto-start on Windows login
- Shows up in *Add or Remove Programs* with publisher *Sand Castle LLC*

> **Windows SmartScreen warning**: the installer is not yet code-signed, so the first time you run it Windows shows *"Windows protected your PC"*. Click **More info** → **Run anyway**.

### Option 2 — Standalone

Just run `GrammarTool.exe`. No installation. No shortcuts created.

### Option 3 — From source (development)

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

Produces `dist\GrammarTool.exe` with version info embedded (CompanyName: Sand Castle LLC).

### Build the installer

Requires [Inno Setup 6](https://jrsoftware.org/isdl.php).

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Or open `installer.iss` in the Inno Setup Compiler and press **F9**.

Output: `installer_output\GrammarToolSetup.exe`.

### Run tests

```powershell
python -m pytest tests\ -q
```

---

## Project layout

```
grammar-tool/
├── main.py                 # entry point
├── tray_app.py             # tray icon + orchestration
├── keyboard_monitor.py     # global hotkeys + typing buffer
├── suggestion_window.py    # inline auto-suggest overlay
├── settings_window.py      # provider/model/key configuration UI
├── text_replacer.py        # injects corrected text via Shift+Left + paste / Ctrl+A + paste
├── text_reader.py          # reads focused field via Windows UI Automation
├── prompt_builder.py       # constructs LLM prompts from active toggles + context
├── ollama_client.py        # Ollama HTTP client + status/list-models helpers
├── openai_client.py        # OpenAI-compatible client (also DeepSeek, Grok, Groq, Custom)
├── claude_client.py        # Anthropic API client
├── text_utils.py           # response cleanup (<think> stripping, quote unwrapping)
├── config.py               # provider catalog + persistent settings (config.json)
├── build.py                # PyInstaller build with embedded version info
├── installer.iss           # Inno Setup script
├── version_info.txt        # Windows EXE metadata
├── tests/                  # unit tests
└── icon.png / icon.ico     # tray icon
```

---

## Troubleshooting

- **No suggestion overlay appears.** Make sure the active provider is reachable: in Settings, the Ollama section shows status. For cloud providers, verify the API key. The tool also requires sentences ≥20 chars ending in `.`, `!`, `?`, or ≥40 chars otherwise before triggering.
- **Auto-suggest with Ollama feels slow.** Use a small instruct model (`llama3.2:3b`). Reasoning models like `deepseek-r1` are too slow for live suggestions.
- **Overlay shows but Ctrl+Tab does nothing.** Click the overlay instead — clicking always works. If neither works, the global keyboard hook may have been blocked by another app; restart the tray.
- **Antivirus warning.** The app uses a global keyboard hook (`pynput`) for hotkeys, which AVs sometimes flag heuristically. Add an exception for `GrammarTool.exe`.
- **Replacement adds text instead of replacing.** This was a known bug with reasoning models that returned `<think>` blocks; the tool now strips them. If it still happens, ensure you're on the latest build.

---

## Requirements

- Windows 10 or 11
- For cloud LLMs: an internet connection and a valid API key
- For local LLM: [Ollama](https://ollama.com) running, with at least one model pulled

---

## License

© Sand Castle LLC. All rights reserved.
