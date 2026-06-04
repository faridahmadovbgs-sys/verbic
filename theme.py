"""Shared visual theme + custom widgets for Verbic's windows.

A dark, modern look inspired by the Capturo app: deep slate background, soft
elevated cards, a sky→blue gradient brand mark, rounded "pill" buttons and
iOS-style toggle switches. Everything here is self-contained (pure Tk Canvas
drawing) so it renders identically on any Windows box without extra deps.
"""
import tkinter as tk
from tkinter import ttk, font as tkfont

# ---- palette (Capturo-inspired slate/sky) ----
BG        = "#0B1120"   # app background  (~slate-950)
SURFACE   = "#131C2E"   # card surface    (~slate-900)
SURFACE_2 = "#1E293B"   # inputs / raised (~slate-800)
SURFACE_3 = "#273449"   # hover surface
BORDER    = "#26344C"   # subtle hairline border
BORDER_HI = "#3A4A66"   # stronger border
TEXT      = "#F1F5F9"   # primary text    (slate-100)
SUBTEXT   = "#CBD5E1"   # secondary text  (slate-300)
MUTED     = "#94A3B8"   # muted text      (slate-400)
SECTION   = "#64748B"   # section caption (slate-500)
ACCENT    = "#3B82F6"   # primary blue    (blue-500)
ACCENT_DK = "#2563EB"   # blue-600 (hover/pressed)
ACCENT_HI = "#60A5FA"   # blue-400
BRAND_TOP = "#7DD3FC"   # sky-300  (badge gradient top)
BRAND_BOT = "#2563EB"   # blue-600 (badge gradient bottom)
DANGER    = "#F87171"   # red-400
DANGER_BG = "#3B1D24"
GOOD      = "#34D399"   # emerald-400
GOOD_DK   = "#10B981"
WARN      = "#FBBF24"   # amber-400

FONT = "Segoe UI"


# ---- low-level helpers ----

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def mix(c1, c2, t):
    """Linear blend between two hex colors (t in 0..1)."""
    a, b = _hex_to_rgb(c1), _hex_to_rgb(c2)
    return _rgb_to_hex(tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle as a smoothed polygon; return the item id."""
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


def set_window_icon(window):
    """Give a Tk window the Verbic logo (taskbar + title bar) instead of the
    default Python/Tk feather. Prefers icon.ico (crisp multi-res on Windows),
    falls back to icon.png via iconphoto. No-ops if the asset isn't found."""
    import os
    import sys
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    try:
        ico = os.path.join(base, "icon.ico")
        if os.path.exists(ico):
            window.iconbitmap(ico)
            return
    except Exception:
        pass
    try:
        png = os.path.join(base, "icon.png")
        img = tk.PhotoImage(file=png)
        window._verbic_icon_ref = img  # keep a reference so it isn't GC'd
        window.iconphoto(True, img)
    except Exception:
        pass


def apply_dark_ttk(root):
    """Style ttk Combobox/Entry/Scrollbar/Separator to match the dark theme."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=SURFACE)
    style.configure("TLabel", background=BG, foreground=TEXT, font=(FONT, 10))

    # Combobox (dark field + dark dropdown list)
    style.configure(
        "Dark.TCombobox", fieldbackground=SURFACE_2, background=SURFACE_2,
        foreground=TEXT, arrowcolor=MUTED, bordercolor=BORDER_HI,
        lightcolor=BORDER_HI, darkcolor=BORDER_HI, borderwidth=1, padding=7,
        selectbackground=ACCENT, selectforeground="#FFFFFF",
    )
    style.map(
        "Dark.TCombobox",
        fieldbackground=[("readonly", SURFACE_2), ("focus", SURFACE_2)],
        bordercolor=[("focus", ACCENT), ("active", BORDER_HI)],
        arrowcolor=[("active", TEXT)],
    )
    root.option_add("*TCombobox*Listbox.background", SURFACE_2)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
    root.option_add("*TCombobox*Listbox.font", (FONT, 10))

    style.configure(
        "Dark.TEntry", fieldbackground=SURFACE_2, foreground=TEXT,
        insertcolor=TEXT, bordercolor=BORDER_HI, lightcolor=BORDER_HI,
        darkcolor=BORDER_HI, borderwidth=1, padding=7,
    )
    style.map("Dark.TEntry", bordercolor=[("focus", ACCENT)])

    style.configure("Dark.Vertical.TScrollbar", background=SURFACE_2,
                    troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
                    relief="flat")
    style.map("Dark.Vertical.TScrollbar", background=[("active", SURFACE_3)])
    style.configure("Dark.TSeparator", background=BORDER)
    return style


# ---- custom widgets ----

class GradientBadge(tk.Canvas):
    """The square 'V' brand mark with a vertical sky→blue gradient."""

    def __init__(self, parent, letter="V", size=40, radius=11, bg=BG, **kw):
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, **kw)
        steps = max(size, 1)
        for i in range(steps):
            color = mix(BRAND_TOP, BRAND_BOT, i / steps)
            self.create_line(0, i, size, i, fill=color)
        # rounded mask corners by overpainting with the bg color
        self._mask_corners(size, radius, bg)
        self.create_text(size / 2, size / 2 + 1, text=letter, fill="#FFFFFF",
                         font=(FONT, int(size * 0.46), "bold"))

    def _mask_corners(self, size, r, bg):
        # paint bg-colored rounded frame so only the rounded interior shows
        self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=90,
                        style="pieslice", outline=bg, fill=bg)
        self.create_arc(size - 2 * r, 0, size, 2 * r, start=0, extent=90,
                        style="pieslice", outline=bg, fill=bg)
        self.create_arc(0, size - 2 * r, 2 * r, size, start=180, extent=90,
                        style="pieslice", outline=bg, fill=bg)
        self.create_arc(size - 2 * r, size - 2 * r, size, size, start=270,
                        extent=90, style="pieslice", outline=bg, fill=bg)


class PillButton(tk.Canvas):
    """A rounded, flat button drawn on a Canvas with hover feedback.

    kind: 'accent' (filled blue), 'ghost' (outlined), 'danger' (red text),
          'soft' (muted filled).
    """

    _KINDS = {
        "accent": dict(fill=ACCENT, hover=ACCENT_DK, fg="#FFFFFF", border=None),
        "ghost":  dict(fill=SURFACE_2, hover=SURFACE_3, fg=TEXT, border=BORDER_HI),
        "soft":   dict(fill=SURFACE, hover=SURFACE_2, fg=SUBTEXT, border=BORDER),
        "danger": dict(fill=SURFACE_2, hover=SURFACE_3, fg=DANGER, border=BORDER_HI),
    }

    def __init__(self, parent, text, command=None, kind="accent",
                 height=34, padx=18, min_width=0, bg=BG, font_size=10, **kw):
        self._spec = dict(self._KINDS.get(kind, self._KINDS["accent"]))
        self._text = text
        self._command = command
        self._font = tkfont.Font(family=FONT, size=font_size, weight="bold")
        w = max(self._font.measure(text) + padx * 2, min_width)
        super().__init__(parent, width=w, height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        self._bw, self._bh = w, height
        self._enabled = True
        self._draw(self._spec["fill"])
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self, fill):
        self.delete("all")
        r = self._bh / 2
        if self._spec["border"]:
            round_rect(self, 1, 1, self._bw - 1, self._bh - 1, r,
                       fill=fill, outline=self._spec["border"], width=1)
        else:
            round_rect(self, 0, 0, self._bw, self._bh, r, fill=fill, outline=fill)
        self.create_text(self._bw / 2, self._bh / 2 + 1, text=self._text,
                         fill=self._spec["fg"], font=self._font)

    def _on_enter(self, _e):
        if self._enabled:
            self._draw(self._spec["hover"])

    def _on_leave(self, _e):
        if self._enabled:
            self._draw(self._spec["fill"])

    def _on_click(self, _e):
        if self._enabled and self._command:
            self._command()

    def set_text(self, text):
        self._text = text
        w = max(self._font.measure(text) + 36, int(self["width"]))
        self.configure(width=w)
        self._bw = w
        self._draw(self._spec["fill"])

    def set_enabled(self, on):
        self._enabled = bool(on)
        self.configure(cursor="hand2" if on else "arrow")
        self._draw(self._spec["fill"] if on else SURFACE)


class ToggleSwitch(tk.Canvas):
    """iOS-style sliding on/off switch. command(bool) fires on toggle.

    The pill track is drawn from two end-circles + a connecting rectangle so the
    rounded ends are perfectly smooth (a smoothed polygon faceted at this size).
    """

    W, H = 44, 24

    def __init__(self, parent, value=False, command=None, bg=SURFACE, **kw):
        super().__init__(parent, width=self.W, height=self.H, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        self._value = bool(value)
        self._command = command
        self._draw()
        self.bind("<Button-1>", self._on_click)

    def _draw(self):
        self.delete("all")
        on = self._value
        track = ACCENT if on else SURFACE_3
        W, H = self.W, self.H
        pad = 1
        r = (H - 2 * pad) / 2            # track radius (rounded ends)
        # Track: left cap + right cap + middle bar, all the same fill.
        self.create_oval(pad, pad, pad + 2 * r, H - pad, fill=track, outline=track)
        self.create_oval(W - pad - 2 * r, pad, W - pad, H - pad, fill=track, outline=track)
        self.create_rectangle(pad + r, pad, W - pad - r, H - pad, fill=track, outline=track)
        # Knob: subtle shadow then a clean white disc.
        kr = r - 4                       # knob radius (inset from track)
        cx = (W - pad - r) if on else (pad + r)
        cy = H / 2
        self.create_oval(cx - kr, cy - kr + 1, cx + kr, cy + kr + 1,
                         fill=mix(track, "#000000", 0.25), outline="")  # soft shadow
        self.create_oval(cx - kr, cy - kr, cx + kr, cy + kr,
                         fill="#FFFFFF", outline="")

    def _on_click(self, _e):
        self._value = not self._value
        self._draw()
        if self._command:
            self._command(self._value)

    def get(self):
        return self._value

    def set(self, value):
        value = bool(value)
        if value != self._value:
            self._value = value
            self._draw()


class ScrollFrame:
    """A vertically scrollable region. Add content to `.body`; pack/grid `.outer`."""

    def __init__(self, parent, bg=BG):
        self.outer = tk.Frame(parent, bg=bg)
        self.canvas = tk.Canvas(self.outer, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar = ttk.Scrollbar(self.outer, orient="vertical",
                                 style="Dark.Vertical.TScrollbar", command=self.canvas.yview)
        self.bar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>",
                       lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))

    def scroll(self, delta):
        self.canvas.yview_scroll(int(-delta / 120), "units")


def make_card(parent, title=None, pad=16):
    """Create an elevated surface card with a hairline border and optional
    section caption. Returns the inner content frame (pack/grid into it)."""
    outer = tk.Frame(parent, bg=BORDER)            # 1px border via bg bleed
    inner = tk.Frame(outer, bg=SURFACE)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    body = tk.Frame(inner, bg=SURFACE)
    body.pack(fill="both", expand=True, padx=pad, pady=(12 if title else pad, pad))
    if title:
        tk.Label(body, text=title.upper(), bg=SURFACE, fg=SECTION,
                 font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 8))
    return outer, body
