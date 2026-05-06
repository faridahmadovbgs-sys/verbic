import tkinter as tk
from tkinter import ttk


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
        self._window.geometry("420x320")
        self._window.resizable(False, False)

        frame = ttk.Frame(self._window, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Provider:").grid(row=0, column=0, sticky="w", pady=5)
        provider_var = tk.StringVar(value=self._config.get("provider", "ollama"))
        provider_combo = ttk.Combobox(frame, textvariable=provider_var, width=27, values=["ollama", "openai"], state="readonly")
        provider_combo.grid(row=0, column=1, pady=5, padx=(10, 0))

        sep = ttk.Separator(frame, orient="horizontal")
        sep.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(frame, text="Ollama Model:").grid(row=2, column=0, sticky="w", pady=5)
        ollama_model_var = tk.StringVar(value=self._config.get("ollama_model", "llama3.1:8b"))
        ollama_model_entry = ttk.Entry(frame, textvariable=ollama_model_var, width=30)
        ollama_model_entry.grid(row=2, column=1, pady=5, padx=(10, 0))

        sep2 = ttk.Separator(frame, orient="horizontal")
        sep2.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(frame, text="OpenAI API Key:").grid(row=4, column=0, sticky="w", pady=5)
        api_key_var = tk.StringVar(value=self._config.get("api_key", ""))
        api_key_entry = ttk.Entry(frame, textvariable=api_key_var, width=30, show="*")
        api_key_entry.grid(row=4, column=1, pady=5, padx=(10, 0))

        ttk.Label(frame, text="OpenAI Model:").grid(row=5, column=0, sticky="w", pady=5)
        openai_model_var = tk.StringVar(value=self._config.get("openai_model", "gpt-4o-mini"))
        openai_model_combo = ttk.Combobox(frame, textvariable=openai_model_var, width=27, values=[
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-nano",
            "gpt-4.1-mini",
        ])
        openai_model_combo.grid(row=5, column=1, pady=5, padx=(10, 0))

        ttk.Label(frame, text="Hotkey:").grid(row=6, column=0, sticky="w", pady=5)
        ttk.Label(frame, text="Ctrl+Shift+G", foreground="gray").grid(row=6, column=1, sticky="w", padx=(10, 0), pady=5)

        def save():
            new_config = {
                "provider": provider_var.get(),
                "ollama_model": ollama_model_var.get(),
                "api_key": api_key_var.get(),
                "openai_model": openai_model_var.get(),
            }
            self._on_save(new_config)
            self._window.destroy()
            self._window = None

        def on_close():
            self._window.destroy()
            self._window = None

        self._window.protocol("WM_DELETE_WINDOW", on_close)
        ttk.Button(frame, text="Save", command=save).grid(row=7, column=0, columnspan=2, pady=15)

        self._window.mainloop()
