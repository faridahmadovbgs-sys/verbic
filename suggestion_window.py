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
    """Read the system caret position via GetGUIThreadInfo.

    Returns None when no usable caret is reported. Chrome / Slack / Discord
    / VS Code / Electron apps draw their own caret instead of using the
    Win32 caret, so they typically report a degenerate (0×0 at 0,0) rect —
    we treat that as "no caret" so the caller falls back to UIA.
    """
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
        r = info.rcCaret
        # A real caret has non-zero height (and usually width 1+). Chrome &
        # friends leave this all zeros, which would otherwise pin the overlay
        # to the window's top-left corner.
        if (r.bottom - r.top) <= 0 or (r.right - r.left) < 0:
            return None
        if r.left == 0 and r.top == 0 and r.right == 0 and r.bottom == 0:
            return None
        pt = wintypes.POINT(r.left, r.bottom)
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


def _get_uia_caret_pos():
    """Return (x, y) of the caret via UIA TextPattern selection.

    This is *the* precise path for Electron apps (Slack, Discord, VS Code,
    Notion, Teams) and modern browsers where there's no Win32 caret. The
    TextPattern's GetSelection() returns one or more TextRange objects whose
    BoundingRectangles report screen-coordinate rects for the selection or
    zero-width caret. We pick the end rect so the overlay lands right under
    where the user is typing, not at the start of a selection.
    """
    result = {"pos": None}

    def worker():
        try:
            import uiautomation as auto
            ctrl = auto.GetFocusedControl()
            if ctrl is None:
                return
            # Try TextPattern2 first (newer UIA), then TextPattern, then
            # TextEditPattern. Most well-behaved Electron apps expose at
            # least one of these.
            tp = None
            for pid in (auto.PatternId.TextPattern2,
                        auto.PatternId.TextPattern,
                        auto.PatternId.TextEditPattern):
                try:
                    tp = ctrl.GetPattern(pid)
                    if tp is not None:
                        break
                except Exception:
                    continue
            if tp is None:
                return
            try:
                selections = tp.GetSelection()
            except Exception:
                return
            if not selections:
                return
            # Use the last selection range, then its last bounding rect: that
            # gives the caret end of a multi-line selection. For a zero-width
            # caret with no selected text, this is just the caret itself.
            text_range = selections[-1]
            try:
                rects = text_range.GetBoundingRectangles()
            except Exception:
                return
            if not rects:
                return
            r = rects[-1]
            if r.bottom <= r.top:
                return
            # Anchor at the bottom-right of the caret rect — slightly to the
            # right of the cursor so the overlay doesn't overlap the next
            # character about to be typed.
            result["pos"] = (int(r.right) if r.right > r.left else int(r.left),
                             int(r.bottom))
        except Exception:
            pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    # Slightly tighter than the older bounding-rect path: TextPattern lookups
    # are normally faster than full-tree walks.
    t.join(0.9)
    return result["pos"]


def _get_focused_control_rect():
    """Return (left, top, right, bottom) of the focused UIA control in screen coords.

    Last-resort UIA path for apps that don't expose TextPattern but at least
    expose a focusable element. The rect covers the entire control, so the
    overlay lands at the bottom-left of the whole textbox — not great in a
    multi-line editor, but better than the foreground-window fallback.
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
    # Chrome's UIA provider can be slow on first call (it lazily builds the
    # accessibility tree). 1.2s is the sweet spot — long enough to succeed,
    # short enough that a hung provider doesn't freeze the overlay.
    t.join(1.2)
    return result["rect"]


def _get_foreground_window_rect():
    """Last-resort: bounding rect of the entire foreground window."""
    try:
        rect = wintypes.RECT()
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return None
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        if rect.right <= rect.left or rect.bottom <= rect.top:
            return None
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        return None


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

    # Serializes tk.Tk() lifecycle across overlays: only one mainloop at a
    # time. Tk is not safe with concurrent roots on different threads — a
    # second overlay constructed while the previous mainloop is still active
    # will silently fail to render on Windows. The class-level lock makes the
    # second .open() block until the first .close() + mainloop exit.
    _lifecycle_lock = threading.Lock()

    # Bounds (x1, y1, x2, y2) of every currently-visible overlay. The global
    # mouse listener consults this as a fallback for WindowFromPoint — which
    # can disagree with pynput's click coords on HighDPI displays and would
    # otherwise miss the overlay, fire _on_typing, and wipe the accept
    # payload before tk's click handler runs.
    _visible_bounds = []
    _bounds_lock = threading.Lock()

    @classmethod
    def point_is_inside_any_visible(cls, x, y):
        with cls._bounds_lock:
            for x1, y1, x2, y2 in cls._visible_bounds:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    return True
        return False

    def __init__(self, suggestion_text, on_click=None):
        self._suggestion = suggestion_text
        self._on_click = on_click
        self._window = None
        self._closed = False
        self._click_fired = False
        self._lock = threading.Lock()
        self._registered_bounds = None

    def open(self):
        with SuggestionWindow._lifecycle_lock:
            # If close() was called before we even got the lock (a fast
            # supersede), skip rendering — the user has already moved on.
            with self._lock:
                if self._closed:
                    return
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
        # Color palette — modern card with an indigo accent stripe. Tk can't
        # do native rounded corners or drop shadows, so we fake depth with a
        # one-pixel border (light gray) around a white card and a thin
        # vertical accent on the left edge.
        BORDER = "#D1D5DB"   # Tailwind slate-300
        CARD_BG = "#FFFFFF"
        ACCENT = "#6366F1"   # Tailwind indigo-500
        TEXT_FG = "#111827"  # Tailwind slate-900
        HINT_FG = "#6B7280"  # Tailwind slate-500
        KBD_BG = "#F3F4F6"   # Tailwind slate-100

        self._window = tk.Tk()
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        # Subtle alpha so the overlay doesn't compete with the user's app for
        # attention. 0.97 ≈ visually opaque but reads as a floating panel.
        try:
            self._window.attributes("-alpha", 0.97)
        except Exception:
            pass
        self._window.geometry("+30000+30000")

        # Apply NOACTIVATE before the window is mapped so it never grabs focus.
        self._apply_no_activate()

        # Outer 1px border via a slightly-larger colored frame.
        border = tk.Frame(self._window, bg=BORDER, padx=1, pady=1)
        border.pack()

        # Horizontal layout: accent stripe | card body.
        body = tk.Frame(border, bg=CARD_BG)
        body.pack(fill="both", expand=True)

        accent = tk.Frame(body, bg=ACCENT, width=3)
        accent.pack(side="left", fill="y")

        card = tk.Frame(body, bg=CARD_BG, cursor="hand2")
        card.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        header = tk.Label(
            card,
            text="Suggested edit",
            bg=CARD_BG,
            fg=ACCENT,
            font=("Segoe UI Semibold", 8),
            cursor="hand2",
        )
        header.pack(anchor="w", padx=12, pady=(8, 0))

        text_label = tk.Label(
            card,
            text=self._suggestion,
            bg=CARD_BG,
            fg=TEXT_FG,
            font=("Segoe UI", 10),
            wraplength=480,
            justify="left",
            cursor="hand2",
        )
        text_label.pack(anchor="w", padx=12, pady=(2, 6))

        # Hint row: a stylized Ctrl+Space "key cap" + action text + dismiss hint.
        hint_row = tk.Frame(card, bg=CARD_BG)
        hint_row.pack(anchor="w", fill="x", padx=10, pady=(0, 8))

        kbd = tk.Label(
            hint_row,
            text=" Ctrl+Space ",
            bg=KBD_BG,
            fg=TEXT_FG,
            font=("Segoe UI", 8),
            bd=1,
            relief="solid",
            padx=2,
            cursor="hand2",
        )
        kbd.pack(side="left")

        hint_label = tk.Label(
            hint_row,
            text="  apply   ·   click to apply   ·   keep typing to dismiss",
            bg=CARD_BG,
            fg=HINT_FG,
            font=("Segoe UI", 8),
            cursor="hand2",
        )
        hint_label.pack(side="left")

        for w in (self._window, border, body, card, header, text_label, hint_row, kbd, hint_label):
            w.bind("<Button-1>", self._handle_click)

        self._window.update_idletasks()
        self._position()
        self._window.update_idletasks()

        self._poll_close()
        try:
            self._window.mainloop()
        finally:
            # Guarantee the root is destroyed even if mainloop exited because
            # of an exception or external close. Without this the next overlay
            # would race against a still-alive Tk interpreter on this thread.
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None
            # Unregister bounds so a fresh click outside doesn't get
            # mistakenly attributed to this (already-gone) overlay.
            if self._registered_bounds is not None:
                with SuggestionWindow._bounds_lock:
                    try:
                        SuggestionWindow._visible_bounds.remove(self._registered_bounds)
                    except ValueError:
                        pass
                self._registered_bounds = None

    def _position(self):
        # Order of preference (most to least precise):
        #   1. System caret — pixel-accurate, works in Win32 controls (Notepad,
        #      Word, classic textboxes).
        #   2. UIA TextPattern caret — Electron / Chromium / modern web text
        #      fields that expose IUIAutomationTextPattern.GetSelection.
        #   3. UIA focused-control bounds — only trusted when it looks like a
        #      single-line input (height ≤ 80 px). Chrome's contenteditable
        #      reports the whole webview here, which is useless for anchoring.
        #   4. Mouse cursor — the user just clicked the input to focus it, so
        #      it's nearly always close to where they're typing. Far better
        #      than the bottom-left of the foreground window when UIA flakes
        #      (notably Chrome's Google homepage and most webmail).
        #   5. Foreground-window bottom-left and (100,100) as last resort.
        pos = _get_caret_screen_pos()
        if pos:
            x, y = pos[0] + 8, pos[1] + 18
        else:
            caret = _get_uia_caret_pos()
            if caret:
                x, y = caret[0] + 4, caret[1] + 6
            else:
                rect = _get_focused_control_rect()
                if rect and (rect[3] - rect[1]) <= 80:
                    left, _top, _right, bottom = rect
                    x, y = left + 8, bottom + 4
                else:
                    cur = _get_cursor_pos()
                    if cur:
                        x, y = cur[0] + 16, cur[1] + 24
                    elif rect:
                        # Tall focused control (e.g. Chrome webview): anchor
                        # at its top-left, not bottom-left — at least it's
                        # near the top of the visible content.
                        left, top, _right, _bottom = rect
                        x, y = left + 8, top + 8
                    else:
                        win_rect = _get_foreground_window_rect()
                        if win_rect:
                            left, top, _right, _bottom = win_rect
                            x, y = left + 40, top + 80
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

        # Register the on-screen bounds so the global mouse listener can
        # recognize a click on this overlay even if WindowFromPoint disagrees.
        self._registered_bounds = (x, y, x + win_w, y + win_h)
        with SuggestionWindow._bounds_lock:
            SuggestionWindow._visible_bounds.append(self._registered_bounds)

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
