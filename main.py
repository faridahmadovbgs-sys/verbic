import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# PyInstaller --noconsole sets sys.stdout / sys.stderr to None. Some bundled
# libraries (language_tool_python via tqdm during JAR download, win10toast,
# subprocess output, etc.) crash with "NoneType has no attribute 'write'"
# when they try to print. Redirect both to NUL before importing anything.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Give this process an explicit taskbar identity. Without it, Windows groups
# our windows under the host process (pythonw.exe in dev, or a generic icon)
# and the taskbar button shows the wrong icon even though the window's own
# icon is set. Setting an AppUserModelID detaches us so the taskbar uses the
# Verbic window icon. Must run before any window is created.
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SandCastleLLC.Verbic")
    except Exception:
        pass

from tray_app import GrammarTrayApp


def main():
    app = GrammarTrayApp()
    app.run()


if __name__ == "__main__":
    main()
