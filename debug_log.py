"""Lightweight diagnostic logger.

Disabled by default. Set the environment variable GRAMMAR_DEBUG=1 (or any
non-empty value) to enable; logs go to %TEMP%\\grammar_tool.log.
"""
import os
from datetime import datetime


_ENABLED = bool(os.environ.get("GRAMMAR_DEBUG"))
_LOG_PATH = os.path.join(os.environ.get("TEMP") or os.getcwd(), "grammar_tool.log")


def is_enabled():
    return _ENABLED


def log(scope, msg):
    if not _ENABLED:
        return
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='milliseconds')} [{scope}] {msg}\n")
    except Exception:
        pass
