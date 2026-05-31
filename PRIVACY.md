# Verbic Privacy Policy

**Effective:** _(set this to your launch date)_
**Last updated:** _(set this to your launch date)_

This Privacy Policy explains what information the Verbic desktop application
("Verbic", "we", "us", "our"), published by **Sand Castle LLC**, processes
when you use the Software, and what we do (and don't do) with it.

This policy is a starting template. Have a privacy lawyer review it before
your first paid customer.

---

## 1. Summary in plain English

- We do not run any servers that receive your text. The Verbic application
  runs entirely on your computer.
- When you choose an AI provider (Ollama / OpenAI / Claude / DeepSeek /
  Grok / Groq / a custom OpenAI-compatible endpoint), the application
  sends the text you have typed or selected to **that provider** so they
  can return a corrected version. Sand Castle never sees the contents of
  what you type.
- When the **LanguageTool** offline engine is selected, your text never
  leaves your computer.
- When the **Local Rules** engine is selected, your text never leaves
  your computer.
- We do not collect telemetry, analytics, or crash reports from the
  application.

---

## 2. What information the app handles

| Data | Where it goes | Why |
|------|---------------|-----|
| **Text you type or select** | Sent to the AI provider you chose, *only* if that engine is active. Stays on your device for LanguageTool / Local Rules / spell-check. | To produce a corrected version. |
| **Surrounding text in the focused field** (read via Windows UI Automation) | Same as above — sent only to your chosen AI provider as context, only when AI engine is active. | To make corrections fit the surrounding tone/topic. |
| **Settings** (provider choice, model, API keys, toggle states) | Stored locally in `config.json` next to the application binary. Never transmitted by Verbic. | To remember your preferences. |
| **Log file** (`verbic.log` in `%TEMP%`) | Stored locally; only written when the `GRAMMAR_DEBUG` environment variable is set. Used for debugging. | Optional, off by default. |

---

## 3. Third-party AI providers

If you select an AI provider, the text you type or select will be
transmitted to that provider for processing. Each provider has its own
privacy practices; please review them before configuring Verbic with
sensitive content:

- **OpenAI** — https://openai.com/privacy
- **Anthropic (Claude)** — https://www.anthropic.com/legal/privacy
- **DeepSeek** — https://www.deepseek.com/privacy
- **xAI (Grok)** — https://x.ai/legal/privacy-policy
- **Groq** — https://groq.com/privacy-policy
- **Ollama** — runs locally on your computer; no third party.

API keys you enter for these providers are stored locally in
`config.json` and only used to authenticate your requests to the
respective provider's API.

---

## 4. What Sand Castle does NOT collect

- We do not run an analytics or telemetry server.
- We do not collect crash reports automatically.
- We do not collect usage statistics.
- We do not collect your text.
- We do not have access to your API keys.

If a future version of Verbic introduces optional analytics, this policy
will be updated and existing users will be notified.

---

## 5. Children's privacy

Verbic is not directed to children under 13. We do not knowingly process
information from children under 13.

---

## 6. International users

Sand Castle LLC is based in the United States. If you use Verbic from
outside the US, the third-party AI providers you configure may transfer
your data to and from the US under their own data-transfer agreements.

---

## 7. Your rights

Because Sand Castle does not collect or store your data, there is
generally nothing for us to delete or export on request. For data held
by your chosen third-party AI provider, please contact that provider
directly.

---

## 8. Changes

We may update this Privacy Policy from time to time. Material changes
will be posted at the same URL where you accessed this version, with
an updated effective date.

---

## 9. Contact

Questions about this Policy can be sent to the contact email listed on
the Sand Castle LLC website.

© Sand Castle LLC.
