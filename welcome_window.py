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
        tagline = tk.Label(
            outer, text="Write better. Everywhere.",
            font=("Segoe UI", 10, "italic"), fg="#6366F1",
        )
        tagline.pack(anchor="w")
        subtitle = tk.Label(
            outer, text="by Sand Castle LLC",
            font=("Segoe UI", 9), fg="#888",
        )
        subtitle.pack(anchor="w", pady=(0, 12))

        intro = tk.Label(
            outer,
            text=(
                "Verbic is your writing assistant in every app — Word, Chrome, "
                "Gmail, Slack, Discord, Notepad. It lives in your system tray "
                "(the small icons near the clock) and helps you as you type.\n\n"
                "What it can do:\n"
                "  • Fix grammar & spelling — pause while typing and a suggestion\n"
                "    appears; press Ctrl+Space (or click it) to apply.\n"
                "  • Rewrite tone — formal, casual, professional, concise, and more.\n"
                "  • Draft replies for you — highlight a question or message, then\n"
                "    set it as context and let Verbic write the answer.\n"
                "  • Floating buttons — highlight text and a small toolbar pops up\n"
                "    right next to it (Context · Answer · Fix)."
            ),
            justify="left", anchor="w", wraplength=480,
            font=("Segoe UI", 10),
        )
        intro.pack(anchor="w", pady=(0, 12))

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=4)

        setup_label = tk.Label(
            outer, text="Before you start: connect an AI provider",
            font=("Segoe UI", 10, "bold"),
        )
        setup_label.pack(anchor="w", pady=(8, 4))

        # Make the API-key requirement impossible to miss.
        key_note = tk.Label(
            outer,
            text=(
                "🔑  Verbic needs an AI provider to work. Most providers "
                "(OpenAI, Claude, DeepSeek, Grok, Groq) require a free API key "
                "you paste into Settings once. Prefer no key and full privacy? "
                "Install Ollama and run a model locally — no key, no internet."
            ),
            justify="left", anchor="w", wraplength=480,
            font=("Segoe UI", 9), fg="#1e3a8a", bg="#eef2ff",
            padx=10, pady=8,
        )
        key_note.pack(fill="x", pady=(0, 8))

        tk.Label(
            outer,
            text=(
                "Next step: open the tray menu (right-click the V icon near the "
                "clock) → Settings → pick a provider and paste your API key, then "
                "click Save. The “Run test” button there confirms it's working."
            ),
            justify="left", anchor="w", wraplength=480,
            font=("Segoe UI", 9), fg="#444",
        ).pack(anchor="w", pady=(0, 8))

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
