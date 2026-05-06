import tkinter as tk
from tkinter import ttk
from config import PROVIDERS, PROVIDER_NAMES


class SettingsWindow:
    def __init__(self, config, on_save):
        self._config = config
        self._on_save = on_save
        self._window = None

    def open(self):
        if self._window is not None:
            self._window.lift()
            return

        self._window = tk.Tk()
        self._window.title("Grammar Tool Settings")
        self._window.geometry("450x280")
        self._window.resizable(False, False)

        frame = ttk.Frame(self._window, padding=20)
        frame.pack(fill="both", expand=True)

        providers_data = self._config.get("providers", {})

        # Provider
        ttk.Label(frame, text="Provider:").grid(row=0, column=0, sticky="w", pady=5)
        provider_var = tk.StringVar(value=self._config.get("provider", "ollama"))
        provider_labels = [PROVIDERS[p]["label"] for p in PROVIDER_NAMES]
        provider_combo = ttk.Combobox(frame, textvariable=provider_var, width=30, values=provider_labels, state="readonly")
        provider_combo.grid(row=0, column=1, pady=5, padx=(10, 0))
        provider_combo.set(PROVIDERS[provider_var.get()]["label"])

        sep = ttk.Separator(frame, orient="horizontal")
        sep.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)

        # API Key
        api_key_label = ttk.Label(frame, text="API Key:")
        api_key_label.grid(row=2, column=0, sticky="w", pady=5)
        api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(frame, textvariable=api_key_var, width=33, show="*")
        api_key_entry.grid(row=2, column=1, pady=5, padx=(10, 0))

        # Model
        ttk.Label(frame, text="Model:").grid(row=3, column=0, sticky="w", pady=5)
        model_var = tk.StringVar()
        model_combo = ttk.Combobox(frame, textvariable=model_var, width=30)
        model_combo.grid(row=3, column=1, pady=5, padx=(10, 0))

        # Base URL (only for Custom)
        base_url_label = ttk.Label(frame, text="Base URL:")
        base_url_var = tk.StringVar()
        base_url_entry = ttk.Entry(frame, textvariable=base_url_var, width=33)

        # Hotkey
        ttk.Label(frame, text="Hotkey:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Label(frame, text="Ctrl+Shift+G  or  Ctrl+`", foreground="gray").grid(row=5, column=1, sticky="w", padx=(10, 0), pady=5)

        def _provider_key():
            label = provider_var.get()
            for key, info in PROVIDERS.items():
                if info["label"] == label:
                    return key
            return "ollama"

        def _update_fields(*_args):
            key = _provider_key()
            info = PROVIDERS[key]
            saved = providers_data.get(key, {})

            # API key
            if info["needs_api_key"]:
                api_key_label.grid()
                api_key_entry.grid()
                api_key_var.set(saved.get("api_key", ""))
            else:
                api_key_label.grid_remove()
                api_key_entry.grid_remove()
                api_key_var.set("")

            # Model
            model_combo["values"] = info["models"]
            model_var.set(saved.get("model", info["default_model"]))

            # Base URL
            if key == "custom":
                base_url_label.grid(row=4, column=0, sticky="w", pady=5)
                base_url_entry.grid(row=4, column=1, pady=5, padx=(10, 0))
                base_url_var.set(saved.get("base_url", ""))
            else:
                base_url_label.grid_remove()
                base_url_entry.grid_remove()
                base_url_var.set(info.get("base_url") or "")

        provider_combo.bind("<<ComboboxSelected>>", _update_fields)
        _update_fields()

        def save():
            key = _provider_key()
            providers_data[key] = {
                "api_key": api_key_var.get(),
                "model": model_var.get(),
                "base_url": base_url_var.get() if key == "custom" else (PROVIDERS[key].get("base_url") or ""),
            }
            new_config = {
                "provider": key,
                "providers": providers_data,
            }
            self._on_save(new_config)
            self._window.destroy()
            self._window = None

        def on_close():
            self._window.destroy()
            self._window = None

        self._window.protocol("WM_DELETE_WINDOW", on_close)
        ttk.Button(frame, text="Save", command=save).grid(row=6, column=0, columnspan=2, pady=12)

        self._window.mainloop()
