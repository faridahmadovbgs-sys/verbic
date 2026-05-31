# Verbic for macOS — architecture plan

## Goal

Port Verbic's inline-correction experience to macOS without compromising the
core UX: a tray-resident app that reads the focused text control's contents,
asks one of the configured grammar engines to fix it, and writes the result
back — all triggered by a single global hotkey or an auto-overlay while the
user pauses.

## What stays the same (free reuse)

The grammar engines themselves are pure Python over HTTP and have no OS
dependencies. These modules port unmodified:

  - `openai_client.py` — any OpenAI-compatible endpoint (OpenAI, DeepSeek,
    Grok, Groq, custom)
  - `claude_client.py`
  - `ollama_client.py`
  - `languagetool_client.py`
  - `prompt_builder.py`
  - `text_utils.py`
  - `config.py` (with the storage location swapped to
    `~/Library/Application Support/Verbic/config.json`)
  - `debug_log.py`

## What has to be replaced (the hard part)

The Windows version leans on three Win32 surfaces. Each needs a macOS
equivalent.

### 1. Tray icon + menu

| Windows | macOS replacement |
|---|---|
| `pystray` + `Pillow` | **`rumps`** — purpose-built statusbar framework. Much cleaner. |

Effort: ~1 day. Mostly aesthetic — re-implement the existing menu items.

### 2. Global hotkey + focus tracking

| Windows | macOS replacement |
|---|---|
| `pynput.keyboard.Listener` raw | `pynput` works on macOS too **but requires Accessibility permission** in System Settings → Privacy & Security → Accessibility. Alternative: the Quartz Event Tap API via `pyobjc`. |
| `SetWinEventHook` (focus changes) | `NSWorkspace` notification `NSWorkspaceDidActivateApplicationNotification` via `pyobjc`. |

Effort: ~2–3 days. The permission prompt + first-run guidance is the
fiddly bit.

### 3. Read & write focused control text  ⚠️ HIGH RISK

This is the core of Verbic, and it's where the Windows port carries the
most asymmetry.

| Windows                              | macOS replacement                                  |
|--------------------------------------|-----------------------------------------------------|
| `uiautomation` (UIA, COM-backed)     | **NSAccessibility (AX) API** via `pyobjc`           |
| `GetValuePattern()`                  | `AXUIElementCopyAttributeValue(_, kAXValueAttribute)` |
| `SetValuePattern().SetValue(text)`   | `AXUIElementSetAttributeValue(_, kAXValueAttribute, text)` |
| `TextPattern.Selection`              | `AXSelectedTextRange` + `AXSelectedText`            |
| UIA caret offset                     | Read `AXSelectedTextRange` location                 |

The pain points:

- **No clean Python wrapper exists.** You write directly against `pyobjc`
  with raw AX function calls. Helper layers like
  [`atomacos`](https://pypi.org/project/atomacos/) exist but are dated and
  geared at test automation, not in-app correction.
- **App cooperation is uneven.** Native Cocoa apps with `NSTextView`
  expose AX cleanly. Electron apps (VS Code, Slack desktop, Discord) need
  `--enable-accessibility` and even then expose only partial trees. Web
  browsers expose Chromium's accessibility tree which is rich but moves
  the read/write to ARIA-style attributes rather than direct value
  replacement.
- **Permission UX is severe.** First launch must prompt the user to grant
  Accessibility permission, and the app **has to restart** for the
  permission to take effect. macOS shows a system dialog you can't
  bypass. Document this clearly in onboarding.
- **Reading vs writing parity differs by app.** Some apps that expose
  text reads refuse value writes. The fallback is the same one any other
  Mac grammar tool uses: simulate Cmd+A to select, Cmd+V to paste the
  corrected text. Less elegant but bulletproof.

Effort: ~1 week for the happy-path UIA equivalent + ~3 days for the
clipboard-fallback path + 2 days hardening across the major apps.

### 4. Notifications

| Windows | macOS replacement |
|---|---|
| `win10toast` | **`pync`** (wraps `terminal-notifier`) or `rumps.notification()` |

Effort: trivial.

### 5. Suggestion overlay window

The Windows version uses a frameless Tk window positioned at the caret. On
macOS, Tk windows look out of place. Two choices:

  - **Reuse Tk** — keep code closer to the Windows version, accept the
    aesthetic mismatch.
  - **Rewrite with `pyobjc`** — `NSWindow` with `NSPanel` styling for a
    proper popover that follows macOS conventions.

Effort: ~3 days for the pyobjc version. ~0 for Tk reuse.

## Packaging

  - `py2app` for `.app` bundles, or `PyInstaller --onedir --windowed`.
  - `Info.plist` entries:
    - `NSAccessibilityUsageDescription` (mandatory for permission prompt)
    - `LSUIElement = true` (hide from Dock — tray-only app)
  - Code signing requires an Apple Developer account ($99/year). Without
    it: users right-click → Open the first time to bypass Gatekeeper.
  - Notarization requires the same paid account.

## Effort estimate

| Path                              | Estimate          |
|-----------------------------------|-------------------|
| Verbic-Mac Lite (clipboard only)  | **2–3 days**      |
| Full Verbic-Mac (AX read + write) | **2–3 weeks**     |
| Verbic-Mac with feature parity    | **3–4 weeks**     |

## Recommendation

Ship Lite first. It validates the engine plumbing on macOS, gets users
something useful while you build the AX layer, and avoids gating the
launch on the highest-risk module.
