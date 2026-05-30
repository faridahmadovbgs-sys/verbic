"""All grammar / tone engines in one file for the Mac Lite build.

Ports of the Windows clients but stripped to the bare correction call so
the Mac entry point is a single import.
"""
import requests
from typing import Optional


# ---------- OpenAI-compatible (covers OpenAI, DeepSeek, Groq, Ollama, custom) ----------

class OpenAICompatClient:
    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def correct(self, text: str, system_prompt: str, timeout: float = 12.0) -> Optional[str]:
        if not text.strip():
            return text
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.2,
                },
                timeout=timeout,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None


# ---------- Anthropic (Claude) ----------

class ClaudeClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def correct(self, text: str, system_prompt: str, timeout: float = 12.0) -> Optional[str]:
        if not text.strip():
            return text
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 2048,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": text}],
                },
                timeout=timeout,
            )
            r.raise_for_status()
            data = r.json()
            blocks = data.get("content", [])
            return "".join(b.get("text", "") for b in blocks).strip() or None
        except Exception:
            return None


# ---------- Prompt builder for the AI engine ----------

def build_system_prompt(options: dict) -> str:
    from config import TONE_PROMPTS
    parts = ["You are an editor. Rewrite the user's text to fix grammar, punctuation, spelling, and word choice."]
    # Tones are mutually exclusive in the UI; emit whichever is enabled.
    for key, prompt in TONE_PROMPTS.items():
        if options.get(key):
            parts.append(prompt)
            break
    if options.get("expand"):
        parts.append("Expand short phrases into complete sentences without changing meaning.")
    parts.append("Preserve the user's intent and meaning exactly.")
    parts.append("Reply with ONLY the corrected text — no explanations, no quotes, no preamble.")
    return " ".join(parts)


# ---------- Factory ----------

def make_engine(cfg: dict):
    """Return an object with a .correct(text, system_prompt) interface for the
    configured AI provider (offline engines were removed)."""
    provider_name = cfg.get("provider", "ollama")
    provider_cfg = cfg.get("providers", {}).get(provider_name, {})
    model = provider_cfg.get("model") or ""
    api_key = provider_cfg.get("api_key") or ""
    base_url = provider_cfg.get("base_url") or ""
    if provider_name == "anthropic":
        return ClaudeClient(api_key=api_key, model=model)
    return OpenAICompatClient(api_key=api_key, model=model, base_url=base_url)
