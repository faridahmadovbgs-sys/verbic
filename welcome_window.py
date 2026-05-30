"""First-run welcome dialog. Shown once after install/reset."""
import tkinter as tk
from tkinter import ttk


class WelcomeWindow:
    def __init__(self, current_engine=None, on_done=None):
        # current_engine is accepted for backward-compat with the old call
        # signature but is no longer used — Verbic always runs on the AI engine.
        self._on_done = on_done or (lambda *_a: None)
        self._window = None

    def open(self):
        try:
            self._build()
        except Exception:
            try:
                self._on_done("ai")
            except Exception:
                pass

    def _build(self):
        self._window = tk.Tk()
        self._window.title("Welcome to Verbic")
        self._window.geometry("560x680")
        self._window.resizable(False, False)
        self._window.attributes("-topmost", True)

        outer = ttk.Frame(self._window, padding=20)
        outer.pack(fill="both", expand=True)

        title = tk.Label(
            outer,
            text="Welcome to Verbic",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(anchor="w")
        subtitle = tk.Label(
            outer, text="by Sand Castle LLC",
            font=("Segoe UI", 9), fg="#888",
        )
        subtitle.pack(anchor="w", pady=(0, 12))

        intro = tk.Label(
            outer,
            text=(
                "Verbic corrects what you write in any app — Word, Chrome, "
                "Slack, Discord, Notepad. It runs quietly in your system tray "
                "(near the clock).\n\n"
                "How to use it:\n"
                "  • Type normally. After ~1 second of pause, an inline\n"
                "    overlay appears near your cursor with a corrected version.\n"
                "  • Click the overlay or press Ctrl+Space to apply the suggestion.\n"
                "  • Or, select any text and press Ctrl+Shift+G to fix it directly."
            ),
            justify="left", anchor="w", wraplength=480,
            font=("Segoe UI", 10),
        )
        intro.pack(anchor="w", pady=(0, 12))

        disclaimer = tk.Label(
            outer,
            text=(
                "⚠ Always review automated changes before relying on them. "
                "Verbic is provided AS IS, without warranty. Not for safety-critical, "
                "legal, medical, or regulated use without independent review."
            ),
            justify="left", anchor="w", wraplength=480,
            font=("Segoe UI", 8), fg="#7a4f00", bg="#fff8e1",
            padx=8, pady=6,
        )
        disclaimer.pack(fill="x", pady=(0, 8))

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=4)

        setup_label = tk.Label(
            outer, text="One quick step:",
            font=("Segoe UI", 10, "bold"),
        )
        setup_label.pack(anchor="w", pady=(8, 4))

        tk.Label(
            outer,
            text=(
                "Verbic uses an AI provider to fix grammar and rewrite tone. "
                "After this dialog, open the tray menu → Settings and pick your "
                "provider: OpenAI, Claude, DeepSeek, Grok, Groq, or a custom "
                "OpenAI-compatible endpoint (cloud providers need an API key), "
                "or run a local model with Ollama (no key, no internet)."
            ),
            justify="left", anchor="w", wraplength=480,
            font=("Segoe UI", 9), fg="#444",
        ).pack(anchor="w", pady=(0, 8))

        button_row = ttk.Frame(outer)
        button_row.pack(fill="x", pady=(16, 0))

        def _finish():
            try:
                self._on_done("ai")
            except Exception:
                pass
            self._window.destroy()
            self._window = None

        ttk.Button(button_row, text="Get Started", command=_finish).pack(side="right")

        self._window.protocol("WM_DELETE_WINDOW", _finish)
        self._window.mainloop()
