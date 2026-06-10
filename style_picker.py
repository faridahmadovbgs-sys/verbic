"""Floating multi-select style picker.

The native tray context menu closes after every click, which makes browsing
tones/accents/languages tedious — each pick means reopening the menu. This
panel stays open while the user clicks around (each click applies instantly
and re-clicking the active item turns it off), and dismisses itself when the
user clicks anywhere outside it (focus loss) or presses Esc.

Follows the app's one-Tk-root-per-thread pattern (like MainWindow and the
suggestion overlay): the panel runs its own mainloop on a daemon thread.
"""
import threading
import tkinter as tk

from config import TONES, ACCENTS, LANGUAGES, TONE_KEYS
from theme import (
    BG, SURFACE, SURFACE_2, SURFACE_3, BORDER, TEXT, MUTED, SECTION,
    ACCENT, ACCENT_DK, FONT,
)
from suggestion_window import _get_cursor_pos, _get_monitor_rect_at


class StylePicker:
    _state_lock = threading.Lock()
    _open = False

    def __init__(self, app):
        self._app = app
        self._window = None
        self._items = {}  # key -> tk.Label

    # ---- lifecycle ----

    def open(self):
        with StylePicker._state_lock:
            if StylePicker._open:
                return
            StylePicker._open = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            self._build()
            self._window.mainloop()
        except Exception:
            pass
        finally:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None
            self._items = {}
            with StylePicker._state_lock:
                StylePicker._open = False

    def _close(self, _event=None):
        try:
            self._window.quit()
        except Exception:
            pass

    # ---- selection ----

    def _active_key(self):
        return next((k for k in TONE_KEYS if self._app.options.get(k)), None)

    def _select(self, key):
        # Re-clicking the active style turns everything off.
        new_key = None if key == self._active_key() else key
        try:
            self._app._apply_tone_selection(new_key)
        except Exception:
            pass
        self._paint_items()

    def _paint_items(self):
        active = self._active_key()
        for key, lbl in self._items.items():
            try:
                if key == active:
                    lbl.configure(bg=ACCENT, fg="#FFFFFF")
                else:
                    lbl.configure(bg=SURFACE, fg=TEXT)
            except Exception:
                pass

    # ---- UI ----

    def _build(self):
        win = tk.Tk()
        self._window = win
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=BORDER)

        outer = tk.Frame(win, bg=BG, padx=14, pady=12)
        outer.pack(padx=1, pady=1)  # 1px hairline border via the root bg

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="Writing style", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).pack(side="left")
        close = tk.Label(header, text="✕", bg=BG, fg=MUTED,
                         font=(FONT, 10), cursor="hand2", padx=6)
        close.pack(side="right")
        close.bind("<Button-1>", self._close)
        close.bind("<Enter>", lambda _e: close.configure(fg=TEXT))
        close.bind("<Leave>", lambda _e: close.configure(fg=MUTED))

        columns = tk.Frame(outer, bg=BG)
        columns.pack()
        for title, entries in (("Tone", TONES),
                               ("Accents", ACCENTS),
                               ("Translate", LANGUAGES)):
            col = tk.Frame(columns, bg=BG)
            col.pack(side="left", anchor="n", padx=(0, 14))
            tk.Label(col, text=title.upper(), bg=BG, fg=SECTION,
                     font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 4))
            for key, label, _prompt in entries:
                self._add_item(col, key, label)

        tk.Label(outer,
                 text="Click to apply · click again to turn off · click anywhere else to close",
                 bg=BG, fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(10, 0))

        self._paint_items()
        self._position(win)

        win.bind("<Escape>", self._close)
        # Click-away dismissal: the panel holds keyboard focus while open, so
        # activating any other window fires FocusOut. Labels never take focus,
        # so clicks inside the panel don't trigger it.
        win.focus_force()
        win.bind("<FocusOut>", self._on_focus_out)

    def _add_item(self, parent, key, label):
        lbl = tk.Label(parent, text=label, bg=SURFACE, fg=TEXT,
                       font=(FONT, 9), anchor="w", padx=10, pady=2,
                       cursor="hand2", width=22)
        lbl.pack(fill="x", pady=1)
        self._items[key] = lbl
        lbl.bind("<Button-1>", lambda _e, k=key: self._select(k))
        lbl.bind("<Enter>", lambda _e, k=key, w=lbl: self._hover(k, w, True))
        lbl.bind("<Leave>", lambda _e, k=key, w=lbl: self._hover(k, w, False))

    def _hover(self, key, lbl, entering):
        if key == self._active_key():
            lbl.configure(bg=ACCENT_DK if entering else ACCENT)
        else:
            lbl.configure(bg=SURFACE_3 if entering else SURFACE)

    def _on_focus_out(self, _event=None):
        # focus_get() is None when focus left the application entirely.
        try:
            if self._window is not None and self._window.focus_get() is None:
                self._close()
        except Exception:
            self._close()

    def _position(self, win):
        win.update_idletasks()
        w = max(win.winfo_reqwidth(), 100)
        h = max(win.winfo_reqheight(), 60)
        cur = _get_cursor_pos() or (200, 200)
        x, y = cur[0] - w // 2, cur[1] - h - 12  # above the cursor (tray area)
        rect = _get_monitor_rect_at(cur[0], cur[1])
        if rect:
            left, top, right, bottom = rect
            x = min(max(x, left + 10), right - w - 10)
            y = min(max(y, top + 10), bottom - h - 10)
        win.geometry(f"+{x}+{y}")
