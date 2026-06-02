import tkinter as tk
from tkinter import ttk
import webbrowser
from config import PROVIDERS, PROVIDER_NAMES
from ollama_client import OllamaClient


# Fastest first — these run live-inline grammar in well under a second.
_FASTEST_OLLAMA_MODEL = "llama3.2:1b"
_RECOMMENDED_OLLAMA_MODELS = ("llama3.2:1b", "llama3.2:3b")
_REASONING_MODEL_HINTS = ("r1", "reason", "thinking", "qwq", "o1")

# Palette (Tailwind-ish).
HEADER_BG = "#6366F1"   # indigo-500
ACCENT = "#6366F1"
ACCENT_DK = "#4F46E5"   # indigo-600
BG = "#FFFFFF"
PANEL = "#F8F9FC"       # very light gray panel
BORDER = "#E5E7EB"      # slate-200
TEXT = "#111827"        # slate-900
MUTED = "#6B7280"       # slate-500
SECTION = "#9CA3AF"     # slate-400 (section captions)
LINK = "#4F46E5"


def _is_reasoning_model(name):
    if not name:
        return False
    lowered = name.lower()
    return any(hint in lowered for hint in _REASONING_MODEL_HINTS)


def _strip_model_marker(value):
    """Remove the ●/○ install-status prefix and pull suffix from a display string."""
    if not value:
        return value
    s = value
    if s.startswith(("● ", "○ ")):
        s = s[2:]
    if "  (" in s:
        s = s.split("  (")[0]
    return s.strip()


class SettingsWindow:
    def __init__(self, config, on_save, build_test_client=None):
        self._config = config
        self._on_save = on_save
        # Callback the host (tray_app) supplies that builds an AI client for
        # whatever provider/model is currently selected in the UI — used so
        # the "Test correction" button can hit the live config without needing
        # to save first.
        self._build_test_client = build_test_client
        self._window = None

    def _init_style(self):
        style = ttk.Style(self._window)
        try:
            style.theme_use("clam")  # only theme that honors custom colors well
        except Exception:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=BG, foreground=SECTION,
                        font=("Segoe UI Semibold", 8))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 9), padding=6,
                        background=PANEL, foreground=TEXT, borderwidth=1)
        style.map("TButton", background=[("active", "#EEF0F5")])
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(18, 8),
                        background=ACCENT, foreground="#FFFFFF", borderwidth=0)
        style.map("Accent.TButton",
                  background=[("active", ACCENT_DK), ("pressed", ACCENT_DK)],
                  foreground=[("disabled", "#E5E7EB")])
        style.configure("TCombobox", padding=5, foreground=TEXT)
        style.configure("TEntry", padding=5, foreground=TEXT)
        style.configure("TSeparator", background=BORDER)

    def open(self):
        if self._window is not None:
            self._window.lift()
            return

        self._window = tk.Tk()
        self._window.title("Verbic — Settings")
        self._window.geometry("600x700")
        self._window.minsize(600, 560)
        self._window.resizable(False, True)
        self._window.configure(bg=BG)
        try:
            self._window.attributes("-topmost", True)
            self._window.update_idletasks()
            self._window.attributes("-topmost", False)
            self._window.lift()
            self._window.focus_force()
        except Exception:
            pass

        self._init_style()

        # ---------- Header ----------
        header = tk.Frame(self._window, bg=HEADER_BG, height=72)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        hin = tk.Frame(header, bg=HEADER_BG)
        hin.pack(side="left", padx=20, pady=14)
        badge = tk.Label(hin, text="V", bg="#FFFFFF", fg=HEADER_BG,
                         font=("Segoe UI", 16, "bold"), width=2, height=1)
        badge.pack(side="left", padx=(0, 12))
        htext = tk.Frame(hin, bg=HEADER_BG)
        htext.pack(side="left")
        tk.Label(htext, text="Settings", bg=HEADER_BG, fg="#FFFFFF",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(htext, text="Write better. Everywhere.", bg=HEADER_BG, fg="#E0E7FF",
                 font=("Segoe UI", 9, "italic")).pack(anchor="w")

        # ---------- Footer (packed before content so it stays pinned) ----------
        footer = tk.Frame(self._window, bg=PANEL, height=60)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Frame(self._window, bg=BORDER, height=1).pack(fill="x", side="bottom")
        save_button = ttk.Button(footer, text="Save", style="Accent.TButton")
        save_button.pack(side="right", padx=20, pady=12)
        cancel_button = ttk.Button(footer, text="Cancel")
        cancel_button.pack(side="right", padx=(0, 8), pady=12)

        # ---------- Content ----------
        frame = ttk.Frame(self._window, padding=(22, 18))
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        providers_data = self._config.get("providers", {})

        # ----- Provider -----
        ttk.Label(frame, text="AI PROVIDER", style="Section.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        provider_var = tk.StringVar(value=self._config.get("provider", "ollama"))
        provider_labels = [PROVIDERS[p]["label"] for p in PROVIDER_NAMES]
        provider_combo = ttk.Combobox(
            frame, textvariable=provider_var, width=40, values=provider_labels, state="readonly"
        )
        provider_combo.set(PROVIDERS[provider_var.get()]["label"])
        provider_combo.grid(row=1, column=0, columnspan=3, pady=(0, 12), sticky="ew")

        api_key_label = ttk.Label(frame, text="API KEY", style="Section.TLabel")
        api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(frame, textvariable=api_key_var, show="•")

        model_label = ttk.Label(frame, text="MODEL", style="Section.TLabel")
        model_var = tk.StringVar()
        model_combo = ttk.Combobox(frame, textvariable=model_var, width=32)
        refresh_button = ttk.Button(frame, text="Refresh", width=9)

        base_url_label = ttk.Label(frame, text="BASE URL", style="Section.TLabel")
        base_url_var = tk.StringVar()
        base_url_entry = ttk.Entry(frame, textvariable=base_url_var)

        ollama_status_label = tk.Label(
            frame, text="", justify="left", anchor="w", wraplength=520,
            font=("Segoe UI", 9), fg=MUTED, bg=BG,
        )
        ollama_link_label = tk.Label(
            frame, text="", cursor="hand2", fg=LINK, bg=BG,
            font=("Segoe UI", 9, "underline"),
        )
        ollama_link_label.bind("<Button-1>", lambda _e: webbrowser.open("https://ollama.com"))

        ollama_perf_label = tk.Label(
            frame,
            text=(
                "Note: local Ollama models run on your CPU/GPU. Expect a few seconds per "
                "correction; the first request after a model is loaded is slowest. "
                "Reasoning models (deepseek-r1, qwq, o1-style) think before answering and "
                "can take 30+ seconds — they are NOT recommended for live auto-suggest. "
                "For best results pick a small instruct model like llama3.2:3b."
            ),
            justify="left", anchor="w", wraplength=520,
            font=("Segoe UI", 8), fg=SECTION, bg=BG,
        )

        model_warning_label = tk.Label(
            frame, text="", justify="left", anchor="w", wraplength=520,
            font=("Segoe UI", 9, "bold"), fg="#b8860b", bg="#FEF9E7",
            padx=8, pady=5,
        )

        # === Helpers ===
        PROV_ROW_BASE = 2  # provider detail rows start here

        def _provider_key():
            label = provider_var.get()
            for key, info in PROVIDERS.items():
                if info["label"] == label:
                    return key
            return "ollama"

        def _refresh_ollama_models():
            running, installed = OllamaClient.get_status()
            installed_set = set(installed)
            curated = list(PROVIDERS["ollama"]["models"])

            display_items = []
            for name in installed:
                tag = "  ⚡ fastest" if name == _FASTEST_OLLAMA_MODEL else ""
                display_items.append(f"● {name}{tag}")
            for name in curated:
                if name not in installed_set:
                    tag = "  ⚡ fastest" if name == _FASTEST_OLLAMA_MODEL else ""
                    display_items.append(f"○ {name}{tag}  (pull required)")
            model_combo["values"] = display_items

            if not running:
                ollama_status_label.configure(
                    text="Ollama is not running. Install it, start the service, then click Refresh.",
                    fg="#b00020",
                )
                ollama_link_label.configure(text="https://ollama.com")
            elif not installed:
                ollama_status_label.configure(
                    text=(
                        "Ollama is running but no models are installed. For the fastest\n"
                        "experience, open PowerShell and run:\n"
                        f"    ollama pull {_FASTEST_OLLAMA_MODEL}   (⚡ fastest — ~1.3 GB, sub-second)\n"
                        "Then click Refresh."
                    ),
                    fg="#b00020",
                )
                ollama_link_label.configure(text="Browse models: https://ollama.com/library")
            else:
                has_fast = _FASTEST_OLLAMA_MODEL in installed_set
                if has_fast:
                    txt = (f"{len(installed)} model(s) available. ⚡ {_FASTEST_OLLAMA_MODEL} is the "
                           f"fastest — pick it for instant inline suggestions.")
                else:
                    txt = (f"{len(installed)} model(s) available. For the fastest experience run:  "
                           f"ollama pull {_FASTEST_OLLAMA_MODEL}  (⚡ ~1.3 GB), then Refresh.")
                ollama_status_label.configure(text=txt, fg=MUTED)
                ollama_link_label.configure(text="Browse more: https://ollama.com/library")

        def _update_provider_fields(*_args):
            key = _provider_key()
            info = PROVIDERS[key]
            saved = providers_data.get(key, {})

            if info["needs_api_key"]:
                api_key_label.grid(row=PROV_ROW_BASE + 2, column=0, columnspan=3, sticky="w", pady=(2, 4))
                api_key_entry.grid(row=PROV_ROW_BASE + 3, column=0, columnspan=3, pady=(0, 12), sticky="ew")
                api_key_var.set(saved.get("api_key", ""))
            else:
                api_key_label.grid_remove()
                api_key_entry.grid_remove()
                api_key_var.set("")

            model_label.grid(row=PROV_ROW_BASE + 4, column=0, columnspan=3, sticky="w", pady=(2, 4))
            model_combo.grid(row=PROV_ROW_BASE + 5, column=0, columnspan=2, pady=(0, 4), sticky="ew")
            if key == "ollama":
                refresh_button.grid(row=PROV_ROW_BASE + 5, column=2, pady=(0, 4), padx=(8, 0), sticky="e")
                ollama_status_label.grid(row=PROV_ROW_BASE + 6, column=0, columnspan=3, sticky="w", pady=(4, 2))
                ollama_link_label.grid(row=PROV_ROW_BASE + 7, column=0, columnspan=3, sticky="w", pady=(0, 4))
                ollama_perf_label.grid(row=PROV_ROW_BASE + 8, column=0, columnspan=3, sticky="w", pady=(2, 6))
                _refresh_ollama_models()
            else:
                refresh_button.grid_remove()
                ollama_status_label.grid_remove()
                ollama_link_label.grid_remove()
                ollama_perf_label.grid_remove()
                model_combo["values"] = info["models"]
            model_var.set(saved.get("model", info["default_model"]))
            _update_model_warning()

            if key == "custom":
                base_url_label.grid(row=PROV_ROW_BASE + 10, column=0, columnspan=3, sticky="w", pady=(2, 4))
                base_url_entry.grid(row=PROV_ROW_BASE + 11, column=0, columnspan=3, pady=(0, 8), sticky="ew")
                base_url_var.set(saved.get("base_url", ""))
            else:
                base_url_label.grid_remove()
                base_url_entry.grid_remove()
                base_url_var.set(info.get("base_url") or "")

        def _on_model_picked(_event=None):
            cleaned = _strip_model_marker(model_var.get())
            if cleaned != model_var.get():
                model_var.set(cleaned)

        def _update_model_warning(*_args):
            if _provider_key() != "ollama":
                model_warning_label.grid_remove()
                return
            if _is_reasoning_model(model_var.get()):
                model_warning_label.configure(
                    text=(
                        "⚠ Reasoning model selected — expect 15–60s per correction and "
                        "auto-suggest will likely time out. Switch to a small instruct "
                        "model (e.g. llama3.2:3b) for fast inline suggestions."
                    )
                )
                model_warning_label.grid(row=PROV_ROW_BASE + 9, column=0, columnspan=3, sticky="ew", pady=(2, 4))
            else:
                model_warning_label.grid_remove()

        def _on_model_combobox_select(event=None):
            _on_model_picked(event)
            _update_model_warning()

        # ----- Test -----
        TEST_ROW = PROV_ROW_BASE + 13
        ttk.Separator(frame, orient="horizontal").grid(
            row=TEST_ROW - 1, column=0, columnspan=3, sticky="ew", pady=12
        )
        ttk.Label(frame, text="TEST YOUR SETUP", style="Section.TLabel").grid(
            row=TEST_ROW, column=0, columnspan=3, sticky="w", pady=(0, 4))
        test_input = tk.Text(frame, height=2, font=("Segoe UI", 10), wrap="word",
                             relief="solid", borderwidth=1, padx=8, pady=6,
                             highlightthickness=1, highlightbackground=BORDER,
                             highlightcolor=ACCENT)
        test_input.insert("1.0", "i think this aplication is realy usful and i love it")
        test_input.grid(row=TEST_ROW + 1, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        test_button = ttk.Button(frame, text="Run test", width=12)
        test_button.grid(row=TEST_ROW + 2, column=0, sticky="w")
        test_output = tk.Label(
            frame, text="", justify="left", anchor="w", wraplength=520,
            font=("Segoe UI", 9), fg="#166534", bg="#F0FDF4",
            padx=10, pady=8, relief="flat", borderwidth=0,
        )

        def _run_test():
            text = test_input.get("1.0", "end").strip()
            if not text:
                return
            test_output.grid(row=TEST_ROW + 3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
            test_output.configure(text="Running…", fg=MUTED, bg=PANEL)

            def _worker():
                try:
                    client = self._build_test_client("ai", _provider_key(), {
                        "api_key": api_key_var.get(),
                        "model": _strip_model_marker(model_var.get()) if _provider_key() == "ollama" else model_var.get(),
                        "base_url": base_url_var.get() if _provider_key() == "custom" else (PROVIDERS[_provider_key()].get("base_url") or ""),
                    }) if self._build_test_client else None
                    if client is None:
                        result = None
                    else:
                        from prompt_builder import PromptBuilder
                        result = client.generate(PromptBuilder().build(text, {"grammar": True}))
                except Exception as exc:
                    result = None
                    err = str(exc)
                else:
                    err = None

                def _show():
                    if result is None:
                        test_output.configure(
                            text=f"✕  Failed: {err or 'provider returned no result'}",
                            fg="#991B1B", bg="#FEF2F2",
                        )
                    else:
                        test_output.configure(text=f"✓  {result}", fg="#166534", bg="#F0FDF4")
                try:
                    self._window.after(0, _show)
                except Exception:
                    pass

            import threading
            threading.Thread(target=_worker, daemon=True).start()

        test_button.configure(command=_run_test)

        # ----- Hotkeys hint -----
        ttk.Label(
            frame, text="Hotkeys & toolbar buttons: customize in the tray menu → "
                        "“Shortcuts & Buttons”.",
            style="Muted.TLabel", wraplength=540,
        ).grid(row=TEST_ROW + 4, column=0, columnspan=3, sticky="w", pady=(14, 0))

        refresh_button.configure(command=_refresh_ollama_models)
        provider_combo.bind("<<ComboboxSelected>>", _update_provider_fields)
        model_combo.bind("<<ComboboxSelected>>", _on_model_combobox_select)
        model_var.trace_add("write", lambda *_a: _update_model_warning())
        _update_provider_fields()

        def save():
            new_config = dict(self._config)
            new_config["engine"] = "ai"  # always AI; kept for backward-compat
            key = _provider_key()
            model_name = _strip_model_marker(model_var.get()) if key == "ollama" else model_var.get()
            providers_data[key] = {
                "api_key": api_key_var.get(),
                "model": model_name,
                "base_url": base_url_var.get() if key == "custom" else (PROVIDERS[key].get("base_url") or ""),
            }
            new_config["provider"] = key
            new_config["providers"] = providers_data
            self._on_save(new_config)
            self._window.destroy()
            self._window = None

        def on_close():
            self._window.destroy()
            self._window = None

        save_button.configure(command=save)
        cancel_button.configure(command=on_close)
        self._window.protocol("WM_DELETE_WINDOW", on_close)
        self._window.mainloop()
