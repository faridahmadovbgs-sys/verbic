"""Inject text replacements into the foreground app via simulated keystrokes.

Performance: clipboard ops use ctypes directly (microseconds) instead of
shelling out to PowerShell (~400 ms each). Per-keystroke sleeps are also
tightened — most modern Windows apps process injected events as fast as
they arrive.
"""
import ctypes
import time
from ctypes import wintypes
from pynput.keyboard import Controller, Key


CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

# Set explicit argtypes/restype so 64-bit handles are not truncated.
_user32.OpenClipboard.argtypes = [wintypes.HWND]
_user32.OpenClipboard.restype = wintypes.BOOL
_user32.CloseClipboard.argtypes = []
_user32.CloseClipboard.restype = wintypes.BOOL
_user32.EmptyClipboard.argtypes = []
_user32.EmptyClipboard.restype = wintypes.BOOL
_user32.GetClipboardData.argtypes = [wintypes.UINT]
_user32.GetClipboardData.restype = wintypes.HANDLE
_user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
_user32.SetClipboardData.restype = wintypes.HANDLE

_kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
_kernel32.GlobalAlloc.restype = wintypes.HANDLE
_kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
_kernel32.GlobalLock.restype = wintypes.LPVOID
_kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
_kernel32.GlobalUnlock.restype = wintypes.BOOL
_kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
_kernel32.GlobalFree.restype = wintypes.HANDLE


def _get_clipboard_text():
    """Return current clipboard text, or None on failure."""
    if not _user32.OpenClipboard(None):
        return None
    try:
        handle = _user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.c_wchar_p(ptr).value or ""
        finally:
            _kernel32.GlobalUnlock(handle)
    finally:
        _user32.CloseClipboard()


def _set_clipboard_text(text):
    """Write `text` to clipboard. Returns True on success."""
    if text is None:
        text = ""
    if not _user32.OpenClipboard(None):
        return False
    try:
        _user32.EmptyClipboard()
        size = (len(text) + 1) * ctypes.sizeof(ctypes.c_wchar)
        handle = _kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not handle:
            return False
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            _kernel32.GlobalFree(handle)
            return False
        try:
            ctypes.memmove(ptr, ctypes.c_wchar_p(text), size)
        finally:
            _kernel32.GlobalUnlock(handle)
        # SetClipboardData transfers ownership of the handle on success.
        if not _user32.SetClipboardData(CF_UNICODETEXT, handle):
            _kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        _user32.CloseClipboard()


class TextReplacer:
    def __init__(self):
        self._keyboard = Controller()

    # === Public API ===

    def replace_text(self, char_count, corrected_text):
        """Select the last `char_count` characters and replace them with
        `corrected_text` via clipboard paste."""
        self._do_replace(char_count, corrected_text)

    def paste_over_selection(self, corrected_text):
        """Paste `corrected_text` over whatever is currently selected."""
        self._paste_with_clipboard(corrected_text, pre_delay=0.04)

    def replace_all(self, corrected_text):
        """Ctrl+A then paste — fully rewrite the focused field."""
        self._do_replace_all(corrected_text)

    def insert_text(self, text):
        """Paste `text` at the current caret without selecting anything first.
        Used for inserting a generated answer where there's no original text
        to replace."""
        self._paste_with_clipboard(text, pre_delay=0.04)

    # === Internals ===

    def _do_replace(self, char_count, corrected_text):
        # Hold Shift for the entire selection sweep — much faster than
        # re-pressing it per arrow key.
        #
        # Timing notes (the source of the "lLet" / "whWhat" leftover-prefix
        # bug — the paste only overwrites part of the typed text because some
        # Shift+Left presses were dropped, so the selection came up short):
        #   - After pressing Shift, the app's input pipeline (especially
        #     Chrome's browser→renderer IPC) needs a moment to register the
        #     modifier as held. If the first Left arrow arrives before that,
        #     the app treats it as a plain "Left" — moving the caret instead
        #     of extending the selection — and the selection is one char short.
        #   - Per-arrow interval: apps coalesce or drop arrow events that
        #     arrive faster than their input loop wakes up. 4 ms still dropped
        #     keys "sometimes" under load / in Electron apps. Now ~13 ms per
        #     char with a gap between the down and up event so the app registers
        #     each as a distinct keystroke — slower but reliable, and short
        #     auto-suggest sentences still complete in well under a second.
        time.sleep(0.05)
        self._keyboard.press(Key.shift)
        time.sleep(0.04)
        try:
            for _ in range(char_count):
                self._keyboard.press(Key.left)
                time.sleep(0.004)
                self._keyboard.release(Key.left)
                time.sleep(0.009)
        finally:
            self._keyboard.release(Key.shift)

        # Let the final selection settle before the paste overwrites it.
        time.sleep(0.03)
        self._paste_with_clipboard(corrected_text, pre_delay=0.05)

    def _do_replace_all(self, corrected_text):
        time.sleep(0.04)
        self._keyboard.press(Key.ctrl)
        self._keyboard.press("a")
        self._keyboard.release("a")
        self._keyboard.release(Key.ctrl)
        self._paste_with_clipboard(corrected_text, pre_delay=0.04)

    def _paste_with_clipboard(self, text, pre_delay=0.04):
        old_clip = _get_clipboard_text()
        _set_clipboard_text(text)

        time.sleep(pre_delay)

        self._keyboard.press(Key.ctrl)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(Key.ctrl)

        # Give the target app time to consume the paste before we restore
        # the previous clipboard contents. 80 ms is enough for every app
        # I tested (Notepad, VS Code, Chrome, Slack, Word).
        time.sleep(0.08)
        if old_clip is not None and old_clip != text:
            # The paste target (or a clipboard manager reacting to it) can
            # briefly hold the clipboard open right after Ctrl+V; one short
            # retry rescues the user's original clipboard in that case.
            if not _set_clipboard_text(old_clip):
                time.sleep(0.05)
                _set_clipboard_text(old_clip)
