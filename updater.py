"""Self-updater for Verbic.

Talks to the Sky Tools site proxy (NOT GitHub directly), so it works even when
the source repo is private — the proxy holds the read token server-side:
    GET https://www.skyscrum.com/api/verbic-version/  -> {"version": "...", "windows": "<url>"}
    GET https://www.skyscrum.com/api/downloads/verbic/ -> the installer .exe

Flow: ask the proxy for the latest version, compare to the running version, and
if newer offer to download + run the installer. The Inno installer closes the
running app (AppMutex) and installs over it.
"""
import os
import sys
import threading
import subprocess
import urllib.request
import json

from version import APP_VERSION

SITE = "https://www.skyscrum.com"
VERSION_URL = f"{SITE}/api/verbic-version/"
DOWNLOAD_URL = f"{SITE}/api/downloads/verbic/"

# Clear, attributable user agent so the SkyScrum version-check/download traffic
# is never an "unknown executable phoning home".
_UA = f"Verbic/{APP_VERSION}"

_checking = False


def _updates_dir():
    """Predictable, reviewable location for the downloaded installer — NOT a
    Temp directory."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") \
        or os.path.expanduser("~")
    return os.path.join(base, "Verbic", "Updates")


def _parse(v):
    out = []
    for part in str(v).lstrip("vV").split("."):
        try:
            out.append(int(part))
        except ValueError:
            out.append(0)
    return out


def _is_newer(remote, local):
    a, b = _parse(remote), _parse(local)
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x > y:
            return True
        if x < y:
            return False
    return False


def _fetch_latest(timeout=10):
    req = urllib.request.Request(VERSION_URL, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download(url, dest, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        expected = resp.headers.get("Content-Length")
        written = 0
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            out.write(chunk)
            written += len(chunk)
    # Never hand a truncated .exe to subprocess — a server that closes the
    # connection early doesn't always raise, it just stops sending.
    if expected and written != int(expected):
        try:
            os.remove(dest)
        except OSError:
            pass
        raise IOError(f"Update download incomplete ({written}/{expected} bytes)")


def check_and_notify(notify=None, timeout=10):
    """Startup check: if a newer version exists, NOTIFY the user — but do not
    download or install anything. The user installs deliberately via the tray
    'Check for Updates' action. This avoids silent self-updating on managed
    devices (a malware-persistence signal) while still surfacing updates."""
    global _checking
    if _checking:
        return
    _checking = True
    try:
        info = _fetch_latest(timeout=timeout)
        latest = info.get("version", "")
        if latest and _is_newer(latest, APP_VERSION) and notify:
            notify("Verbic",
                   f"Verbic {latest} is available. Open the tray menu → "
                   f"“Check for Updates” to install.")
    except Exception:
        # Stay silent on the startup check — surface errors only on the
        # user-initiated manual check.
        pass
    finally:
        _checking = False


def check_for_updates(silent=True, notify=None, ask=None):
    """Check for and optionally install an update.

    silent : if True, stay quiet when already up to date or on error (startup check).
    notify : optional callable(title, message) for tray notifications.
    ask    : optional callable(version) -> bool, returns True to proceed with install.
             If None, updates auto-install when found.
    """
    global _checking
    if _checking:
        return
    _checking = True
    try:
        info = _fetch_latest()
        latest = info.get("version", "")
        if not latest or not _is_newer(latest, APP_VERSION):
            if not silent and notify:
                notify("Verbic", f"You're on the latest version ({APP_VERSION}).")
            return

        if ask is not None and not ask(latest):
            return

        if notify:
            notify("Verbic", f"Downloading update {latest}…")

        updates_dir = _updates_dir()
        os.makedirs(updates_dir, exist_ok=True)
        dest = os.path.join(updates_dir, f"VerbicSetup-{latest}.exe")
        _download(info.get("windows") or DOWNLOAD_URL, dest)

        # Launch the installer detached and exit so it can replace the running app.
        subprocess.Popen([dest], creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        os._exit(0)
    except Exception as e:
        if not silent and notify:
            notify("Verbic", f"Update check failed: {e}")
    finally:
        _checking = False


def check_in_background(**kwargs):
    threading.Thread(target=lambda: check_for_updates(**kwargs), daemon=True).start()
