"""Small floating toolbar shown next to a fresh text selection.

When the user drags to select text in any app, the tray app pops one of
these near the mouse-release point with one or more action buttons (Set
context, Draft answer, Fix grammar — whichever the user enabled). It mirrors
SuggestionWindow's Win32 NOACTIVATE + topmost approach so it never steals
focus from the app holding the selection (focus theft would collapse the
selection before we can copy it).
"""
import ctypes
import threading
import tkinter as tk
from ctypes import wintypes


GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def _virtual_screen_bounds():
    try:
        gsm = ctypes.windll.user32.GetSystemMetrics
        return (gsm(SM_XVIRTUALSCREEN), gsm(SM_YVIRTUALSCREEN),
                gsm(SM_CXVIRTUALSCREEN), gsm(SM_CYVIRTUALSCREEN))
    except Exception:
        return None


class SelectionToolbar:
    """A frameless pill with one or more action buttons anchored near (x, y).

    `buttons` is a list of (label, callback) tuples. Clicking a button fires
    its callback then closes the toolbar. Dismissal is also external via
    close(); the tray app auto-dismisses it on a timer / on typing.
    """

    _lifecycle_lock = threading.Lock()

    # Bounds of the currently-visible toolbar so the global mouse listener can
    # recognize a click on it (and not treat it as a new selection / buffer
    # reset) even when WindowFromPoint disagrees on HighDPI displays.
    _visible_bounds = []
    _bounds_lock = threading.Lock()

    @classmethod
    def point_is_inside_any_visible(cls, x, y):
        with cls._bounds_lock:
            for x1, y1, x2, y2 in cls._visible_bounds:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    return True
        return False

    def __init__(self, x, y, buttons):
        self._x = x
        self._y = y
        self._buttons = list(buttons or [])
        self._window = None
        self._closed = False
        self._click_fired = False
        self._lock = threading.Lock()
        self._registered_bounds = None

    def open(self):
        with SelectionToolbar._lifecycle_lock:
            with self._lock:
                if self._closed:
                    return
            if not self._buttons:
                return
            try:
                self._build_and_show()
            except Exception:
                pass

    def close(self):
        with self._lock:
            self._closed = True

    def _make_handler(self, callback):
        def handler(_event=None):
            if self._click_fired:
                return "break"
            self._click_fired = True
            if callback:
                try:
                    callback()
                except Exception:
                    pass
            self.close()
            return "break"
        return handler

    def _build_and_show(self):
        BORDER = "#4F46E5"   # indigo-600
        BAR_BG = "#6366F1"   # indigo-500 (separators between buttons)
        BTN_BG = "#6366F1"
        HOVER_BG = "#4338CA"  # indigo-700
        TEXT_FG = "#FFFFFF"

        self._window = tk.Tk()
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        try:
            self._window.attributes("-alpha", 0.98)
        except Exception:
            pass
        self._window.geometry("+30000+30000")

        self._apply_no_activate()

        border = tk.Frame(self._window, bg=BORDER, padx=1, pady=1)
        border.pack()
        bar = tk.Frame(border, bg=BAR_BG)
        bar.pack()

        clickables = [self._window, border, bar]
        for idx, (label, callback) in enumerate(self._buttons):
            if idx > 0:
                sep = tk.Frame(bar, bg=BORDER, width=1)
                sep.pack(side="left", fill="y", pady=3)
            btn = tk.Label(
                bar, text=label, bg=BTN_BG, fg=TEXT_FG,
                font=("Segoe UI Semibold", 9), cursor="hand2",
                padx=10, pady=5,
            )
            btn.pack(side="left")
            handler = self._make_handler(callback)
            btn.bind("<Button-1>", handler)

            def _enter(_e, b=btn):
                b.configure(bg=HOVER_BG)

            def _leave(_e, b=btn):
                b.configure(bg=BTN_BG)

            btn.bind("<Enter>", _enter)
            btn.bind("<Leave>", _leave)
            clickables.append(btn)

        # Trailing ✕ to dismiss the toolbar without picking an action.
        if self._buttons:
            sep = tk.Frame(bar, bg=BORDER, width=1)
            sep.pack(side="left", fill="y", pady=3)
            close_btn = tk.Label(
                bar, text="✕", bg=BTN_BG, fg="#C7D2FE",
                font=("Segoe UI", 9), cursor="hand2", padx=9, pady=5,
            )
            close_btn.pack(side="left")
            close_btn.bind("<Button-1>", lambda _e: self.close())
            close_btn.bind("<Enter>", lambda _e: close_btn.configure(bg=HOVER_BG, fg="#FFFFFF"))
            close_btn.bind("<Leave>", lambda _e: close_btn.configure(bg=BTN_BG, fg="#C7D2FE"))

        # Clicking the chrome (the 1px border/background, not a button) dismisses.
        for w in (border, bar):
            w.bind("<Button-1>", lambda _e: self.close())

        self._window.update_idletasks()
        self._position()
        self._window.update_idletasks()

        self._poll_close()
        try:
            self._window.mainloop()
        finally:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None
            if self._registered_bounds is not None:
                with SelectionToolbar._bounds_lock:
                    try:
                        SelectionToolbar._visible_bounds.remove(self._registered_bounds)
                    except ValueError:
                        pass
                self._registered_bounds = None

    def _position(self):
        # Anchor just below-right of the mouse release point so the bar doesn't
        # cover the text the user just selected, but stays close to it.
        x, y = self._x + 2, self._y + 6

        bounds = _virtual_screen_bounds()
        if bounds:
            vx, vy, vw, vh = bounds
        else:
            vx, vy = 0, 0
            vw = self._window.winfo_screenwidth()
            vh = self._window.winfo_screenheight()

        win_w = max(self._window.winfo_reqwidth(), 60)
        win_h = max(self._window.winfo_reqheight(), 24)
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

        self._registered_bounds = (x, y, x + win_w, y + win_h)
        with SelectionToolbar._bounds_lock:
            SelectionToolbar._visible_bounds.append(self._registered_bounds)

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
                    h, GWL_EXSTYLE,
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
