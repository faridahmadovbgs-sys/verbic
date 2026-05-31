import ctypes
import os
import threading
from ctypes import wintypes
from pynput import keyboard, mouse
from debug_log import log as _dlog


_VK_CONTROL = 0x11
_VK_SHIFT = 0x10
_VK_SPACE = 0x20

_OWN_PID = os.getpid()

# Bind WindowFromPoint so we can identify the window under a mouse click.
# Used by _on_click to skip buffer resets when the click landed on our own
# overlay — otherwise the click that's meant to accept the suggestion would
# also fire _on_typing and wipe the accept payload.
_user32 = ctypes.windll.user32
_user32.WindowFromPoint.argtypes = [wintypes.POINT]
_user32.WindowFromPoint.restype = wintypes.HWND


def _is_own_window(hwnd):
    """True if hwnd belongs to this process (our overlay / settings / about /
    welcome windows). The keystroke-time foreground poll must ignore these so
    a brief overlay appearance doesn't trigger a buffer reset."""
    if not hwnd:
        return False
    try:
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == _OWN_PID
    except Exception:
        return False


def _is_own_window_at_point(x, y):
    """True if the topmost window at screen coords (x, y) is one of ours."""
    try:
        pt = wintypes.POINT(int(x), int(y))
        return _is_own_window(_user32.WindowFromPoint(pt))
    except Exception:
        return False


class KeyboardMonitor:
    def __init__(self, on_hotkey, on_text_ready=None, on_accept_hotkey=None,
                 on_typing=None):
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
        # Enter ends a paragraph: in chat apps it sends the message, in
        # editors it starts a new line. Either way the previous text is
        # "committed" — drop it from the buffer so the next auto-suggest
        # only considers what the user is typing *now*, not what came
        # before the Enter.
        with self._lock:
            self._buffer.clear()
            self._char_count = 0
            self._cancel_text_timer()

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

    def snapshot_buffer(self):
        """Atomically return (text, char_count). The auto-suggest pipeline
        captures both at fire-time so the replacement length always matches
        the text we sent to the LLM — even if the user manages to type
        between the LLM completing and the overlay rendering."""
        with self._lock:
            return "".join(self._buffer), self._char_count

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
        keystroke — cursor position is no longer where we thought it was.

        Own-process windows (overlay, settings, welcome, about) are ignored:
        a brief overlay flash must not invalidate the buffer the user is
        actively typing into."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            return
        if _is_own_window(hwnd):
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

        # Ctrl+Space (accept suggestion). Ctrl+Tab was the v1.0.x default but
        # it clashed with tab cycling in browsers (Chrome/Edge/Firefox) and
        # channel cycling in chat apps (Slack/Discord). Ctrl+Space is free in
        # those and semantically matches "trigger suggestion" in IDEs.
        if self._ctrl_pressed and not self._shift_pressed and self._on_accept_hotkey:
            if key == keyboard.Key.space:
                self._on_accept_hotkey()
                return
            try:
                if hasattr(key, "vk") and key.vk == _VK_SPACE:
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
            # Enter clears the buffer (previous paragraph is "done"). Don't
            # schedule a suggestion off of an empty buffer — wait for the
            # user to actually start typing the next sentence.
            self._fire_on_typing()
            return
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
        """Mouse press anywhere on screen.

        Resets the keystroke buffer so the next round of typing starts fresh
        at the (likely new) cursor position. Notably does NOT close any
        visible suggestion overlay or clear the pending accept payload:
        pynput's global mouse hook fires *before* tk's window-level click
        handler, so racing here against a click meant for the overlay
        reliably wiped the payload before the overlay could read it
        (HighDPI made the coordinate-based 'is this click on us?' check
        too flaky to rely on). The overlay still goes away when the user
        types, which is the normal dismissal path; clicks elsewhere just
        leave it floating until typing resumes.
        """
        try:
            if self._paused:
                return
            if pressed:
                self.reset_buffer()
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
