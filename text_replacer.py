import time
import subprocess
import threading
from pynput.keyboard import Controller, Key

_NO_WINDOW = subprocess.CREATE_NO_WINDOW


class TextReplacer:
    def __init__(self):
        self._keyboard = Controller()

    def replace_text(self, char_count, corrected_text):
        self._do_replace(char_count, corrected_text)

    def _do_replace(self, char_count, corrected_text):
        import subprocess

        time.sleep(0.15)

        self._keyboard.press(Key.shift)
        for _ in range(char_count):
            self._keyboard.press(Key.left)
            self._keyboard.release(Key.left)
            time.sleep(0.02)
        self._keyboard.release(Key.shift)

        time.sleep(0.12)

        old_clip = self._get_clipboard()

        self._set_clipboard(corrected_text)
        time.sleep(0.05)

        self._keyboard.press(Key.ctrl)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(Key.ctrl)

        time.sleep(0.2)
        if old_clip is not None:
            self._set_clipboard(old_clip)

    def paste_over_selection(self, corrected_text):
        self._do_paste_over(corrected_text)

    def replace_all(self, corrected_text):
        self._do_replace_all(corrected_text)

    def _do_replace_all(self, corrected_text):
        time.sleep(0.15)

        self._keyboard.press(Key.ctrl)
        self._keyboard.press("a")
        self._keyboard.release("a")
        self._keyboard.release(Key.ctrl)

        time.sleep(0.12)

        old_clip = self._get_clipboard()

        self._set_clipboard(corrected_text)
        time.sleep(0.05)

        self._keyboard.press(Key.ctrl)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(Key.ctrl)

        time.sleep(0.2)
        if old_clip is not None:
            self._set_clipboard(old_clip)

    def _do_paste_over(self, corrected_text):
        time.sleep(0.15)

        old_clip = self._get_clipboard()
        self._set_clipboard(corrected_text)
        time.sleep(0.05)

        self._keyboard.press(Key.ctrl)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(Key.ctrl)

        time.sleep(0.2)
        if old_clip is not None:
            self._set_clipboard(old_clip)

    def _get_clipboard(self):
        try:
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=2,
                creationflags=_NO_WINDOW,
            )
            return result.stdout.rstrip("\r\n") if result.returncode == 0 else None
        except Exception:
            return None

    def _set_clipboard(self, text):
        try:
            subprocess.run(
                ["powershell", "-command", f"Set-Clipboard -Value '{text.replace(chr(39), chr(39)+chr(39))}'"],
                capture_output=True, timeout=2,
                creationflags=_NO_WINDOW,
            )
        except Exception:
            pass
