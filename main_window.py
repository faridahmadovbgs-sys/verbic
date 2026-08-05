"""Verbic — the single, unified app window.

Everything lives here now: a Capturo-style dark window with a left sidebar that
switches between four panels — General (corrections, tone, context, toolbar),
AI Provider (provider/model/key/test), Shortcuts (hotkeys + toolbar buttons),
and About. The old separate Settings/Shortcuts windows are gone; their UIs are
embedded as panels (settings_window.SettingsPanel / shortcuts_window.ShortcutsPanel).

Window behavior:
  * Minimize  -> normal (sits in the taskbar).
  * Close (X) -> hides to the system tray; the app keeps running. Reopen from
                 the tray (double-click the V icon or "Open Verbic").
  * The app only quits from the tray "Quit" item.
"""
import threading
import tkinter as tk
from tkinter import ttk

import theme as T
from theme import (
    BG, SURFACE, SURFACE_2, SURFACE_3, BORDER, BORDER_HI, TEXT, SUBTEXT, MUTED,
    SECTION, ACCENT, ACCENT_HI, GOOD, WARN, FONT,
    GradientBadge, PillButton, ToggleSwitch, ScrollFrame, make_card,
)
from config import TONES, ACCENTS, LANGUAGES, PROVIDERS
from settings_window import SettingsPanel
from shortcuts_window import ShortcutsPanel
from version import APP_VERSION

_NONE = "None"

_TABS = [
    ("general", "General"),
    ("provider", "AI Provider"),
    ("shortcuts", "Shortcuts"),
    ("about", "About"),
]


class MainWindow:
    def __init__(self, app):
        self._app = app
        self._window = None
        self._pending_tab = "general"
        # General-panel widgets (kept for refresh()).
        self._toggles = {}
        self._tone_var = None
        self._context_var = None
        self._status_label = None
        self._status_dot = None
        self._pause_btn = None
        self._provider_label = None
        self._autostart_note = None
        # Tabs.
        self._panels = {}        # key -> ScrollFrame
        self._nav_items = {}     # key -> (frame, bar, label)
        self._current = None
        self._active_scroll = None
        self._settings_panel = None
        self._shortcuts_panel = None
        self._tone_choices = [(_NONE, None)] \
            + [(label, key) for key, label, _p in TONES] \
            + [(label, key) for key, label, _p in ACCENTS] \
            + [(f"Translate → {label}", key) for key, label, _p in LANGUAGES]
        self._label_to_key = {label: key for label, key in self._tone_choices}
        self._key_to_label = {key: label for label, key in self._tone_choices if key}

    # ---- lifecycle ----

    def open(self, tab=None):
        if tab:
            self._pending_tab = tab
        if self._window is not None:
            try:
                self._window.after(0, lambda: self._reopen(tab))
                return
            except Exception:
                self._window = None
        threading.Thread(target=self._run, daemon=True).start()

    def _reopen(self, tab):
        self._bring_to_front()
        if tab:
            self._show_tab(tab)

    def _run(self):
        try:
            self._build()
        except Exception:
            self._window = None

    def _bring_to_front(self):
        try:
            self._window.deiconify()
            self._window.lift()
            self._window.focus_force()
        except Exception:
            pass

    def _hide(self):
        try:
            self._window.withdraw()
        except Exception:
            pass

    # ---- build ----

    def _build(self):
        self._window = tk.Tk()
        self._window.title("Verbic")
        self._window.geometry("760x680")
        self._window.minsize(700, 600)
        self._window.configure(bg=BG)
        T.set_window_icon(self._window)
        T.apply_dark_ttk(self._window)

        self._build_header()
        self._build_footer()

        # main = sidebar | content
        main = tk.Frame(self._window, bg=BG)
        main.pack(fill="both", expand=True)

        sidebar = tk.Frame(main, bg=BG, width=168)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Frame(main, bg=BORDER, width=1).pack(side="left", fill="y")
        for key, label in _TABS:
            self._nav_items[key] = self._nav_item(sidebar, key, label)

        content = tk.Frame(main, bg=BG)
        content.pack(side="left", fill="both", expand=True)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        for key, _label in _TABS:
            sf = ScrollFrame(content, bg=BG)
            sf.outer.grid(row=0, column=0, sticky="nsew")
            self._panels[key] = sf
        self._build_general(self._panels["general"].body)
        self._build_provider(self._panels["provider"].body)
        self._build_shortcuts(self._panels["shortcuts"].body)
        self._build_about(self._panels["about"].body)

        self._window.bind_all("<MouseWheel>", self._on_wheel)
        self._show_tab(self._pending_tab or "general")
        self._do_refresh()

        self._window.protocol("WM_DELETE_WINDOW", self._hide)
        try:
            self._window.attributes("-topmost", True)
            self._window.update_idletasks()
            self._window.attributes("-topmost", False)
            self._window.lift()
            self._window.focus_force()
        except Exception:
            pass
        self._window.mainloop()
        self._window = None

    def _on_wheel(self, e):
        # If the pointer is over an open combobox dropdown (a Listbox), scroll
        # that list instead of the panel behind it.
        try:
            w = self._window.winfo_containing(e.x_root, e.y_root)
        except Exception:
            w = None
        probe = w
        for _ in range(4):  # the listbox itself, or a child of the popdown
            if probe is None:
                break
            try:
                if probe.winfo_class() == "Listbox":
                    probe.yview_scroll(int(-e.delta / 120), "units")
                    return
                probe = probe.master
            except Exception:
                break
        if self._active_scroll is not None:
            self._active_scroll.scroll(e.delta)

    def _build_header(self):
        header = tk.Frame(self._window, bg=BG, height=72)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        GradientBadge(header, "V", size=42, bg=BG).pack(side="left", padx=(18, 12), pady=15)
        ht = tk.Frame(header, bg=BG)
        ht.pack(side="left", pady=15)
        tk.Label(ht, text="Verbic", bg=BG, fg=TEXT, font=(FONT, 16, "bold")).pack(anchor="w")
        self._status_label = tk.Label(ht, text="Write better. Everywhere.", bg=BG,
                                      fg=MUTED, font=(FONT, 9))
        self._status_label.pack(anchor="w")

        right = tk.Frame(header, bg=BG)
        right.pack(side="right", padx=18)
        self._pause_btn = PillButton(right, "Pause", command=self._toggle_pause,
                                     kind="ghost", bg=BG, height=32)
        self._pause_btn.pack(side="right")
        self._status_dot = tk.Canvas(right, width=12, height=12, bg=BG,
                                     highlightthickness=0, bd=0)
        self._status_dot.pack(side="right", padx=(0, 10))
        tk.Frame(self._window, bg=BORDER, height=1).pack(fill="x", side="top")

    def _build_footer(self):
        tk.Frame(self._window, bg=BORDER, height=1).pack(fill="x", side="bottom")
        footer = tk.Frame(self._window, bg=BG, height=56)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        PillButton(footer, "Hide to tray", command=self._hide, kind="accent",
                   bg=BG, height=34).pack(side="right", padx=18, pady=11)
        tk.Label(footer, text=f"Verbic v{APP_VERSION}", bg=BG, fg=SECTION,
                 font=(FONT, 8)).pack(side="left", padx=18)

    # ---- sidebar nav ----

    def _nav_item(self, parent, key, label):
        row = tk.Frame(parent, bg=BG, height=44)
        row.pack(fill="x")
        row.pack_propagate(False)
        bar = tk.Frame(row, bg=BG, width=3)
        bar.pack(side="left", fill="y")
        lbl = tk.Label(row, text=label, bg=BG, fg=MUTED, font=(FONT, 11),
                       anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="both", expand=True, padx=(14, 0))
        for w in (row, lbl):
            w.bind("<Button-1>", lambda _e, k=key: self._show_tab(k))
            w.bind("<Enter>", lambda _e, k=key: self._nav_hover(k, True))
            w.bind("<Leave>", lambda _e, k=key: self._nav_hover(k, False))
        return (row, bar, lbl)

    def _nav_hover(self, key, on):
        if key == self._current:
            return
        row, _bar, lbl = self._nav_items[key]
        row.configure(bg=SURFACE if on else BG)
        lbl.configure(bg=SURFACE if on else BG, fg=SUBTEXT if on else MUTED)

    def _show_tab(self, key):
        if key not in self._panels:
            key = "general"
        self._current = key
        for k, (row, bar, lbl) in self._nav_items.items():
            active = (k == key)
            row.configure(bg=SURFACE_2 if active else BG)
            bar.configure(bg=ACCENT if active else BG)
            lbl.configure(bg=SURFACE_2 if active else BG,
                          fg=TEXT if active else MUTED,
                          font=(FONT, 11, "bold") if active else (FONT, 11))
        self._panels[key].outer.tkraise()
        self._active_scroll = self._panels[key]

    # ---- General panel ----

    def _build_general(self, body):
        pad = dict(fill="x", padx=20, pady=(0, 12))
        opt = self._app.options

        card, b = make_card(body, "Corrections")
        card.pack(**{**pad, "pady": (18, 12)})
        self._toggle_row(b, "grammar", "Fix grammar & spelling", opt.get("grammar"))
        self._toggle_row(b, "expand", "Expand — elaborate the text", opt.get("expand"))
        self._toggle_row(b, "auto_suggest", "Auto-suggest while typing", opt.get("auto_suggest"))
        self._toggle_row(b, "speculation", "Predictive (Flow) Mode", opt.get("speculation"))

        card, b = make_card(body, "Tone / Accent")
        card.pack(**pad)
        self._tone_var = tk.StringVar()
        combo = ttk.Combobox(b, textvariable=self._tone_var, style="Dark.TCombobox",
                             values=[label for label, _k in self._tone_choices], state="readonly")
        combo.pack(fill="x")
        combo.bind("<<ComboboxSelected>>", lambda _e: self._on_tone())
        tk.Label(b, text="One at a time — picking a tone or accent clears the others.",
                 bg=SURFACE, fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(8, 0))

        card, b = make_card(body, "Writing context")
        card.pack(**pad)
        self._context_var = tk.StringVar(value=self._app._writing_context or "")
        tk.Label(b, text="Tell the AI who you are / what you're writing for.",
                 bg=SURFACE, fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(0, 6))
        ttk.Entry(b, textvariable=self._context_var, style="Dark.TEntry").pack(fill="x")
        crow = tk.Frame(b, bg=SURFACE)
        crow.pack(fill="x", pady=(8, 0))
        PillButton(crow, "Set", command=self._set_context, kind="accent",
                   bg=SURFACE, height=30, font_size=9).pack(side="left")
        PillButton(crow, "Clear", command=self._clear_context, kind="ghost",
                   bg=SURFACE, height=30, font_size=9).pack(side="left", padx=(8, 0))

        card, b = make_card(body, "Floating toolbar")
        card.pack(**pad)
        self._toggle_row(b, "selection_button", "Show action toolbar when I select text",
                         self._app._enable_selection_button)

        card, b = make_card(body, "Startup")
        card.pack(**pad)
        self._toggle_row(b, "start_with_windows", "Start Verbic when Windows starts",
                         self._app.is_autostart_enabled())
        tk.Label(b, text="Verbic launches straight to the system tray — no window pops up.",
                 bg=SURFACE, fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(4, 0))
        self._autostart_note = tk.Label(b, text="", bg=SURFACE, fg=WARN, font=(FONT, 8))
        self._autostart_note.pack(anchor="w")

        card, b = make_card(body, "AI Provider")
        card.pack(**{**pad, "pady": (0, 20)})
        self._provider_label = tk.Label(b, text=self._provider_text(), bg=SURFACE,
                                        fg=SUBTEXT, font=(FONT, 11, "bold"))
        self._provider_label.pack(anchor="w", pady=(0, 8))
        PillButton(b, "Manage provider & model →", command=lambda: self._show_tab("provider"),
                   kind="ghost", bg=SURFACE, height=32).pack(anchor="w")

    def _build_provider(self, body):
        wrap = tk.Frame(body, bg=BG)
        wrap.pack(fill="both", expand=True, padx=20, pady=18)
        _card, inner = make_card(wrap, pad=18)
        _card.pack(fill="x")
        self._settings_panel = SettingsPanel(
            inner, self._app.get_config(), on_save=self._app.save_provider_config,
            build_test_client=self._app.build_test_client)

    def _build_shortcuts(self, body):
        wrap = tk.Frame(body, bg=BG)
        wrap.pack(fill="both", expand=True, padx=20, pady=18)
        _card, inner = make_card(wrap, pad=18)
        _card.pack(fill="x")
        self._shortcuts_panel = ShortcutsPanel(
            inner, self._window, self._app.get_config(),
            on_save=self._app.save_shortcuts_config)

    def _build_about(self, body):
        wrap = tk.Frame(body, bg=BG)
        wrap.pack(fill="both", expand=True, padx=20, pady=18)
        _card, b = make_card(wrap, pad=20)
        _card.pack(fill="x")
        head = tk.Frame(b, bg=SURFACE)
        head.pack(anchor="w", pady=(0, 6))
        GradientBadge(head, "V", size=44, bg=SURFACE).pack(side="left", padx=(0, 12))
        ht = tk.Frame(head, bg=SURFACE)
        ht.pack(side="left")
        tk.Label(ht, text="Verbic", bg=SURFACE, fg=TEXT, font=(FONT, 17, "bold")).pack(anchor="w")
        tk.Label(ht, text=f"Version {APP_VERSION} · © Sand Castle LLC", bg=SURFACE,
                 fg=MUTED, font=(FONT, 9)).pack(anchor="w")
        tk.Label(b, text="Write better. Everywhere.", bg=SURFACE, fg=ACCENT_HI,
                 font=(FONT, 10, "italic")).pack(anchor="w", pady=(0, 14))
        tk.Frame(b, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))
        tk.Label(b, text="DEFAULT HOTKEYS", bg=SURFACE, fg=SECTION,
                 font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Label(b, justify="left", bg=SURFACE, fg=SUBTEXT, font=(FONT, 9), text=(
            "Ctrl+Shift+G    Fix selected text or whole field\n"
            "Ctrl+Space      Apply suggestion (or fix selection)\n"
            "Ctrl+Alt+X      Set highlighted text as writing context\n"
            "Ctrl+Alt+A      Draft an answer using the context"
        )).pack(anchor="w")
        tk.Label(b, justify="left", bg=SURFACE, fg=MUTED, font=(FONT, 8), wraplength=560, text=(
            "\nVerbic is provided AS IS, without warranty. Always review automated "
            "changes before relying on them. Not for safety-critical, legal, medical, "
            "or regulated use without independent review."
        )).pack(anchor="w", pady=(10, 0))
        if hasattr(self._app, "_open_eula"):
            PillButton(b, "View License", command=lambda: self._app._open_eula(),
                       kind="ghost", bg=SURFACE, height=32).pack(anchor="w", pady=(14, 0))

    # ---- general row helper ----

    def _toggle_row(self, parent, name, label, current):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=SURFACE, fg=TEXT, font=(FONT, 10)).pack(side="left")
        sw = ToggleSwitch(row, value=bool(current), bg=SURFACE,
                          command=lambda v, n=name: self._on_toggle(n, v))
        sw.pack(side="right")
        self._toggles[name] = sw

    # ---- handlers ----

    def _on_toggle(self, name, value):
        if name == "selection_button":
            self._app._set_selection_button(bool(value))
        elif name == "start_with_windows":
            ok = self._app._set_autostart(bool(value))
            if self._autostart_note is not None:
                self._autostart_note.configure(
                    text="" if ok else "Windows refused the change — try again as this user.")
        else:
            self._app._set_option(name, bool(value))

    def _on_tone(self):
        key = self._label_to_key.get(self._tone_var.get())
        self._app._apply_tone_selection(key)

    def _toggle_pause(self):
        self._app._toggle_pause()

    def _set_context(self):
        text = (self._context_var.get() or "").strip()
        if text:
            self._app._apply_context(text)
        else:
            self._app._clear_context()

    def _clear_context(self):
        self._context_var.set("")
        self._app._clear_context()

    # ---- refresh ----

    def refresh(self):
        if self._window is None:
            return
        try:
            self._window.after(0, self._do_refresh)
        except Exception:
            pass

    def _do_refresh(self):
        try:
            opt = self._app.options
            for name, sw in self._toggles.items():
                if name == "selection_button":
                    sw.set(bool(self._app._enable_selection_button))
                elif name == "start_with_windows":
                    sw.set(bool(self._app.is_autostart_enabled()))
                else:
                    sw.set(bool(opt.get(name)))
            active = next((k for _l, k in self._tone_choices if k and opt.get(k)), None)
            if self._tone_var is not None:
                self._tone_var.set(self._key_to_label.get(active, _NONE))
            if self._context_var is not None:
                ctx = self._app._writing_context or ""
                if ctx != self._context_var.get():
                    self._context_var.set(ctx)
            if self._provider_label is not None:
                self._provider_label.configure(text=self._provider_text())
            # Keep embedded panels reading the latest config.
            if self._settings_panel is not None:
                self._settings_panel.set_config(self._app.get_config())
            if self._shortcuts_panel is not None:
                self._shortcuts_panel.set_config(self._app.get_config())
            self._refresh_status()
        except Exception:
            pass

    def _refresh_status(self):
        paused = bool(getattr(self._app, "_paused_globally", False))
        if self._status_label is not None:
            self._status_label.configure(
                text="Paused — not correcting" if paused else "Write better. Everywhere.")
        if self._pause_btn is not None:
            self._pause_btn.set_text("Resume" if paused else "Pause")
        if self._status_dot is not None:
            self._status_dot.delete("all")
            self._status_dot.create_oval(1, 1, 11, 11, fill=(WARN if paused else GOOD), outline="")

    def _provider_text(self):
        cfg = self._app._config
        prov = cfg.get("provider", "ollama")
        label = PROVIDERS.get(prov, {}).get("label", prov)
        model = (cfg.get("providers", {}).get(prov, {}) or {}).get("model", "")
        return f"{label} · {model}" if model else label
