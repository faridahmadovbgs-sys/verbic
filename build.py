"""Build GrammarTool.exe using PyInstaller."""
import subprocess
import sys
import os
from PIL import Image

def create_ico():
    img = Image.open("icon.png")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []
    for size in sizes:
        resized = img.resize(size, Image.LANCZOS)
        icons.append(resized)
    icons[0].save("icon.ico", format="ICO", sizes=[s for s in sizes], append_images=icons[1:])
    print("Created icon.ico")

def build_exe():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--icon=icon.ico",
        "--version-file=version_info.txt",
        "--add-data", "icon.png;.",
        "--name", "GrammarTool",
        "main.py",
    ]
    subprocess.run(cmd, check=True)
    print("Build complete: dist/GrammarTool.exe")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    create_ico()
    build_exe()
