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

from tray_app import GrammarTrayApp


def main():
    app = GrammarTrayApp()
    app.run()


if __name__ == "__main__":
    main()
