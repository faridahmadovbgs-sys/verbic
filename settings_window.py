import tkinter as tk
from tkinter import ttk


class SettingsWindow:
    def __init__(self, current_model, on_save):
        self._current_model = current_model
        self._on_save = on_save
        self._window = None

    def open(self):
        if self._window is not None:
            self._window.lift()
            return

        self._window = tk.Tk()
        self._window.title("Grammar Tool Settings")
        self._window.geometry("350x200")
        self._window.resizable(False, False)

        frame = ttk.Frame(self._window, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Ollama Model:").grid(row=0, column=0, sticky="w", pady=5)
        model_var = tk.StringVar(value=self._current_model)
        model_entry = ttk.Entry(frame, textvariable=model_var, width=25)
        model_entry.grid(row=0, column=1, pady=5, padx=(10, 0))

        ttk.Label(frame, text="Hotkey:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(frame, text="Ctrl+Shift+G", foreground="gray").grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)

        def save():
            self._on_save(model_var.get())
            self._window.destroy()
            self._window = None

        def on_close():
            self._window.destroy()
            self._window = None

        self._window.protocol("WM_DELETE_WINDOW", on_close)
        ttk.Button(frame, text="Save", command=save).grid(row=3, column=0, columnspan=2, pady=20)

        self._window.mainloop()
