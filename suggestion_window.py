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

    def __init__(self, suggestion_text, on_click=None, on_dismiss=None, on_copy=None, header_label=None):
        self._suggestion = suggestion_text
        self._on_click = on_click
        self._on_dismiss = on_dismiss
        self._on_copy = on_copy
        self._header_label = header_label or "Suggested edit"
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

    def _handle_dismiss(self, event=None):
        if self._click_fired:
            return "break"
        self._click_fired = True
        if self._on_dismiss:
            try:
                self._on_dismiss()
            except Exception:
                pass
        self.close()
        return "break"

    def _handle_copy(self, event=None):
        if self._click_fired:
            return "break"
        self._click_fired = True
        if self._on_copy:
            try:
                self._on_copy()
            except Exception:
                pass
        self.close()
        return "break"

    @staticmethod
    def _round_rect_points(x1, y1, x2, y2, r):
        """Polygon points approximating a rounded rectangle. Use with
        create_polygon(..., smooth=True) so the corners spline into curves."""
        return [
            x1 + r, y1,  x2 - r, y1,  x2, y1,
            x2, y1 + r,  x2, y2 - r,  x2, y2,
            x2 - r, y2,  x1 + r, y2,  x1, y2,
            x1, y2 - r,  x1, y1 + r,  x1, y1,
        ]

    def _build_and_show(self):
        # Modern card rendered on a Canvas so we get real rounded corners and a
        # soft(-ish) drop shadow — impossible with plain Tk frames. A magenta
        # color key is made fully transparent, so everything outside the
        # rounded card (corners + shadow margin) disappears, leaving a floating
        # pill instead of a hard rectangle.
        TRANSPARENT = "#FF00FE"
        CARD_BG = "#FFFFFF"
        CARD_BORDER = "#E5E7EB"  # slate-200
        ACCENT = "#6366F1"       # indigo-500
        ACCENT_DK = "#4F46E5"    # indigo-600 (hover)
        TEXT_FG = "#111827"      # slate-900
        HINT_FG = "#6B7280"      # slate-500
        SHADOW = ("#E9EAF0", "#EFF0F5", "#F5F6FA")  # stacked = faux soft shadow

        PAD = 16
        CARD_W = 380
        WRAP = CARD_W - 2 * PAD
        RADIUS = 14
        BTN_H = 30
        SHADOW_OFF = 6  # how far the shadow extends past the card

        self._window = tk.Tk()
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.configure(bg=TRANSPARENT)
        try:
            self._window.attributes("-transparentcolor", TRANSPARENT)
        except Exception:
            pass
        self._window.geometry("+30000+30000")

        # Apply NOACTIVATE before the window is mapped so it never grabs focus.
        self._apply_no_activate()

        canvas = tk.Canvas(
            self._window, bg=TRANSPARENT, highlightthickness=0, bd=0,
            width=CARD_W + SHADOW_OFF, height=400,
        )
        canvas.pack()
        self._canvas = canvas

        import tkinter.font as tkfont
        f_header = tkfont.Font(family="Segoe UI Semibold", size=9)
        f_body = tkfont.Font(family="Segoe UI", size=11)
        f_btn = tkfont.Font(family="Segoe UI Semibold", size=9)
        f_link = tkfont.Font(family="Segoe UI", size=9)

        # --- Header (✦ mode label) + close ✕, measured for layout only ---
        header_y = PAD
        body_y = header_y + 22

        # --- Body text: create first so we can measure its wrapped height ---
        body_item = canvas.create_text(
            PAD, body_y, text=self._suggestion, font=f_body, fill=TEXT_FG,
            width=WRAP, anchor="nw", justify="left",
        )
        bbox = canvas.bbox(body_item)
        body_bottom = bbox[3] if bbox else body_y + 20

        # --- Action row geometry ---
        btn_y = body_bottom + 14
        apply_text = "Apply (Ctrl+Space)"
        apply_w = f_btn.measure(apply_text) + 24
        apply_x1, apply_x2 = PAD, PAD + apply_w
        copy_x = apply_x2 + 14
        copy_w = f_link.measure("Copy")
        dismiss_x = copy_x + copy_w + 18
        card_bottom = btn_y + BTN_H + PAD

        # --- Draw shadow (stacked, offset) then the card, behind everything ---
        for i, col in enumerate(SHADOW):
            off = (len(SHADOW) - i) * 2
            canvas.create_polygon(
                self._round_rect_points(off, off, CARD_W + off - 2,
                                        card_bottom + off - 2, RADIUS),
                fill=col, outline=col, smooth=True,
            )
        card_item = canvas.create_polygon(
            self._round_rect_points(0, 0, CARD_W, card_bottom, RADIUS),
            fill=CARD_BG, outline=CARD_BORDER, smooth=True,
        )
        # Shadows were drawn first (so they're underneath); the card sits above
        # them but below the text/buttons. Body text was drawn before the card,
        # so lift it back on top.
        canvas.tag_raise(body_item)

        # --- Header content on top of the card ---
        canvas.create_text(
            PAD, header_y, text=f"✦  {self._header_label}", font=f_header,
            fill=ACCENT, anchor="nw",
        )
        close_item = canvas.create_text(
            CARD_W - PAD, header_y, text="✕", font=("Segoe UI", 10),
            fill=HINT_FG, anchor="ne",
        )
        canvas.tag_bind(close_item, "<Button-1>", self._handle_dismiss)
        canvas.tag_bind(close_item, "<Enter>", lambda _e: canvas.itemconfigure(close_item, fill=TEXT_FG))
        canvas.tag_bind(close_item, "<Leave>", lambda _e: canvas.itemconfigure(close_item, fill=HINT_FG))

        # --- Apply button (filled, rounded) ---
        apply_rect = canvas.create_polygon(
            self._round_rect_points(apply_x1, btn_y, apply_x2, btn_y + BTN_H, 7),
            fill=ACCENT, outline=ACCENT, smooth=True,
        )
        apply_lbl = canvas.create_text(
            (apply_x1 + apply_x2) / 2, btn_y + BTN_H / 2,
            text=apply_text, font=f_btn, fill="#FFFFFF",
        )
        for it in (apply_rect, apply_lbl):
            canvas.tag_bind(it, "<Button-1>", self._handle_click)
        def _apply_hover(_e, col):
            canvas.itemconfigure(apply_rect, fill=col, outline=col)
        canvas.tag_bind(apply_rect, "<Enter>", lambda e: _apply_hover(e, ACCENT_DK))
        canvas.tag_bind(apply_lbl, "<Enter>", lambda e: _apply_hover(e, ACCENT_DK))
        canvas.tag_bind(apply_rect, "<Leave>", lambda e: _apply_hover(e, ACCENT))
        canvas.tag_bind(apply_lbl, "<Leave>", lambda e: _apply_hover(e, ACCENT))

        # --- Copy + Dismiss text buttons ---
        copy_item = canvas.create_text(
            copy_x, btn_y + BTN_H / 2, text="Copy", font=f_link,
            fill=ACCENT, anchor="w",
        )
        canvas.tag_bind(copy_item, "<Button-1>", self._handle_copy)
        canvas.tag_bind(copy_item, "<Enter>", lambda _e: canvas.itemconfigure(copy_item, fill=ACCENT_DK))
        canvas.tag_bind(copy_item, "<Leave>", lambda _e: canvas.itemconfigure(copy_item, fill=ACCENT))

        dismiss_item = canvas.create_text(
            dismiss_x, btn_y + BTN_H / 2, text="Dismiss", font=f_link,
            fill=HINT_FG, anchor="w",
        )
        canvas.tag_bind(dismiss_item, "<Button-1>", self._handle_dismiss)
        canvas.tag_bind(dismiss_item, "<Enter>", lambda _e: canvas.itemconfigure(dismiss_item, fill=TEXT_FG))
        canvas.tag_bind(dismiss_item, "<Leave>", lambda _e: canvas.itemconfigure(dismiss_item, fill=HINT_FG))

        # Size the canvas/window exactly to the card (+ shadow margin).
        canvas.configure(width=CARD_W + SHADOW_OFF, height=card_bottom + SHADOW_OFF)

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
