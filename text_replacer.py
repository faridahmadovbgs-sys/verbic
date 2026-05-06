import time
import threading
from pynput.keyboard import Controller, Key


class TextReplacer:
    def __init__(self):
        self._keyboard = Controller()

    def replace_text(self, char_count, corrected_text):
        thread = threading.Thread(target=self._do_replace, args=(char_count, corrected_text), daemon=True)
        thread.start()

    def _do_replace(self, char_count, corrected_text):
        time.sleep(0.1)

        for _ in range(char_count):
            self._keyboard.press(Key.shift)
            self._keyboard.press(Key.left)
            self._keyboard.release(Key.left)
            self._keyboard.release(Key.shift)
            time.sleep(0.005)

        time.sleep(0.05)

        for char in corrected_text:
            if char == "\n":
                self._keyboard.press(Key.enter)
                self._keyboard.release(Key.enter)
            else:
                self._keyboard.type(char)
            time.sleep(0.005)
