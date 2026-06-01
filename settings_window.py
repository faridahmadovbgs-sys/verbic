import tkinter as tk
from tkinter import ttk
import webbrowser
from config import PROVIDERS, PROVIDER_NAMES
from ollama_client import OllamaClient


_RECOMMENDED_OLLAMA_MODELS = ("llama3.2:3b", "qwen2.5:7b")
_REASONING_MODEL_HINTS = ("r1", "reason", "thinking", "qwq", "o1")


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

    def open(self):
        if self._window is not None:
            self._window.lift()
            return

        self._window = tk.Tk()
        self._window.title("Verbic — Settings")
        self._window.geometry("580x720")
        self._window.resizable(False, False)
        # Bring the window to front and grab focus, otherwise it can appear
        # behind whatever app the user was using.
        try:
            self._window.attributes("-topmost", True)
            self._window.update_idletasks()
            self._window.attributes("-topmost", False)
            self._window.lift()
            self._window.focus_force()
        except Exception:
            pass

        frame = ttk.Frame(self._window, padding=20)
        frame.pack(fill="both", expand=True)

        providers_data = self._config.get("providers", {})

        # ----- Provider -----
        # Verbic runs exclusively on the configured AI provider, so the provider
        # picker is always shown (no engine selector / offline mode).
        ttk.Label(frame, text="AI Provider:").grid(row=0, column=0, sticky="w", pady=5)
        provider_var = tk.StringVar(value=self._config.get("provider", "ollama"))
        provider_labels = [PROVIDERS[p]["label"] for p in PROVIDER_NAMES]
        provider_combo = ttk.Combobox(
            frame, textvariable=provider_var, width=36, values=provider_labels, state="readonly"
        )
        provider_combo.set(PROVIDERS[provider_var.get()]["label"])
        provider_combo.grid(row=0, column=1, columnspan=2, pady=5, padx=(10, 0), sticky="w")

        ttk.Separator(frame, orient="horizontal").grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=4
        )

        api_key_label = ttk.Label(frame, text="API Key:")
        api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(frame, textvariable=api_key_var, width=38, show="*")

        model_label = ttk.Label(frame, text="Model:")
        model_var = tk.StringVar()
        model_combo = ttk.Combobox(frame, textvariable=model_var, width=30)
        refresh_button = ttk.Button(frame, text="Refresh", width=8)

        base_url_label = ttk.Label(frame, text="Base URL:")
        base_url_var = tk.StringVar()
        base_url_entry = ttk.Entry(frame, textvariable=base_url_var, width=38)

        ollama_status_label = tk.Label(
            frame, text="", justify="left", anchor="w", wraplength=500,
            font=("Segoe UI", 9), fg="#444444",
        )
        ollama_link_label = tk.Label(
            frame, text="", cursor="hand2", fg="#1a73e8",
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
            justify="left", anchor="w", wraplength=500,
            font=("Segoe UI", 8), fg="#777777",
        )

        model_warning_label = tk.Label(
            frame, text="", justify="left", anchor="w", wraplength=500,
            font=("Segoe UI", 9, "bold"), fg="#b8860b",
        )

        # ----- Hotkey row -----
        hotkey_label = ttk.Label(frame, text="Hotkeys:")
        hotkey_value = ttk.Label(
            frame, text="Customize in tray → “Shortcuts & Buttons”",
            foreground="gray",
        )

        # ----- Save button -----
        save_button = ttk.Button(frame, text="Save")

        # === Helpers ===
        PROV_ROW_BASE = 2  # provider detail rows start here (after picker + separator)

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
                display_items.append(f"● {name}")
            for name in curated:
                if name not in installed_set:
                    display_items.append(f"○ {name}  (pull required)")
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
                        "Ollama is running but no models are installed. Open PowerShell and run:\n"
                        "    ollama pull llama3.2:3b   (recommended for grammar — ~2 GB)\n"
                        "Then click Refresh."
                    ),
                    fg="#b00020",
                )
                ollama_link_label.configure(text="Browse models: https://ollama.com/library")
            else:
                rec = " · ".join(_RECOMMENDED_OLLAMA_MODELS)
                ollama_status_label.configure(
                    text=(
                        f"{len(installed)} model(s) available. Recommended for grammar: {rec}.\n"
                        "Pull more with:  ollama pull <model-name>"
                    ),
                    fg="#444444",
                )
                ollama_link_label.configure(text="Browse more: https://ollama.com/library")

        def _update_provider_fields(*_args):
            key = _provider_key()
            info = PROVIDERS[key]
            saved = providers_data.get(key, {})

            if info["needs_api_key"]:
                api_key_label.grid(row=PROV_ROW_BASE + 2, column=0, sticky="w", pady=5)
                api_key_entry.grid(row=PROV_ROW_BASE + 2, column=1, columnspan=2, pady=5, padx=(10, 0), sticky="w")
                api_key_var.set(saved.get("api_key", ""))
            else:
                api_key_label.grid_remove()
                api_key_entry.grid_remove()
                api_key_var.set("")

            model_label.grid(row=PROV_ROW_BASE + 3, column=0, sticky="w", pady=5)
            model_combo.grid(row=PROV_ROW_BASE + 3, column=1, pady=5, padx=(10, 0), sticky="w")
            if key == "ollama":
                refresh_button.grid(row=PROV_ROW_BASE + 3, column=2, pady=5, padx=(6, 0), sticky="w")
                ollama_status_label.grid(row=PROV_ROW_BASE + 4, column=0, columnspan=3, sticky="w", pady=(6, 2))
                ollama_link_label.grid(row=PROV_ROW_BASE + 5, column=0, columnspan=3, sticky="w", pady=(0, 4))
                ollama_perf_label.grid(row=PROV_ROW_BASE + 6, column=0, columnspan=3, sticky="w", pady=(2, 2))
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
                base_url_label.grid(row=PROV_ROW_BASE + 7, column=0, sticky="w", pady=5)
                base_url_entry.grid(row=PROV_ROW_BASE + 7, column=1, columnspan=2, pady=5, padx=(10, 0), sticky="w")
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
                model_warning_label.grid(row=PROV_ROW_BASE + 8, column=0, columnspan=3, sticky="w", pady=(2, 2))
            else:
                model_warning_label.grid_remove()

        def _on_model_combobox_select(event=None):
            _on_model_picked(event)
            _update_model_warning()

        # ----- Test correction -----
        test_label = ttk.Label(frame, text="Test:")
        test_input = tk.Text(frame, height=2, width=44, font=("Segoe UI", 9), wrap="word")
        test_input.insert("1.0", "i think this aplication is realy usful and i love it")
        test_button = ttk.Button(frame, text="Run test", width=10)
        test_output = tk.Label(
            frame, text="", justify="left", anchor="w", wraplength=500,
            font=("Segoe UI", 9), fg="#1a4d1a", bg="#f0f9f0",
            padx=8, pady=6, relief="solid", borderwidth=1,
        )

        def _run_test():
            text = test_input.get("1.0", "end").strip()
            if not text:
                return
            test_output.configure(text="Running…", fg="#666666", bg="#f5f5f5")

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
                            text=f"Failed: {err or 'provider returned no result'}",
                            fg="#b00020", bg="#fdf3f3",
                        )
                    else:
                        test_output.configure(text=result, fg="#1a4d1a", bg="#f0f9f0")
                try:
                    self._window.after(0, _show)
                except Exception:
                    pass

            import threading
            threading.Thread(target=_worker, daemon=True).start()

        test_button.configure(command=_run_test)

        # Hotkey + Save row indices live AFTER all dynamic provider rows.
        TEST_ROW = PROV_ROW_BASE + 10
        ttk.Separator(frame, orient="horizontal").grid(
            row=TEST_ROW - 1, column=0, columnspan=3, sticky="ew", pady=8
        )
        test_label.grid(row=TEST_ROW, column=0, sticky="nw", pady=5)
        test_input.grid(row=TEST_ROW, column=1, sticky="w", padx=(10, 0), pady=5)
        test_button.grid(row=TEST_ROW, column=2, sticky="nw", padx=(6, 0), pady=5)
        test_output.grid(row=TEST_ROW + 1, column=0, columnspan=3, sticky="ew", pady=(4, 0))

        hotkey_label.grid(row=TEST_ROW + 2, column=0, sticky="w", pady=5)
        hotkey_value.grid(row=TEST_ROW + 2, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=5)
        save_button.grid(row=TEST_ROW + 3, column=0, columnspan=3, pady=12)

        refresh_button.configure(command=_refresh_ollama_models)
        provider_combo.bind("<<ComboboxSelected>>", _update_provider_fields)
        model_combo.bind("<<ComboboxSelected>>", _on_model_combobox_select)
        model_var.trace_add("write", lambda *_a: _update_model_warning())
        _update_provider_fields()

        def save():
            new_config = dict(self._config)
            # Engine is always AI now; keep the key for backward-compat configs.
            new_config["engine"] = "ai"
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

        save_button.configure(command=save)

        def on_close():
            self._window.destroy()
            self._window = None

        self._window.protocol("WM_DELETE_WINDOW", on_close)
        self._window.mainloop()
