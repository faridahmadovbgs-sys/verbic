import threading
from pynput import keyboard


class KeyboardMonitor:
    def __init__(self, on_hotkey):
        self._buffer = []
        self._char_count = 0
        self._lock = threading.Lock()
        self._on_hotkey = on_hotkey
        self._listener = None
        self._hotkey_keys = {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.KeyCode.from_char("g")}
        self._pressed_keys = set()

    def add_char(self, char):
        with self._lock:
            self._buffer.append(char)
            self._char_count += 1

    def add_newline(self):
        with self._lock:
            self._buffer.append("\n")
            self._char_count += 1

    def handle_backspace(self):
        with self._lock:
            if self._buffer:
                self._buffer.pop()
                self._char_count = max(0, self._char_count - 1)

    def reset_buffer(self):
        with self._lock:
            self._buffer.clear()
            self._char_count = 0

    def get_buffer(self):
        with self._lock:
            return "".join(self._buffer)

    def get_char_count(self):
        with self._lock:
            return self._char_count

    def consume_buffer(self):
        with self._lock:
            text = "".join(self._buffer)
            count = self._char_count
            self._buffer.clear()
            self._char_count = 0
            return text, count

    def _on_press(self, key):
        self._pressed_keys.add(key)
        if self._hotkey_keys.issubset(self._pressed_keys):
            self._on_hotkey()
            return

        try:
            if hasattr(key, "char") and key.char is not None:
                self.add_char(key.char)
        except AttributeError:
            pass

        if key == keyboard.Key.enter:
            self.add_newline()
        elif key == keyboard.Key.backspace:
            self.handle_backspace()
        elif key in (keyboard.Key.left, keyboard.Key.right, keyboard.Key.up, keyboard.Key.down):
            self.reset_buffer()

    def _on_release(self, key):
        self._pressed_keys.discard(key)

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
