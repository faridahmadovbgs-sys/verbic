"""Windows auto-start ("run Verbic when Windows starts") management.

The source of truth is the per-user Run key in the registry, NOT a flag in
config.json: the user can also switch Verbic off from Task Manager's Startup
tab, and a mirrored config flag would silently disagree with reality. Every
read here hits the registry (cheap — microseconds).

Two mechanisms can start Verbic at logon:
  * HKCU\\...\\CurrentVersion\\Run  — what this module writes, and what the
    installer's optional auto-start task now writes too.
  * A .lnk in the user's Startup folder — what installers up to v1.4.2 created.
Verbic has no single-instance guard, so leaving both in place would launch two
copies. enable() therefore writes the Run entry and removes the legacy
shortcut; disable() removes both.
"""
import os
import sys

try:
    import winreg
except ImportError:  # non-Windows (the mac port shares parts of this tree)
    winreg = None

APP_NAME = "Verbic"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_SHELL_FOLDERS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
_SHORTCUT_NAME = APP_NAME + ".lnk"


def is_supported():
    return sys.platform == "win32" and winreg is not None


def _launch_command():
    """The command line Windows should run at logon, fully quoted."""
    exe = os.path.abspath(sys.executable)
    if getattr(sys, "frozen", False):
        return f'"{exe}"'
    # Running from source (dev): start main.py with the console-less
    # interpreter so the tray app comes up without a command window.
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = exe
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return f'"{pythonw}" "{script}"'


def _read_run_value():
    if not is_supported():
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _type = winreg.QueryValueEx(key, APP_NAME)
        return value or None
    except OSError:
        return None


def _write_run_value(command):
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        return True
    except OSError:
        return False


def _startup_shortcut_path():
    """The legacy (pre-1.5.0 installer) Startup-folder shortcut. May not exist."""
    folder = None
    if is_supported():
        # Ask Explorer where the Startup folder actually is — the user may have
        # redirected it, and the on-disk name is localized in some Windows builds.
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SHELL_FOLDERS) as key:
                folder, _type = winreg.QueryValueEx(key, "Startup")
        except OSError:
            folder = None
    if not folder:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        folder = os.path.join(appdata, "Microsoft", "Windows", "Start Menu",
                              "Programs", "Startup")
    return os.path.join(folder, _SHORTCUT_NAME)


def _remove_startup_shortcut():
    path = _startup_shortcut_path()
    if not path or not os.path.exists(path):
        return True
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def is_enabled():
    if not is_supported():
        return False
    if _read_run_value():
        return True
    path = _startup_shortcut_path()
    return bool(path and os.path.exists(path))


def enable():
    if not is_supported():
        return False
    if not _write_run_value(_launch_command()):
        return False
    # One mechanism only, or Windows starts two copies — see the module docstring.
    _remove_startup_shortcut()
    return True


def disable():
    if not is_supported():
        return False
    ok = True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    except OSError:
        ok = False
    if not _remove_startup_shortcut():
        ok = False
    return ok


def set_enabled(value):
    return enable() if value else disable()


def refresh():
    """Repoint an existing Run entry at the current executable.

    An in-place update can land Verbic in a different folder; the stale command
    would then fail silently at the next logon. Frozen builds only — from source
    this would overwrite an installed copy's entry with a dev command line.
    """
    if not is_supported() or not getattr(sys, "frozen", False):
        return
    current = _read_run_value()
    if not current:
        return
    wanted = _launch_command()
    if current.strip().lower() != wanted.lower():
        _write_run_value(wanted)
