"""Lightweight diagnostic logger.

Disabled by default. Set the environment variable GRAMMAR_DEBUG=1 (or any
non-empty value) to enable. Logs go to a predictable, reviewable per-user
location — %APPDATA%\\Verbic\\Logs\\verbic.log — NOT a Temp directory.

Logs intentionally contain only non-sensitive metadata (scopes, decisions,
text *lengths*) — never API keys, prompt contents, or selected/typed text.
"""
import os
from datetime import datetime


def _log_dir():
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") \
        or os.path.expanduser("~")
    return os.path.join(base, "Verbic", "Logs")


_ENABLED = bool(os.environ.get("GRAMMAR_DEBUG"))
_LOG_PATH = os.path.join(_log_dir(), "verbic.log")


def is_enabled():
    return _ENABLED


def log(scope, msg):
    if not _ENABLED:
        return
    try:
        os.makedirs(_log_dir(), exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='milliseconds')} [{scope}] {msg}\n")
    except Exception:
        pass
