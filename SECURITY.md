# Verbic — Security & Data Handling

Publisher: **Sand Castle LLC**  ·  Application: **Verbic** (Windows desktop, system-tray)
Purpose: an AI writing assistant — grammar/spelling correction, tone rewriting,
and drafting — that the user invokes while typing in other applications.

This document answers the standard questions a security team asks about a
developer-built tool that connects to external AI services.

---

## Install & file locations (no user-space / Temp execution)

| What | Location |
|------|----------|
| Application binaries | `C:\Program Files\Verbic\` (all-users install, requires admin/UAC) |
| Runtime DLLs | `C:\Program Files\Verbic\_internal\` (PyInstaller `--onedir`; **no per-launch Temp extraction**) |
| User settings (incl. API key) | `%APPDATA%\Verbic\config.json` |
| Opt-in diagnostic log | `%APPDATA%\Verbic\Logs\verbic.log` (only when `GRAMMAR_DEBUG=1`) |
| Downloaded installer (manual update) | `%LOCALAPPDATA%\Verbic\Updates\` |

The application is built `--onedir`, so it runs directly from the install
folder. It does **not** unpack or execute from `AppData\Local\Temp` or any
random staging directory.

---

## Network destinations (FQDNs)

Verbic contacts only the destinations below. There is **no telemetry or
analytics**, and no data is sent to any Sand Castle server beyond the version
check described.

| Destination | When | Why | Data sent | Auth |
|-------------|------|-----|-----------|------|
| **Your chosen AI provider** — one of: `api.openai.com`, `api.anthropic.com`, `api.deepseek.com`, `api.x.ai`, `api.groq.com`, a custom OpenAI-compatible endpoint, **or** `http://localhost:11434` (Ollama, fully local) | Only on an explicit user action (typing pause with auto-suggest on, a hotkey, or a toolbar button) | To perform the requested correction / rewrite / draft | The text the user is editing (typed or selected) + the instruction | The user's own API key, sent as `Authorization: Bearer …` / `x-api-key` to that provider only. Ollama is local and needs no key. |
| `www.skyscrum.com/api/verbic-version/` | Once, ~12 s after launch, and on a manual "Check for Updates" | Compare the running version to the latest release | None (simple GET) | None |
| `www.skyscrum.com/api/downloads/verbic/` | Only when the user explicitly chooses to install an update | Download the signed installer for the new version | None (simple GET) | None |

All requests send a clear, attributable user agent: **`Verbic/<version>`**
(e.g. `Verbic/1.2.3`).

Only **one** AI provider is ever contacted — whichever the user configured in
Settings. If the user selects **Ollama**, no external AI calls are made at all
(inference runs locally).

---

## Data handling

- **What leaves the machine for AI:** the specific snippet the user is editing
  (the current sentence, a selection, or a typed buffer) plus the fixed
  instruction (e.g. "fix grammar"). Nothing else from the screen or other apps.
- **When:** only on a deliberate user action. Verbic does **not** scrape the
  screen, read other windows, or send data on a timer.
- **API keys:** stored locally in `%APPDATA%\Verbic\config.json` and used only
  as the auth header to the user's chosen provider. They are never sent to
  Sand Castle or logged.
- **No telemetry / no PHI collection by Verbic:** Sand Castle operates no
  servers that receive user text. The only Sand Castle endpoint contacted is
  the version check, which sends no user data.
- **Governance note for regulated environments:** Verbic forwards whatever text
  the user edits to the configured cloud provider. Users must not process PHI,
  customer data, credentials, or other regulated/internal content through a
  cloud provider unless that provider and use are approved by data-governance
  review. For zero external egress, configure **Ollama** (local) — then no text
  ever leaves the device.
- **Disabling external AI:** choosing the **Ollama** provider keeps everything
  local. The tray **Pause** action stops all corrections entirely.

---

## Logging

- Off by default; enabled only with the environment variable `GRAMMAR_DEBUG=1`.
- Writes to `%APPDATA%\Verbic\Logs\verbic.log`.
- Contains **non-sensitive metadata only** — scopes, decisions, and text
  *lengths*. It never records API keys, prompt contents, selected/typed text,
  or full request/response payloads.

---

## Updates

- **No silent self-update.** At startup Verbic performs one attributable
  version check and, if a newer version exists, shows a notification. It does
  **not** download or install anything on its own.
- Installation happens only when the user explicitly chooses **Check for
  Updates** from the tray menu.
- Each release is published on GitHub with its installer and SHA-256 hash, so
  Security can pin/allowlist specific versions:
  `https://github.com/faridahmadovbgs-sys/verbic/releases`

---

## Code signing

Code-signing of `VerbicSetup.exe` and `Verbic.exe` with a reputable
(OV/EV) certificate for Sand Castle LLC is planned; the installer build is
wired to sign once the certificate is in place (`installer.iss` SignTool hook).

---

## Quick answers for review

- **What domains?** The one configured AI provider, plus `www.skyscrum.com` for
  version check / installer download.
- **Why?** AI corrections (user-initiated) and update checks.
- **What data is sent?** Only the text the user is actively editing, to the
  chosen AI provider. Nothing to SkyScrum but a version GET.
- **Any WellSky/customer data, PHI, credentials, source code?** Not by design —
  only what the user explicitly submits for correction. Use Ollama (local) to
  guarantee no egress.
- **Auth?** The user's own provider API key. SkyScrum endpoints are unauthenticated GETs.
- **Logged?** Only opt-in, metadata-only.
- **Can destinations be restricted?** Yes — pick one provider, or Ollama for
  fully local. The full FQDN list is above.
