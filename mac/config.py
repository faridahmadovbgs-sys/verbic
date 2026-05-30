"""Per-user config for Verbic Mac Lite.

Stored at ~/Library/Application Support/Verbic/config.json so it persists
across reinstalls and isn't bundled with the .app.
"""
import json
import os
from copy import deepcopy

APP_NAME = "Verbic"

PROVIDERS = {
    "ollama": {
        "label": "Ollama (local)",
        "default_model": "llama3.1:8b",
        "base_url": "http://localhost:11434/v1",
        "needs_api_key": False,
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "needs_api_key": True,
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "default_model": "claude-sonnet-4-20250514",
        "base_url": "https://api.anthropic.com/v1",
        "needs_api_key": True,
    },
    "deepseek": {
        "label": "DeepSeek",
        "default_model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "needs_api_key": True,
    },
    "groq": {
        "label": "Groq",
        "default_model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "needs_api_key": True,
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "default_model": "",
        "base_url": "",
        "needs_api_key": True,
    },
}

# Tones the user can pick from the menu-bar "Tone" submenu. Mutually exclusive;
# each maps to a one-line instruction injected into the AI system prompt.
TONES = [
    ("formal", "Formal", "Use a formal, professional tone."),
    ("casual", "Casual", "Use a casual, friendly tone."),
    ("professional", "Professional", "Use a polished, workplace-appropriate professional tone."),
    ("friendly", "Friendly", "Use a warm, approachable, friendly tone."),
    ("confident", "Confident", "Use a confident, assertive tone; prefer direct statements over hedging."),
    ("concise", "Concise", "Make it as concise as possible; cut filler while preserving meaning."),
    ("persuasive", "Persuasive", "Use a persuasive, compelling tone."),
    ("empathetic", "Empathetic", "Use a kind, empathetic, understanding tone."),
    ("academic", "Academic", "Use a precise, scholarly, academic tone."),
    ("playful", "Playful", "Use a fun, playful, lighthearted tone."),
]
TONE_KEYS = [k for k, _l, _p in TONES]
TONE_PROMPTS = {k: p for k, _l, p in TONES}

# Verbic runs exclusively on the configured AI provider (offline engines
# removed). ENGINES kept as a single entry so stale configs normalize cleanly.
ENGINES = {
    "ai": {"label": "AI (Provider configured below)"},
}

DEFAULT_OPTIONS = {
    "grammar": True,
    **{k: False for k in TONE_KEYS},
    "expand": False,
}

DEFAULT_ENGINE = "ai"


def config_dir() -> str:
    base = os.path.expanduser("~/Library/Application Support")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def default_config() -> dict:
    return {
        "engine": DEFAULT_ENGINE,
        "provider": "ollama",
        "options": dict(DEFAULT_OPTIONS),
        "providers": {
            name: {"model": info["default_model"], "api_key": "", "base_url": info["base_url"]}
            for name, info in PROVIDERS.items()
        },
    }


def load_config() -> dict:
    path = config_path()
    defaults = default_config()
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return defaults
    cfg = _merge(defaults, data)
    # Normalize any stale offline engine ("rules"/"languagetool") to AI.
    if cfg.get("engine") not in ENGINES:
        cfg["engine"] = DEFAULT_ENGINE
    return cfg


def save_config(cfg: dict) -> None:
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def _merge(defaults: dict, override: dict) -> dict:
    out = deepcopy(defaults)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out
