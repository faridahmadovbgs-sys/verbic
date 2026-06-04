"""First-run Setup — a mandatory onboarding gate.

Verbic needs a working AI provider (a cloud API key, or a local Ollama model)
before it can do anything useful. This window blocks app startup: the tray icon
and keyboard monitor only start after the user connects a provider and the
connection is verified. Closing the window without finishing quits the app.

It reuses settings_window.SettingsPanel for the provider/model/key/test UI, with
its own "Verify & Finish" button that actually pings the provider before letting
the user through.
"""
import threading
import tkinter as tk

import theme as T
from theme import (
    BG, SURFACE, BORDER, TEXT, SUBTEXT, MUTED, ACCENT, ACCENT_HI, GOOD, DANGER,
    FONT, GradientBadge, PillButton, ScrollFrame, make_card,
)
from settings_window import SettingsPanel


class SetupWindow:
    def __init__(self, config, build_test_client, on_complete):
        self._config = config
        self._build_test_client = build_test_client
        self._on_complete = on_complete
        self._window = None
        self._panel = None
        self._captured = dict(config)
        self._completed = False
        self._status = None
        self._finish_btn = None
        self._verifying = False

    def run(self):
        """Show the setup window (blocking). Returns True if completed."""
        try:
            self._build()
        except Exception:
            # If the UI itself fails to build, don't hard-lock the user out.
            self._completed = True
        return self._completed

    def _build(self):
        self._window = tk.Tk()
        self._window.title("Verbic — Setup")
        self._window.geometry("640x740")
        self._window.minsize(600, 660)
        self._window.configure(bg=BG)
        T.set_window_icon(self._window)
        T.apply_dark_ttk(self._window)

        # Header
        header = tk.Frame(self._window, bg=BG, height=92)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        GradientBadge(header, "V", size=44, bg=BG).pack(side="left", padx=(20, 12), pady=22)
        ht = tk.Frame(header, bg=BG)
        ht.pack(side="left", pady=20)
        tk.Label(ht, text="Welcome to Verbic", bg=BG, fg=TEXT,
                 font=(FONT, 16, "bold")).pack(anchor="w")
        tk.Label(ht, text="Let's connect an AI provider to get started.",
                 bg=BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w")
        tk.Frame(self._window, bg=BORDER, height=1).pack(fill="x", side="top")

        # Footer (status + finish)
        tk.Frame(self._window, bg=BORDER, height=1).pack(fill="x", side="bottom")
        footer = tk.Frame(self._window, bg=BG, height=66)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self._finish_btn = PillButton(footer, "Verify & Finish", kind="accent",
                                      bg=BG, height=38, min_width=150)
        self._finish_btn._command = self._finish
        self._finish_btn.pack(side="right", padx=20, pady=14)
        self._status = tk.Label(footer, text="", bg=BG, fg=MUTED, font=(FONT, 9))
        self._status.pack(side="right", padx=(0, 6))
        PillButton(footer, "Quit", command=self._on_close, kind="ghost",
                   bg=BG, height=38).pack(side="left", padx=20, pady=14)

        # Body
        sf = ScrollFrame(self._window, bg=BG)
        sf.outer.pack(fill="both", expand=True)
        self._window.bind_all("<MouseWheel>", lambda e: sf.scroll(e.delta))
        body = sf.body

        intro_wrap = tk.Frame(body, bg=BG)
        intro_wrap.pack(fill="x", padx=20, pady=(16, 0))
        _c, ib = make_card(intro_wrap, pad=16)
        _c.pack(fill="x")
        tk.Label(ib, text="🔑  Verbic needs an AI provider to work.", bg=SURFACE,
                 fg=TEXT, font=(FONT, 11, "bold")).pack(anchor="w")
        tk.Label(ib, justify="left", bg=SURFACE, fg=SUBTEXT, font=(FONT, 9),
                 wraplength=560, text=(
                     "Pick a cloud provider (OpenAI, Claude, DeepSeek, Grok, Groq) and paste "
                     "a free API key — or choose Ollama to run a model locally with no key and "
                     "full privacy. Use \"Run test\" to try it, then \"Verify & Finish\" below to "
                     "start using Verbic.")).pack(anchor="w", pady=(6, 0))

        panel_wrap = tk.Frame(body, bg=BG)
        panel_wrap.pack(fill="both", expand=True, padx=20, pady=16)
        _card, inner = make_card(panel_wrap, pad=18)
        _card.pack(fill="x")
        self._panel = SettingsPanel(inner, self._config, on_save=self._capture,
                                    build_test_client=self._build_test_client, show_save=False)

        self._window.protocol("WM_DELETE_WINDOW", self._on_close)
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

    def _capture(self, cfg):
        self._captured = cfg

    def _set_status(self, text, color=MUTED):
        if self._status is not None:
            self._status.configure(text=text, fg=color)

    def _finish(self):
        if self._verifying:
            return
        self._panel.save()              # commit current selections -> _capture
        cfg = self._captured
        prov = cfg.get("provider")
        pc = (cfg.get("providers", {}) or {}).get(prov, {}) or {}
        info_needs_key = prov not in ("ollama",)
        if info_needs_key and prov != "custom" and not (pc.get("api_key", "") or "").strip():
            self._set_status("Enter your API key first.", DANGER)
            return

        self._verifying = True
        self._set_status("Verifying connection…", ACCENT_HI)
        self._finish_btn.set_enabled(False)

        def _worker():
            ok, err = False, None
            try:
                client = self._build_test_client("ai", prov, pc)
                if client is None:
                    err = "could not build a client for this provider"
                else:
                    from prompt_builder import PromptBuilder
                    res = client.generate(PromptBuilder().build("test", {"grammar": True}))
                    ok = res is not None
                    if not ok:
                        err = "provider returned no result"
            except Exception as exc:
                err = str(exc)

            def _done():
                self._verifying = False
                self._finish_btn.set_enabled(True)
                if ok:
                    self._set_status("✓ Connected", GOOD)
                    self._completed = True
                    try:
                        self._on_complete(cfg)
                    except Exception:
                        pass
                    try:
                        self._window.destroy()
                    except Exception:
                        pass
                else:
                    self._set_status(f"✕ {err or 'connection failed'} — check and retry.", DANGER)
            try:
                self._window.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _on_close(self):
        # User bailed without connecting a provider -> app will quit.
        self._completed = False
        try:
            self._window.destroy()
        except Exception:
            pass
