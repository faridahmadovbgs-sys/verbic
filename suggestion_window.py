import ctypes
import threading
import tkinter as tk
from ctypes import wintypes


GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

# Virtual-screen system metrics (multi-monitor)
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


def _get_caret_screen_pos():
    try:
        fg = ctypes.windll.user32.GetForegroundWindow()
        if not fg:
            return None
        tid = ctypes.windll.user32.GetWindowThreadProcessId(fg, None)
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
            return None
        if not info.hwndCaret:
            return None
        pt = wintypes.POINT(info.rcCaret.left, info.rcCaret.bottom)
        ctypes.windll.user32.ClientToScreen(info.hwndCaret, ctypes.byref(pt))
        return (pt.x, pt.y)
    except Exception:
        return None


def _get_cursor_pos():
    try:
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)
    except Exception:
        return None


def _get_focused_control_rect():
    """Return (left, top, right, bottom) of the focused UIA control in screen coords.

    Works for apps that don't expose a system caret (Chrome, Slack, Electron).
    """
    result = {"rect": None}

    def worker():
        try:
            import uiautomation as auto
            ctrl = auto.GetFocusedControl()
            if ctrl is None:
                return
            r = ctrl.BoundingRectangle
            if r is None:
                return
            if r.right > r.left and r.bottom > r.top:
                result["rect"] = (int(r.left), int(r.top), int(r.right), int(r.bottom))
        except Exception:
            pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(0.6)
    return result["rect"]


def _get_virtual_screen_bounds():
    """Return (left, top, width, height) of the full multi-monitor virtual screen."""
    try:
        gsm = ctypes.windll.user32.GetSystemMetrics
        return (
            gsm(SM_XVIRTUALSCREEN),
            gsm(SM_YVIRTUALSCREEN),
            gsm(SM_CXVIRTUALSCREEN),
            gsm(SM_CYVIRTUALSCREEN),
        )
    except Exception:
        return None


class SuggestionWindow:
    """Inline overlay shown near the caret. Does not steal focus.

    Accept fires via the on_click callback (or the host's global hotkey);
    dismissal is driven externally via close().
    """

    def __init__(self, suggestion_text, on_click=None):
        self._suggestion = suggestion_text
        self._on_click = on_click
        self._window = None
        self._closed = False
        self._click_fired = False
        self._lock = threading.Lock()

    def open(self):
        try:
            self._build_and_show()
        except Exception:
            pass

    def close(self):
        with self._lock:
            self._closed = True

    def _handle_click(self, event=None):
        if self._click_fired:
            return "break"
        self._click_fired = True
        if self._on_click:
            try:
                self._on_click()
            except Exception:
                pass
        return "break"

    def _build_and_show(self):
        self._window = tk.Tk()
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.geometry("+30000+30000")

        # Apply NOACTIVATE before the window is mapped so it never grabs focus.
        self._apply_no_activate()

        outer = tk.Frame(self._window, bg="#888888", padx=1, pady=1)
        outer.pack()
        inner = tk.Frame(outer, bg="#fff8c4", cursor="hand2")
        inner.pack(fill="both", expand=True)

        text_label = tk.Label(
            inner,
            text=self._suggestion,
            bg="#fff8c4",
            fg="#222222",
            font=("Segoe UI", 10),
            wraplength=520,
            justify="left",
            padx=10,
            pady=6,
            cursor="hand2",
        )
        text_label.pack(anchor="w")

        hint_label = tk.Label(
            inner,
            text="Click or Ctrl+Tab to apply  ·  keep typing to dismiss",
            bg="#fff8c4",
            fg="#666666",
            font=("Segoe UI", 8),
            padx=10,
            cursor="hand2",
        )
        hint_label.pack(anchor="w", pady=(0, 4))

        for w in (self._window, outer, inner, text_label, hint_label):
            w.bind("<Button-1>", self._handle_click)

        self._window.update_idletasks()
        self._position()
        self._window.update_idletasks()

        self._poll_close()
        self._window.mainloop()

    def _position(self):
        # Order of preference: system caret (most accurate for Win32 controls),
        # UIA focused-control bounds (for Chrome / Slack / Electron / VS Code),
        # mouse cursor (last resort).
        pos = _get_caret_screen_pos()
        if pos:
            x, y = pos[0] + 8, pos[1] + 18
        else:
            rect = _get_focused_control_rect()
            if rect:
                # Anchor to bottom-left of the focused control, slightly indented.
                left, _top, _right, bottom = rect
                x, y = left + 8, bottom + 4
            else:
                cur = _get_cursor_pos()
                if cur:
                    x, y = cur[0] + 16, cur[1] + 16
                else:
                    x, y = 100, 100

        # Clamp to the full virtual screen across all monitors.
        bounds = _get_virtual_screen_bounds()
        if bounds:
            vx, vy, vw, vh = bounds
        else:
            vx, vy = 0, 0
            vw = self._window.winfo_screenwidth()
            vh = self._window.winfo_screenheight()

        win_w = max(self._window.winfo_reqwidth(), 60)
        win_h = max(self._window.winfo_reqheight(), 30)
        right = vx + vw
        bottom = vy + vh
        if x + win_w > right - 10:
            x = right - win_w - 10
        if y + win_h > bottom - 10:
            y = bottom - win_h - 10
        if x < vx + 10:
            x = vx + 10
        if y < vy + 10:
            y = vy + 10
        self._window.geometry(f"+{x}+{y}")

    def _hwnds(self):
        try:
            hwnd = self._window.winfo_id()
        except Exception:
            return []
        result = []
        if hwnd:
            result.append(hwnd)
            parent = ctypes.windll.user32.GetParent(hwnd)
            if parent:
                result.append(parent)
        return result

    def _apply_no_activate(self):
        try:
            for h in self._hwnds():
                ex_style = ctypes.windll.user32.GetWindowLongW(h, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(
                    h,
                    GWL_EXSTYLE,
                    ex_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
                )
        except Exception:
            pass

    def _poll_close(self):
        with self._lock:
            should_close = self._closed
        if should_close and self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                pass
            return
        if self._window is not None:
            try:
                self._window.after(50, self._poll_close)
            except Exception:
                pass
