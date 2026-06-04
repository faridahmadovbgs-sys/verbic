"""AI Provider settings — rendered as an embeddable panel inside the unified
Verbic window (see main_window.py). `SettingsPanel` builds its widgets into a
parent frame; it owns no top-level window of its own."""
import tkinter as tk
from tkinter import ttk
import webbrowser
import threading

from theme import (
    SURFACE, SURFACE_2, BORDER, BORDER_HI, TEXT, MUTED, SECTION,
    ACCENT, GOOD, DANGER, WARN, FONT, PillButton,
)
from config import PROVIDERS, PROVIDER_NAMES
from ollama_client import OllamaClient


# Fastest first — these run live-inline grammar in well under a second.
_FASTEST_OLLAMA_MODEL = "llama3.2:1b"
_RECOMMENDED_OLLAMA_MODELS = ("llama3.2:1b", "llama3.2:3b")
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


class SettingsPanel:
    """Builds the provider/model/key/test UI into `parent` (a frame with
    bg=SURFACE). `on_save(new_config)` is called when the user clicks Save."""

    def __init__(self, parent, config, on_save, build_test_client=None, show_save=True):
        self._parent = parent
        self._config = config
        self._on_save = on_save
        self._build_test_client = build_test_client
        self._show_save = show_save
        self._do_save = None
        self._build()

    def set_config(self, config):
        self._config = config

    def save(self):
        """Commit the current selections (used when the host supplies its own
        action button, e.g. the first-run Setup window). Returns the saved config."""
        if self._do_save:
            self._do_save()
        return self._config

    def _build(self):
        frame = self._parent
        frame.columnconfigure(1, weight=1)

        def section(text, row, **g):
            tk.Label(frame, text=text.upper(), bg=SURFACE, fg=SECTION,
                     font=(FONT, 8, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", **g)

        providers_data = self._config.get("providers", {})

        section("AI Provider", 0, pady=(0, 4))
        provider_var = tk.StringVar(value=self._config.get("provider", "ollama"))
        provider_labels = [PROVIDERS[p]["label"] for p in PROVIDER_NAMES]
        provider_combo = ttk.Combobox(
            frame, textvariable=provider_var, values=provider_labels,
            state="readonly", style="Dark.TCombobox")
        provider_combo.set(PROVIDERS[provider_var.get()]["label"])
        provider_combo.grid(row=1, column=0, columnspan=3, pady=(0, 12), sticky="ew")

        api_key_label = tk.Label(frame, text="API KEY", bg=SURFACE, fg=SECTION, font=(FONT, 8, "bold"))
        api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(frame, textvariable=api_key_var, show="•", style="Dark.TEntry")

        model_label = tk.Label(frame, text="MODEL", bg=SURFACE, fg=SECTION, font=(FONT, 8, "bold"))
        model_var = tk.StringVar()
        model_combo = ttk.Combobox(frame, textvariable=model_var, style="Dark.TCombobox")
        refresh_button = PillButton(frame, "Refresh", kind="ghost", bg=SURFACE, height=30, font_size=9)

        base_url_label = tk.Label(frame, text="BASE URL", bg=SURFACE, fg=SECTION, font=(FONT, 8, "bold"))
        base_url_var = tk.StringVar()
        base_url_entry = ttk.Entry(frame, textvariable=base_url_var, style="Dark.TEntry")

        ollama_status_label = tk.Label(frame, text="", justify="left", anchor="w", wraplength=470,
                                       font=(FONT, 9), fg=MUTED, bg=SURFACE)
        ollama_link_label = tk.Label(frame, text="", cursor="hand2", fg=ACCENT, bg=SURFACE,
                                     font=(FONT, 9, "underline"))
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
            justify="left", anchor="w", wraplength=470, font=(FONT, 8), fg=SECTION, bg=SURFACE)
        model_warning_label = tk.Label(frame, text="", justify="left", anchor="w", wraplength=450,
                                       font=(FONT, 9, "bold"), fg=WARN, bg=SURFACE_2, padx=10, pady=7)

        PROV_ROW_BASE = 2

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
                    fg=DANGER)
                ollama_link_label.configure(text="https://ollama.com")
            elif not installed:
                ollama_status_label.configure(
                    text=(
                        "Ollama is running but no models are installed. For the fastest\n"
                        "experience, open PowerShell and run:\n"
                        f"    ollama pull {_FASTEST_OLLAMA_MODEL}   (⚡ fastest — ~1.3 GB, sub-second)\n"
                        "Then click Refresh."
                    ), fg=DANGER)
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
                api_key_label.grid_remove(); api_key_entry.grid_remove(); api_key_var.set("")
            model_label.grid(row=PROV_ROW_BASE + 4, column=0, columnspan=3, sticky="w", pady=(2, 4))
            model_combo.grid(row=PROV_ROW_BASE + 5, column=0, columnspan=2, pady=(0, 4), sticky="ew")
            if key == "ollama":
                refresh_button.grid(row=PROV_ROW_BASE + 5, column=2, pady=(0, 4), padx=(8, 0), sticky="e")
                ollama_status_label.grid(row=PROV_ROW_BASE + 6, column=0, columnspan=3, sticky="w", pady=(4, 2))
                ollama_link_label.grid(row=PROV_ROW_BASE + 7, column=0, columnspan=3, sticky="w", pady=(0, 4))
                ollama_perf_label.grid(row=PROV_ROW_BASE + 8, column=0, columnspan=3, sticky="w", pady=(2, 6))
                _refresh_ollama_models()
            else:
                refresh_button.grid_remove(); ollama_status_label.grid_remove()
                ollama_link_label.grid_remove(); ollama_perf_label.grid_remove()
                model_combo["values"] = info["models"]
            model_var.set(saved.get("model", info["default_model"]))
            _update_model_warning()
            if key == "custom":
                base_url_label.grid(row=PROV_ROW_BASE + 10, column=0, columnspan=3, sticky="w", pady=(2, 4))
                base_url_entry.grid(row=PROV_ROW_BASE + 11, column=0, columnspan=3, pady=(0, 8), sticky="ew")
                base_url_var.set(saved.get("base_url", ""))
            else:
                base_url_label.grid_remove(); base_url_entry.grid_remove()
                base_url_var.set(info.get("base_url") or "")

        def _on_model_picked(_event=None):
            cleaned = _strip_model_marker(model_var.get())
            if cleaned != model_var.get():
                model_var.set(cleaned)

        def _update_model_warning(*_args):
            if _provider_key() != "ollama":
                model_warning_label.grid_remove(); return
            if _is_reasoning_model(model_var.get()):
                model_warning_label.configure(
                    text=("⚠ Reasoning model selected — expect 15–60s per correction and "
                          "auto-suggest will likely time out. Switch to a small instruct "
                          "model (e.g. llama3.2:3b) for fast inline suggestions."))
                model_warning_label.grid(row=PROV_ROW_BASE + 9, column=0, columnspan=3, sticky="ew", pady=(2, 4))
            else:
                model_warning_label.grid_remove()

        def _on_model_combobox_select(event=None):
            _on_model_picked(event); _update_model_warning()

        # ----- Test -----
        TEST_ROW = PROV_ROW_BASE + 13
        tk.Frame(frame, bg=BORDER, height=1).grid(
            row=TEST_ROW - 1, column=0, columnspan=3, sticky="ew", pady=14)
        section("Test your setup", TEST_ROW, pady=(0, 4))
        test_input = tk.Text(frame, height=2, font=(FONT, 10), wrap="word", relief="flat",
                             borderwidth=0, padx=10, pady=8, bg=SURFACE_2, fg=TEXT,
                             insertbackground=TEXT, highlightthickness=1,
                             highlightbackground=BORDER_HI, highlightcolor=ACCENT)
        test_input.insert("1.0", "i think this aplication is realy usful and i love it")
        test_input.grid(row=TEST_ROW + 1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        test_button = PillButton(frame, "Run test", kind="ghost", bg=SURFACE, height=32)
        test_button.grid(row=TEST_ROW + 2, column=0, sticky="w")
        test_output = tk.Label(frame, text="", justify="left", anchor="w", wraplength=470,
                               font=(FONT, 9), fg=GOOD, bg=SURFACE_2, padx=12, pady=9)

        def _run_test():
            text = test_input.get("1.0", "end").strip()
            if not text:
                return
            test_output.grid(row=TEST_ROW + 3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
            test_output.configure(text="Running…", fg=MUTED, bg=SURFACE_2)

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
                    result = None; err = str(exc)
                else:
                    err = None

                def _show():
                    if result is None:
                        test_output.configure(text=f"✕  Failed: {err or 'provider returned no result'}",
                                              fg=DANGER, bg=SURFACE_2)
                    else:
                        test_output.configure(text=f"✓  {result}", fg=GOOD, bg=SURFACE_2)
                try:
                    self._parent.after(0, _show)
                except Exception:
                    pass

            threading.Thread(target=_worker, daemon=True).start()

        test_button._command = _run_test

        # ----- Save -----
        saved_note = tk.Label(frame, text="", bg=SURFACE, fg=GOOD, font=(FONT, 9, "bold"))
        save_btn = PillButton(frame, "Save provider settings", kind="accent", bg=SURFACE, height=34)

        def _save():
            new_config = dict(self._config)
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
            self._config = new_config
            try:
                self._on_save(new_config)
            except Exception:
                pass
            saved_note.configure(text="✓ Saved")
            try:
                self._parent.after(2000, lambda: saved_note.configure(text=""))
            except Exception:
                pass

        save_btn._command = _save
        self._do_save = _save
        if self._show_save:
            save_btn.grid(row=TEST_ROW + 5, column=0, sticky="w", pady=(18, 0))
            saved_note.grid(row=TEST_ROW + 5, column=1, sticky="w", pady=(18, 0), padx=(10, 0))
            tk.Label(frame, text="Hotkeys & toolbar buttons live in the Shortcuts tab.",
                     bg=SURFACE, fg=MUTED, font=(FONT, 9), wraplength=470, justify="left").grid(
                row=TEST_ROW + 6, column=0, columnspan=3, sticky="w", pady=(14, 0))

        refresh_button._command = _refresh_ollama_models
        provider_combo.bind("<<ComboboxSelected>>", _update_provider_fields)
        model_combo.bind("<<ComboboxSelected>>", _on_model_combobox_select)
        model_var.trace_add("write", lambda *_a: _update_model_warning())
        _update_provider_fields()
