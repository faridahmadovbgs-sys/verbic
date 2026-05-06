import json
import os
import sys

PROVIDERS = {
    "ollama": {
        "label": "Ollama (Local)",
        "default_model": "llama3.1:8b",
        "models": ["llama3.2:3b", "llama3.1:8b", "llama3.1:70b", "mistral", "gemma2"],
        "needs_api_key": False,
        "base_url": None,
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-nano", "gpt-4.1-mini"],
        "needs_api_key": True,
        "base_url": "https://api.openai.com/v1",
    },
    "claude": {
        "label": "Claude (Anthropic)",
        "default_model": "claude-sonnet-4-20250514",
        "models": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
        "needs_api_key": True,
        "base_url": "https://api.anthropic.com",
    },
    "deepseek": {
        "label": "DeepSeek",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "needs_api_key": True,
        "base_url": "https://api.deepseek.com/v1",
    },
    "grok": {
        "label": "Grok (xAI)",
        "default_model": "grok-3-mini",
        "models": ["grok-3-mini", "grok-3"],
        "needs_api_key": True,
        "base_url": "https://api.x.ai/v1",
    },
    "groq": {
        "label": "Groq",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "needs_api_key": True,
        "base_url": "https://api.groq.com/openai/v1",
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "default_model": "",
        "models": [],
        "needs_api_key": True,
        "base_url": "",
    },
}

PROVIDER_NAMES = list(PROVIDERS.keys())


def _config_path():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")


def _default_config():
    return {
        "provider": "ollama",
        "providers": {
            name: {"model": info["default_model"], "api_key": "", "base_url": info["base_url"] or ""}
            for name, info in PROVIDERS.items()
        },
    }


def load_config():
    path = _config_path()
    defaults = _default_config()
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "providers" not in data:
            data = _migrate_old_config(data)
        for name in PROVIDERS:
            if name not in data.get("providers", {}):
                data["providers"][name] = defaults["providers"][name]
        return data
    except Exception:
        return defaults


def _migrate_old_config(old):
    config = _default_config()
    config["provider"] = old.get("provider", "ollama")
    if old.get("ollama_model"):
        config["providers"]["ollama"]["model"] = old["ollama_model"]
    if old.get("openai_model"):
        config["providers"]["openai"]["model"] = old["openai_model"]
    if old.get("api_key"):
        config["providers"]["openai"]["api_key"] = old["api_key"]
    return config


def save_config(config):
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass
