import ctypes
import threading
from pynput import keyboard, mouse
from debug_log import log as _dlog


_VK_CONTROL = 0x11
_VK_SHIFT = 0x10


class KeyboardMonitor:
    def __init__(self, on_hotkey, on_text_ready=None, on_accept_hotkey=None, on_typing=None):
        self._buffer = []
        self._char_count = 0
        self._lock = threading.Lock()
        self._on_hotkey = on_hotkey
        self._on_text_ready = on_text_ready
        self._on_accept_hotkey = on_accept_hotkey
        self._on_typing = on_typing
        self._listener = None
        self._ctrl_pressed = False
        self._shift_pressed = False
        self._pressed_keys = set()
        self._mouse_listener = None
        self._paused = False
        self._text_timer = None
        self._last_fg_hwnd = None

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
            self._cancel_text_timer()
            return text, count

    def _cancel_text_timer(self):
        if self._text_timer is not None:
            try:
                self._text_timer.cancel()
            except Exception:
                pass
            self._text_timer = None

    def _schedule_text_ready(self):
        self._cancel_text_timer()
        if self._paused or self._on_text_ready is None:
            return
        self._text_timer = threading.Timer(0.8, self._fire_text_ready)
        self._text_timer.daemon = True
        self._text_timer.start()

    def _fire_text_ready(self):
        if self._paused:
            return
        try:
            if self._on_text_ready:
                self._on_text_ready()
        except Exception:
            pass

    def pause(self):
        self._paused = True
        self._cancel_text_timer()

    def resume(self):
        self._paused = False
        self.reset_buffer()

    def _on_press(self, key):
        # Wrap to keep the global listener alive if any callback raises.
        try:
            self._on_press_inner(key)
        except Exception:
            pass

    def _sync_modifier_state(self):
        """Re-read Ctrl/Shift from the OS in case a release event was missed
        during a window switch (e.g., Alt+Tab while holding modifiers)."""
        try:
            gks = ctypes.windll.user32.GetAsyncKeyState
            self._ctrl_pressed = bool(gks(_VK_CONTROL) & 0x8000)
            self._shift_pressed = bool(gks(_VK_SHIFT) & 0x8000)
        except Exception:
            pass

    def _check_foreground_change(self):
        """Reset the buffer if the foreground window changed since the last
        keystroke — cursor position is no longer where we thought it was."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            return
        if self._last_fg_hwnd is None:
            self._last_fg_hwnd = hwnd
            return
        if hwnd != self._last_fg_hwnd:
            self._last_fg_hwnd = hwnd
            self.reset_buffer()
            self._fire_on_typing()

    def notify_foreground_change(self, hwnd):
        """External hook for the FocusWatcher — same effect as detecting a
        change on the next keystroke, but fires immediately."""
        try:
            if self._last_fg_hwnd != hwnd:
                self._last_fg_hwnd = hwnd
                self.reset_buffer()
                self._fire_on_typing()
                _dlog("monitor", f"foreground changed -> hwnd={hwnd}; buffer reset")
        except Exception:
            pass

    def _on_press_inner(self, key):
        if self._paused:
            return
        self._sync_modifier_state()
        self._check_foreground_change()
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

        # Ctrl+Tab (accept suggestion)
        if self._ctrl_pressed and not self._shift_pressed and self._on_accept_hotkey:
            if key == keyboard.Key.tab:
                self._on_accept_hotkey()
                return
            try:
                if hasattr(key, "vk") and key.vk == 9:
                    self._on_accept_hotkey()
                    return
            except AttributeError:
                pass

        typed = False
        try:
            if hasattr(key, "char") and key.char is not None:
                if not self._ctrl_pressed:
                    self.add_char(key.char)
                    typed = True
        except AttributeError:
            pass

        if key == keyboard.Key.space:
            self.add_char(" ")
            typed = True
        elif key == keyboard.Key.enter:
            self.add_newline()
            typed = True
        elif key == keyboard.Key.backspace:
            self.handle_backspace()
            typed = True
        elif key == keyboard.Key.tab:
            self.add_char("\t")
            typed = True
        elif key in (keyboard.Key.left, keyboard.Key.right, keyboard.Key.up, keyboard.Key.down):
            self.reset_buffer()
            typed = False
            self._fire_on_typing()

        if typed:
            self._schedule_text_ready()
            self._fire_on_typing()

    def _fire_on_typing(self):
        if self._on_typing is None:
            return
        try:
            self._on_typing()
        except Exception:
            pass

    def _on_release(self, key):
        try:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self._ctrl_pressed = False
            elif key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
                self._shift_pressed = False
        except Exception:
            pass

    def _on_click(self, x, y, button, pressed):
        try:
            if self._paused:
                return
            if pressed:
                self.reset_buffer()
                self._fire_on_typing()
        except Exception:
            pass

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
