import threading
from pynput import keyboard, mouse


class KeyboardMonitor:
    def __init__(self, on_hotkey):
        self._buffer = []
        self._char_count = 0
        self._lock = threading.Lock()
        self._on_hotkey = on_hotkey
        self._listener = None
        self._ctrl_pressed = False
        self._shift_pressed = False
        self._pressed_keys = set()
        self._mouse_listener = None
        self._paused = False

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

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
        self.reset_buffer()

    def _on_press(self, key):
        if self._paused:
            return
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = True
        elif key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self._shift_pressed = True

        # Ctrl+` (backtick/tilde)
        if self._ctrl_pressed:
            try:
                if hasattr(key, "char") and key.char == "`":
                    self._on_hotkey()
                    return
                if hasattr(key, "vk") and key.vk == 192:
                    self._on_hotkey()
                    return
            except AttributeError:
                pass

        # Ctrl+Shift+G
        if self._ctrl_pressed and self._shift_pressed:
            try:
                if hasattr(key, "char") and key.char == "\x07":
                    self._on_hotkey()
                    return
                if hasattr(key, "vk") and key.vk == 71:
                    self._on_hotkey()
                    return
            except AttributeError:
                pass
            if key == keyboard.KeyCode.from_char("g") or key == keyboard.KeyCode.from_char("G"):
                self._on_hotkey()
                return

        try:
            if hasattr(key, "char") and key.char is not None:
                if not self._ctrl_pressed:
                    self.add_char(key.char)
        except AttributeError:
            pass

        if key == keyboard.Key.space:
            self.add_char(" ")
        elif key == keyboard.Key.enter:
            self.add_newline()
        elif key == keyboard.Key.backspace:
            self.handle_backspace()
        elif key == keyboard.Key.tab:
            self.add_char("\t")
        elif key in (keyboard.Key.left, keyboard.Key.right, keyboard.Key.up, keyboard.Key.down):
            self.reset_buffer()

    def _on_release(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = False
        elif key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self._shift_pressed = False

    def _on_click(self, x, y, button, pressed):
        if pressed:
            self.reset_buffer()

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()
