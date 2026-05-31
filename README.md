# Verbic

A Windows system-tray app that quietly fixes your writing in any application — Word, Chrome, Slack, Discord, Notepad, anywhere you can type. Sentence-level grammar suggestions appear inline while you pause; click to apply, keep typing to dismiss.

Three correction engines, switchable any time:

- **AI** (Ollama local, OpenAI, Claude, DeepSeek, Grok, Groq, or any OpenAI-compatible endpoint) — best quality, supports tone changes
- **LanguageTool** (offline, ~5000 grammar rules, requires Java) — no internet, no API key
- **Local Rules** (instant, ~5 ms, fully offline) — capitalization, spacing, punctuation

Published by **Sand Castle LLC**.

---

## Quick start

1. Run `VerbicSetup.exe` — the icon appears in your system tray near the clock.
2. The first launch shows a **Welcome** dialog where you pick the engine.
3. Type anywhere. Either:
   - Press **Ctrl+Shift+G** to fix what you just typed, your selection, or the whole field.
   - Wait for the inline suggestion overlay → click it or press **Ctrl+Space** to apply.

---

## Hotkeys

| Shortcut | Action |
|----------|--------|
| **Ctrl+Shift+G** | Correct typed text / selection / full field |
| **Ctrl+\`** | Same as above (alternate hotkey) |
| **Ctrl+Space** | Apply the suggestion if one is visible — otherwise fix selection / typed text / full field |
| **Click overlay** | Same — apply the suggestion |
| **Double-click tray icon** | Open Settings |
| Keep typing | Dismisses the overlay; new suggestion fires after you pause |

---

## Tray menu

Right-click the tray icon for:

- **Pause / Resume corrections** — temporarily disable everything without quitting
- **Fix Grammar** — spelling, punctuation, grammar (on by default)
- **Formal Tone** / **Casual Tone** — rewrite (AI engine only)
- **Concise** / **Expand** — shorten or elaborate (AI engine only)
- **Auto Suggest (typing)** — silent inline overlay near your caret while typing
- **Switch Engine** — AI / LanguageTool / Local Rules
- **Settings** — full configuration window
- **About** — version, license, hotkeys

The active engine + provider is shown as a dim line in the menu and on the tray-icon hover tooltip.

---

## Correction engines

### AI (default)

Routes through your chosen provider. Best quality, supports all tone toggles, handles surrounding-text context (read silently via Windows UI Automation).

| Provider | API key | Notes |
|----------|:---:|-------|
| **Ollama** (local) | — | Free, runs on your CPU/GPU. Fully offline. Tone changes supported. |
| **OpenAI** | ✓ | gpt-4o-mini, gpt-4o, gpt-4.1-mini |
| **Claude** | ✓ | Sonnet 4, Haiku 4 |
| **DeepSeek** | ✓ | deepseek-chat, deepseek-reasoner |
| **Grok (xAI)** | ✓ | grok-3-mini, grok-3 |
| **Groq** | ✓ | Fast inference, free tier |
| **Custom** | ✓ | Any OpenAI-compatible endpoint |

API key links: [OpenAI](https://platform.openai.com/api-keys) · [Claude](https://console.anthropic.com/settings/keys) · [DeepSeek](https://platform.deepseek.com/api_keys) · [Grok](https://console.x.ai) · [Groq](https://console.groq.com/keys)

### LanguageTool (offline grammar)

The same engine LibreOffice and Firefox use — ~5000 rules, no internet, no API key.

- **Requires Java JRE 11+** (free, https://adoptium.net)
- First use downloads the LanguageTool JAR (~250 MB) into a local cache
- **Tone toggles are not supported** — switch to AI for those
- Settings has a **Refresh** button to re-detect Java after installing it

### Local Rules (instant)

Pure Python, ~5 ms per call:

- Capitalize the first letter of each sentence
- Standalone `i` → `I` (and `i'm`, `i've`, etc.)
- Add space after `.,!?;:` when missing
- Collapse runs of spaces
- Add a trailing period to complete-looking sentences

No grammar AI; tone toggles ignored.

> **Why no silent word-by-word autocorrect?** Verbic follows Grammarly's UX
> principle: never rewrite a word without showing the user first. Silent
> autocorrect (the kind built into mobile keyboards) routinely "fixes" words
> the user typed on purpose, and is twice as annoying as it is helpful.
> Verbic only ever surfaces a suggestion that you explicitly accept.

---

## Using Ollama (free, fully local with tone changes)

1. Install Ollama from https://ollama.com
2. Pull a small instruct model — recommended for grammar:
   ```
   ollama pull llama3.2:3b
   ```
   ~2 GB; runs in ~1 second per correction on most modern CPUs.

   Alternatives: `qwen2.5:7b`, `llama3.1:8b`.

   ⚠ Avoid reasoning models (`deepseek-r1`, `qwq`, `o1`-style) — they spend 30+ seconds "thinking" before answering, which breaks live auto-suggest.
3. Tray → **Settings** → Engine: **AI**, Provider: **Ollama (Local)**.
4. The model dropdown auto-detects what you've pulled — `● installed`, `○ pull required`.
5. Click **Refresh** if you pulled a model after opening Settings.

---

## Settings → Test correction

The Settings dialog has a **Test** field with a sample sentence and a **Run test** button. Type any text, click Run test, and you'll see exactly what the active engine will produce — useful for tuning before saving and going live.

---

## Installation

### Option 1 — Installer (recommended)

Run `VerbicSetup.exe`:

- **Per-user install** — no UAC prompt; installs to `%LOCALAPPDATA%\Programs\Verbic`
- **Optional desktop shortcut** (checkbox during install)
- **Optional auto-start on Windows login** (checkbox during install, off by default)
- **EULA** is shown on the License page; you click Accept to continue
- **Auto-kills** any running Verbic before overwriting the exe (safe re-install)
- Shows up in *Add or Remove Programs* with publisher *Sand Castle LLC*

> **Windows SmartScreen** will warn the first time because the installer isn't yet code-signed. Click **More info** → **Run anyway**.

### Option 2 — Standalone

Just run `Verbic.exe`. No install, no Start-menu shortcut, no auto-start.

### Option 3 — From source

Requires Python 3.10+ on Windows.

```powershell
git clone <repo-url>
cd verbic
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

Produces `dist\Verbic.exe` with publisher metadata embedded (CompanyName: Sand Castle LLC).

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

If something seems wrong, set `GRAMMAR_DEBUG=1` before launching to write a log to `%TEMP%\verbic.log`:

```powershell
$env:GRAMMAR_DEBUG="1"
.\dist\Verbic.exe
```

The log shows engine choice, suggest-thread lifecycle, focus changes, and autofix decisions.

---

## Project layout

```
verbic/
├── main.py                 # entry point; redirects stdout/stderr in --noconsole builds
├── tray_app.py             # tray icon + orchestration
├── keyboard_monitor.py     # global hotkeys, typing buffer, word-boundary detection
├── focus_watcher.py        # SetWinEventHook to react to foreground-window changes
├── suggestion_window.py    # inline auto-suggest overlay (frameless, non-focus-stealing)
├── welcome_window.py       # first-run welcome / engine picker
├── settings_window.py      # full configuration UI with Test correction
├── text_replacer.py        # ctypes clipboard + Shift+Left / Ctrl+A injection
├── text_reader.py          # reads focused field via Windows UI Automation
├── prompt_builder.py       # constructs LLM prompts from active toggles + context
├── ollama_client.py        # Ollama HTTP client + status/list-models + warm-up
├── openai_client.py        # OpenAI-compatible client (also DeepSeek, Grok, Groq, Custom)
├── claude_client.py        # Anthropic API client
├── languagetool_client.py  # offline grammar via language_tool_python (requires Java)
├── sentence_formatter.py   # pure-Python rule-based formatter
├── text_utils.py           # response cleanup (<think> stripping, quote unwrapping)
├── debug_log.py            # opt-in diagnostic logger (GRAMMAR_DEBUG=1)
├── config.py               # engine + provider catalog + persistent settings (config.json)
├── build.py                # PyInstaller build with embedded version info
├── installer.iss           # Inno Setup script
├── version_info.txt        # Windows EXE metadata (Sand Castle LLC)
├── EULA.txt                # end-user license agreement (bundled with installer)
├── PRIVACY.md              # privacy policy stub for the website
├── tests/                  # unit tests
└── icon.png / icon.ico     # V app icon
```

---

## Troubleshooting

| Problem | Try |
|---|---|
| No suggestion overlay appears | Tray → confirm **Auto Suggest (typing)** is checked. The threshold is ≥20 chars ending in `.!?`, or ≥40 chars otherwise. |
| Auto-suggest with Ollama feels slow | Use a small instruct model (`llama3.2:3b`). Reasoning models like `deepseek-r1` take 30+s. |
| Settings won't open | Tray icon → right-click → Settings. Or double-click the tray icon. Window comes to front automatically. |
| Overlay shows but Ctrl+Space does nothing | Click the overlay instead. If neither works, the global keyboard hook may have been intercepted — quit and relaunch. |
| LanguageTool says "Java not found" after installing Java | In Settings (LanguageTool engine selected) click **Refresh**. Verbic re-detects Java in `Program Files\Eclipse Adoptium\*` and updates PATH for the running process. |
| LanguageTool says "NoneType has no attribute 'write'" | You're on an old build. Reinstall — main.py now redirects stdout/stderr in --noconsole mode. |
| Antivirus flags the app | The global keyboard hook (pynput) is the same mechanism used by AutoHotkey and text expanders. Add an exception for `Verbic.exe`. |
| Settings opened twice on double-click | Fixed in current build (single-instance guard). |

---

## Performance

| Operation | Latency |
|---|---|
| Local Rules engine | ~5 ms |
| LanguageTool engine | 50–300 ms |
| AI · Ollama (small model, warm) | ~1 s |
| AI · cloud (OpenAI / Claude / etc.) | ~1–2 s |
| Sentence replacement injection | ~200–300 ms (ctypes clipboard, no subprocess) |

---

## Privacy

- Sand Castle LLC operates **no servers** that receive your text. The app runs entirely on your machine.
- The **AI engine** sends your typed/selected text to whichever provider you configure (Ollama is local; everyone else is cloud). Each provider has its own privacy policy — review it before sending sensitive content.
- The **LanguageTool** and **Local Rules** engines never send your text anywhere.
- API keys are stored locally in `config.json`, never transmitted by Verbic.
- See [PRIVACY.md](PRIVACY.md) for the full policy.

---

## Legal

This software is provided **AS IS, without warranty**. Always review automated changes before relying on them. **Not for safety-critical, legal, medical, or regulated use without independent review.**

See [EULA.txt](EULA.txt) for the full agreement (also shown during install).

---

## Requirements

- Windows 10 or 11
- For cloud LLMs: an internet connection and a valid API key
- For local LLM: [Ollama](https://ollama.com) running, with at least one model pulled
- For LanguageTool: [Java JRE 11+](https://adoptium.net)

---

## License

© Sand Castle LLC. All rights reserved. Verbic is licensed, not sold — see [EULA.txt](EULA.txt).
