import json
import os
import sys

PROVIDERS = {
    "ollama": {
        "label": "Ollama (Local)",
        # Default to the fastest small model so live inline suggestions feel
        # instant. llama3.2:1b (~1.3 GB) handles grammar/tone in well under a
        # second on most CPUs; larger models are slower per correction.
        "default_model": "llama3.2:1b",
        # Ordered fastest → most capable.
        "models": ["llama3.2:1b", "qwen2.5:1.5b", "gemma2:2b", "llama3.2:3b",
                   "qwen2.5:7b", "llama3.1:8b", "mistral"],
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


def _config_dir():
    # User settings live in %APPDATA%\Verbic — a per-user data location that
    # app updates never touch. (They used to sit next to the executable, in the
    # install folder, which the installer rewrites on update — wiping the saved
    # API key. See _legacy_config_path + the migration in load_config.)
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") \
        or os.path.expanduser("~")
    return os.path.join(base, "Verbic")


def _config_path():
    return os.path.join(_config_dir(), "config.json")


def _legacy_config_path():
    """Old pre-1.2.2 location: next to the executable (frozen) or source file.
    Read once for migration so existing users keep their settings."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")


# Tone rewrites the user can pick from the tray "Tone" submenu. They are
# mutually exclusive with each other; "grammar" and "expand" are independent
# options. Each tone maps to a one-line instruction injected into the AI prompt
# (see prompt_builder + TONE_PROMPTS below).
TONES = [
    ("formal", "Formal", "Rewrite in a formal, professional tone."),
    ("casual", "Casual", "Rewrite in a casual, friendly, conversational tone."),
    ("professional", "Professional", "Rewrite in a polished, workplace-appropriate professional tone."),
    ("friendly", "Friendly", "Rewrite in a warm, approachable, friendly tone."),
    ("confident", "Confident", "Rewrite in a confident, assertive tone; prefer direct statements over hedging."),
    ("concise", "Concise", "Make it as concise as possible; cut filler and redundancy while preserving the meaning."),
    ("persuasive", "Persuasive", "Rewrite in a persuasive, compelling tone."),
    ("empathetic", "Empathetic", "Rewrite in a kind, empathetic, understanding tone."),
    ("academic", "Academic", "Rewrite in a precise, scholarly, academic tone."),
    ("playful", "Playful", "Rewrite in a fun, playful, lighthearted tone."),
    ("redneck", "Redneck / Hillbilly", "Rewrite in a folksy Southern redneck/hillbilly dialect — relaxed grammar, drawl spellings (e.g. 'gonna', 'ain't', 'y'all', 'fixin' to', 'reckon', 'dadgum'), and homespun country phrasing — while keeping the original meaning clear."),
]
TONE_KEYS = [key for key, _label, _prompt in TONES]
TONE_PROMPTS = {key: prompt for key, _label, prompt in TONES}


DEFAULT_OPTIONS = {
    "grammar": True,
    **{key: False for key in TONE_KEYS},
    "expand": False,
    "auto_suggest": True,
    # Speculation mode: predict sentence continuations on a typing pause and
    # eagerly pre-draft answers as soon as context is set.
    "speculation": False,
}


# === Configurable hotkeys ===
# Each action maps to a binding: required modifiers + the main key's Windows
# virtual-key code, plus a human-readable label for the UI. Users rebind these
# in the Shortcuts window (settings_window). The keyboard monitor matches live
# keystrokes against these definitions instead of hardcoded combos.
HOTKEY_ACTIONS = [
    ("fix", "Fix grammar / whole field"),
    ("accept", "Apply suggestion"),
    ("context", "Set selection as context"),
    ("answer", "Draft answer from context"),
]

DEFAULT_HOTKEYS = {
    "fix":     {"ctrl": True, "shift": True,  "alt": False, "vk": 71, "label": "Ctrl+Shift+G"},
    "accept":  {"ctrl": True, "shift": False, "alt": False, "vk": 32, "label": "Ctrl+Space"},
    "context": {"ctrl": True, "shift": False, "alt": True,  "vk": 88, "label": "Ctrl+Alt+X"},
    "answer":  {"ctrl": True, "shift": False, "alt": True,  "vk": 65, "label": "Ctrl+Alt+A"},
}


# === Floating selection toolbar ===
# Buttons shown next to a drag-selection. Each action maps to enabled/disabled.
# The label carries a small glyph + word; order here is the on-screen order.
TOOLBAR_ACTIONS = [
    ("set_context", "✎ Context"),
    ("draft_answer", "✦ Answer"),
    ("fix_grammar", "✓ Fix"),
]
DEFAULT_TOOLBAR = {"set_context": True, "draft_answer": True, "fix_grammar": True}


def _hotkeys_copy():
    return {k: dict(v) for k, v in DEFAULT_HOTKEYS.items()}


# Correction engine. Verbic runs exclusively on the configured AI provider —
# the offline LanguageTool engine has been removed. The single-entry ENGINES
# map is kept so older configs that stored an engine value still load cleanly
# (anything not "ai" is normalized to "ai" in load_config).
ENGINES = {
    "ai": {"label": "AI (Provider configured below)"},
}
DEFAULT_ENGINE = "ai"


def _default_config():
    return {
        "engine": DEFAULT_ENGINE,
        "provider": "ollama",
        "options": dict(DEFAULT_OPTIONS),
        "hotkeys": _hotkeys_copy(),
        "toolbar": dict(DEFAULT_TOOLBAR),
        "selection_button": True,
        "providers": {
            name: {"model": info["default_model"], "api_key": "", "base_url": info["base_url"] or ""}
            for name, info in PROVIDERS.items()
        },
    }


def load_config():
    path = _config_path()
    defaults = _default_config()

    # One-time migration: if there's no config in %APPDATA% yet but a legacy
    # one exists next to the executable, adopt it so the user keeps their API
    # key and settings across this update.
    if not os.path.exists(path):
        legacy = _legacy_config_path()
        if os.path.abspath(legacy) != os.path.abspath(path) and os.path.exists(legacy):
            try:
                import shutil
                os.makedirs(_config_dir(), exist_ok=True)
                shutil.copyfile(legacy, path)
            except Exception:
                # Couldn't copy — read the legacy file directly this run; the
                # next save_config() will persist it to the new location.
                path = legacy

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
        # Backfill missing toggle states from defaults so older configs upgrade cleanly.
        saved_options = data.get("options") or {}
        merged_options = dict(DEFAULT_OPTIONS)
        for k, v in saved_options.items():
            if k in merged_options and isinstance(v, bool):
                merged_options[k] = v
        data["options"] = merged_options
        if data.get("engine") not in ENGINES:
            data["engine"] = DEFAULT_ENGINE

        # Backfill hotkeys: start from defaults, overlay any saved binding that
        # still names a known action and carries a valid shape.
        saved_hotkeys = data.get("hotkeys") or {}
        merged_hotkeys = _hotkeys_copy()
        for action, binding in saved_hotkeys.items():
            if action in merged_hotkeys and isinstance(binding, dict) and "vk" in binding:
                merged_hotkeys[action] = {
                    "ctrl": bool(binding.get("ctrl")),
                    "shift": bool(binding.get("shift")),
                    "alt": bool(binding.get("alt")),
                    "vk": int(binding.get("vk")),
                    "label": str(binding.get("label", "")),
                }
        data["hotkeys"] = merged_hotkeys

        # Backfill toolbar toggles.
        saved_toolbar = data.get("toolbar") or {}
        merged_toolbar = dict(DEFAULT_TOOLBAR)
        for k, v in saved_toolbar.items():
            if k in merged_toolbar and isinstance(v, bool):
                merged_toolbar[k] = v
        data["toolbar"] = merged_toolbar
        if "selection_button" not in data or not isinstance(data["selection_button"], bool):
            data["selection_button"] = True

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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass
