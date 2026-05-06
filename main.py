import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tray_app import GrammarTrayApp


def main():
    app = GrammarTrayApp()
    app.run()


if __name__ == "__main__":
    main()
