"""Shortcuts & Buttons window — rebind hotkeys and pick floating-toolbar buttons.

Hotkey capture reads the Windows virtual-key code straight from the Tk event
(event.keycode == VK on Windows) and the live modifier state via
GetAsyncKeyState, so a captured binding matches exactly how keyboard_monitor
later detects it.
"""
import ctypes
import tkinter as tk
from tkinter import ttk

from config import HOTKEY_ACTIONS, TOOLBAR_ACTIONS, DEFAULT_HOTKEYS


_VK_CONTROL = 0x11
_VK_SHIFT = 0x10
_VK_ALT = 0x12

# Keysyms that are pure modifiers — ignored as a hotkey's "main" key.
_MODIFIER_KEYSYMS = {
    "Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R",
    "Super_L", "Super_R", "Win_L", "Win_R", "Caps_Lock", "Num_Lock",
}


def _vk_name(vk):
    if vk == 0x20:
        return "Space"
    if vk == 0x0D:
        return "Enter"
    if vk == 0x09:
        return "Tab"
    if 0x70 <= vk <= 0x7B:
        return f"F{vk - 0x6F}"
    if (0x30 <= vk <= 0x39) or (0x41 <= vk <= 0x5A):
        return chr(vk)
    if vk == 0xC0:
        return "`"
    return f"VK{vk}"


def format_binding(binding):
    parts = []
    if binding.get("ctrl"):
        parts.append("Ctrl")
    if binding.get("shift"):
        parts.append("Shift")
    if binding.get("alt"):
        parts.append("Alt")
    parts.append(_vk_name(int(binding.get("vk", 0))))
    return "+".join(parts)


class ShortcutsWindow:
    def __init__(self, config, on_save):
        self._config = config
        self._on_save = on_save
        self._window = None
        self._capturing_action = None
        # Working copies edited in the UI; committed to config on Save.
        self._hotkeys = {
            action: dict(self._config.get("hotkeys", {}).get(action, DEFAULT_HOTKEYS[action]))
            for action, _label in HOTKEY_ACTIONS
        }
        self._binding_buttons = {}
        self._toolbar_vars = {}
        self._show_toolbar_var = None

    def open(self):
        if self._window is not None:
            self._window.lift()
            return

        self._window = tk.Tk()
        self._window.title("Verbic — Shortcuts & Buttons")
        self._window.geometry("460x520")
        self._window.resizable(False, False)
        try:
            self._window.attributes("-topmost", True)
            self._window.update_idletasks()
            self._window.attributes("-topmost", False)
            self._window.lift()
            self._window.focus_force()
        except Exception:
            pass

        pad = ttk.Frame(self._window, padding=18)
        pad.pack(fill="both", expand=True)

        # ----- Keyboard shortcuts -----
        tk.Label(pad, text="Keyboard shortcuts", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(
            pad,
            text="Click a shortcut, then press the key combination you want.",
            font=("Segoe UI", 8), fg="#777",
        ).pack(anchor="w", pady=(0, 8))

        keys_frame = ttk.Frame(pad)
        keys_frame.pack(fill="x")
        for row, (action, label) in enumerate(HOTKEY_ACTIONS):
            tk.Label(keys_frame, text=label, font=("Segoe UI", 9), width=26, anchor="w").grid(
                row=row, column=0, sticky="w", pady=4
            )
            btn = tk.Button(
                keys_frame,
                text=format_binding(self._hotkeys[action]),
                width=18,
                font=("Segoe UI", 9),
                relief="groove",
                command=lambda a=action: self._start_capture(a),
            )
            btn.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=4)
            self._binding_buttons[action] = btn

        ttk.Separator(pad, orient="horizontal").pack(fill="x", pady=14)

        # ----- Floating toolbar -----
        tk.Label(pad, text="Selection toolbar", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(
            pad,
            text="Buttons that appear next to text you highlight with the mouse.",
            font=("Segoe UI", 8), fg="#777",
        ).pack(anchor="w", pady=(0, 8))

        self._show_toolbar_var = tk.BooleanVar(value=self._config.get("selection_button", True))
        ttk.Checkbutton(
            pad, text="Show toolbar when I select text",
            variable=self._show_toolbar_var, command=self._sync_toolbar_enabled,
        ).pack(anchor="w", pady=(0, 6))

        tb_frame = ttk.Frame(pad)
        tb_frame.pack(fill="x", padx=(18, 0))
        saved_toolbar = self._config.get("toolbar", {})
        for action, label in TOOLBAR_ACTIONS:
            var = tk.BooleanVar(value=bool(saved_toolbar.get(action, False)))
            self._toolbar_vars[action] = var
            ttk.Checkbutton(tb_frame, text=label, variable=var).pack(anchor="w", pady=2)
        self._toolbar_checkbuttons = tb_frame
        self._sync_toolbar_enabled()

        # ----- Buttons -----
        btn_row = ttk.Frame(pad)
        btn_row.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(btn_row, text="Restore defaults", command=self._restore_defaults).pack(side="left")
        ttk.Button(btn_row, text="Save", command=self._save).pack(side="right")
        ttk.Button(btn_row, text="Cancel", command=self._close).pack(side="right", padx=(0, 8))

        self._window.bind("<KeyPress>", self._on_key)
        self._window.protocol("WM_DELETE_WINDOW", self._close)
        self._window.mainloop()

    def _sync_toolbar_enabled(self):
        state = "normal" if self._show_toolbar_var.get() else "disabled"
        try:
            for child in self._toolbar_checkbuttons.winfo_children():
                child.configure(state=state)
        except Exception:
            pass

    def _start_capture(self, action):
        # Cancel any in-progress capture first (restore its label).
        if self._capturing_action and self._capturing_action != action:
            self._binding_buttons[self._capturing_action].configure(
                text=format_binding(self._hotkeys[self._capturing_action])
            )
        self._capturing_action = action
        self._binding_buttons[action].configure(text="Press keys…")

    def _on_key(self, event):
        if not self._capturing_action:
            return
        if event.keysym in _MODIFIER_KEYSYMS:
            return  # wait for the real key
        if event.keysym == "Escape":
            # Cancel capture, keep old binding.
            self._binding_buttons[self._capturing_action].configure(
                text=format_binding(self._hotkeys[self._capturing_action])
            )
            self._capturing_action = None
            return

        vk = event.keycode  # Windows: equals the virtual-key code
        try:
            gks = ctypes.windll.user32.GetAsyncKeyState
            ctrl = bool(gks(_VK_CONTROL) & 0x8000)
            shift = bool(gks(_VK_SHIFT) & 0x8000)
            alt = bool(gks(_VK_ALT) & 0x8000)
        except Exception:
            ctrl = shift = alt = False

        binding = {"ctrl": ctrl, "shift": shift, "alt": alt, "vk": int(vk)}
        binding["label"] = format_binding(binding)
        action = self._capturing_action
        self._hotkeys[action] = binding
        self._binding_buttons[action].configure(text=binding["label"])
        self._capturing_action = None

    def _restore_defaults(self):
        for action, _label in HOTKEY_ACTIONS:
            self._hotkeys[action] = dict(DEFAULT_HOTKEYS[action])
            self._binding_buttons[action].configure(text=format_binding(self._hotkeys[action]))

    def _save(self):
        new_config = dict(self._config)
        # Ensure each binding carries a fresh label.
        hotkeys = {}
        for action, _label in HOTKEY_ACTIONS:
            b = dict(self._hotkeys[action])
            b["label"] = format_binding(b)
            hotkeys[action] = b
        new_config["hotkeys"] = hotkeys
        new_config["toolbar"] = {a: bool(v.get()) for a, v in self._toolbar_vars.items()}
        new_config["selection_button"] = bool(self._show_toolbar_var.get())
        try:
            self._on_save(new_config)
        except Exception:
            pass
        self._close()

    def _close(self):
        try:
            self._window.destroy()
        except Exception:
            pass
        self._window = None
