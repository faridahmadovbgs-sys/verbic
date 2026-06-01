import ctypes
import os
import threading
import time
from ctypes import wintypes
from pynput import keyboard, mouse
from debug_log import log as _dlog


_VK_CONTROL = 0x11
_VK_SHIFT = 0x10
_VK_ALT = 0x12
_VK_SPACE = 0x20

# Virtual-key codes that are modifiers — never treated as a hotkey's "main" key.
_MODIFIER_VKS = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C}

_OWN_PID = os.getpid()


def _key_vk(key):
    """Best-effort Windows virtual-key code for a pynput key.

    KeyCode objects expose .vk directly. Special keys (space, enter, function
    keys) wrap a KeyCode in .value. Returns None when no vk is available."""
    vk = getattr(key, "vk", None)
    if vk is not None:
        return vk
    try:
        return key.value.vk
    except Exception:
        return None

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
                 on_typing=None, on_context_hotkey=None, on_answer_hotkey=None,
                 on_selection_made=None):
        self._buffer = []
        self._char_count = 0
        self._lock = threading.Lock()
        self._on_hotkey = on_hotkey
        self._on_text_ready = on_text_ready
        self._on_accept_hotkey = on_accept_hotkey
        self._on_typing = on_typing
        self._on_context_hotkey = on_context_hotkey
        self._on_answer_hotkey = on_answer_hotkey
        self._on_selection_made = on_selection_made
        # Maps an action name to its callback. Hotkey definitions are matched
        # against these at keypress time (see set_hotkeys / _match_hotkey).
        self._action_callbacks = {
            "fix": on_hotkey,
            "accept": on_accept_hotkey,
            "context": on_context_hotkey,
            "answer": on_answer_hotkey,
        }
        self._hotkeys = {}
        self._listener = None
        self._ctrl_pressed = False
        self._shift_pressed = False
        self._pressed_keys = set()
        self._mouse_listener = None
        self._paused = False
        self._text_timer = None
        self._last_fg_hwnd = None
        # Drag-to-select tracking for the floating context button.
        self._press_pos = None
        # Double/triple-click tracking: word- and line-selection produce no
        # drag, so we detect them by two rapid clicks at the same spot.
        self._last_release_time = 0.0
        self._last_release_pos = None

    def set_hotkeys(self, hotkeys):
        """Install the action→binding map. `hotkeys` is the dict from config:
        {action: {ctrl, shift, alt, vk, label}}. Safe to call at runtime to
        apply a rebind without restarting the listener."""
        self._hotkeys = dict(hotkeys or {})

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

        # Configurable hotkeys: match the pressed key's vk + the live modifier
        # state against each action's binding. Modifiers are read from the OS
        # (GetAsyncKeyState) rather than tracked state so a missed release event
        # during a window switch can't desync the match.
        vk = _key_vk(key)
        if vk is not None and vk not in _MODIFIER_VKS and self._hotkeys:
            try:
                gks = ctypes.windll.user32.GetAsyncKeyState
                ctrl = bool(gks(_VK_CONTROL) & 0x8000)
                shift = bool(gks(_VK_SHIFT) & 0x8000)
                alt = bool(gks(_VK_ALT) & 0x8000)
            except Exception:
                ctrl, shift, alt = self._ctrl_pressed, self._shift_pressed, False
            for action, binding in self._hotkeys.items():
                cb = self._action_callbacks.get(action)
                if cb is None:
                    continue
                if (vk == binding.get("vk")
                        and bool(binding.get("ctrl")) == ctrl
                        and bool(binding.get("shift")) == shift
                        and bool(binding.get("alt")) == alt):
                    cb()
                    return

        # Ctrl+` (backtick/tilde) — fixed convenience alias for Fix, kept for
        # muscle memory regardless of the configurable Fix binding.
        if self._ctrl_pressed:
            try:
                if hasattr(key, "char") and key.char == "`":
                    self._on_hotkey()
                    return
                if vk == 192:
                    self._on_hotkey()
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
        """Mouse press/release anywhere on screen.

        On press: resets the keystroke buffer so the next round of typing
        starts fresh at the (likely new) cursor position. Notably does NOT
        close any visible suggestion overlay or clear the pending accept
        payload: pynput's global mouse hook fires *before* tk's window-level
        click handler, so racing here against a click meant for the overlay
        reliably wiped the payload before the overlay could read it
        (HighDPI made the coordinate-based 'is this click on us?' check
        too flaky to rely on). The overlay still goes away when the user
        types, which is the normal dismissal path; clicks elsewhere just
        leave it floating until typing resumes.

        On release: if the pointer moved far enough since press, the user
        just drag-selected text — fire on_selection_made so the host can pop
        the floating 'Set as context' button near the release point.
        """
        try:
            if self._paused:
                return
            # Ignore clicks that land on one of our own windows (the floating
            # button or the suggestion overlay) so clicking the button doesn't
            # wipe the buffer or re-trigger selection handling. The bounds
            # fallback covers HighDPI displays where WindowFromPoint and
            # pynput's click coordinates disagree.
            if _is_own_window_at_point(x, y):
                return
            try:
                from selection_button import SelectionToolbar
                if SelectionToolbar.point_is_inside_any_visible(x, y):
                    return
            except Exception:
                pass
            if pressed:
                self._press_pos = (x, y)
                self.reset_buffer()
            else:
                press = self._press_pos
                self._press_pos = None
                if press is not None and self._on_selection_made is not None:
                    dx = abs(x - press[0])
                    dy = abs(y - press[1])
                    now = time.monotonic()
                    # Case 1: drag-select — pointer moved between press and
                    # release. 6px threshold filters clicks and tiny jitter.
                    dragged = (dx + dy) >= 6
                    # Case 2: double/triple-click select (word / line) — no
                    # drag, but a second click lands at ~the same spot within
                    # 450ms of the previous one.
                    multi_click = False
                    if not dragged and self._last_release_pos is not None:
                        ldx = abs(x - self._last_release_pos[0])
                        ldy = abs(y - self._last_release_pos[1])
                        if (now - self._last_release_time) <= 0.45 and (ldx + ldy) <= 8:
                            multi_click = True
                    self._last_release_time = now
                    self._last_release_pos = (x, y)
                    if dragged or multi_click:
                        try:
                            self._on_selection_made(x, y)
                        except Exception:
                            pass
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
