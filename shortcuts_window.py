"""Shortcuts & Buttons — rendered as an embeddable panel inside the unified
Verbic window (see main_window.py).

Hotkey capture reads the Windows virtual-key code straight from the Tk event
(event.keycode == VK on Windows) and the live modifier state via
GetAsyncKeyState, so a captured binding matches exactly how keyboard_monitor
later detects it.
"""
import ctypes
import tkinter as tk

from theme import (
    SURFACE, SURFACE_2, SURFACE_3, BORDER, BORDER_HI, TEXT, MUTED, SECTION,
    ACCENT, GOOD, FONT, PillButton, ToggleSwitch,
)
from config import HOTKEY_ACTIONS, TOOLBAR_ACTIONS, DEFAULT_HOTKEYS


_VK_CONTROL = 0x11
_VK_SHIFT = 0x10
_VK_ALT = 0x12

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


class ShortcutsPanel:
    """Builds the hotkeys + toolbar-buttons UI into `parent` (bg=SURFACE).
    `toplevel` is the window that receives key events during capture.
    `on_save(new_config)` is called on Save."""

    def __init__(self, parent, toplevel, config, on_save):
        self._parent = parent
        self._toplevel = toplevel
        self._config = config
        self._on_save = on_save
        self._capturing_action = None
        self._hotkeys = {
            action: dict(self._config.get("hotkeys", {}).get(action, DEFAULT_HOTKEYS[action]))
            for action, _label in HOTKEY_ACTIONS
        }
        self._binding_buttons = {}
        self._toolbar_switches = {}
        self._show_toolbar = None
        self._saved_note = None
        self._build()
        toplevel.bind("<KeyPress>", self._on_key, add="+")

    def set_config(self, config):
        self._config = config

    def _build(self):
        p = self._parent

        tk.Label(p, text="KEYBOARD SHORTCUTS", bg=SURFACE, fg=SECTION,
                 font=(FONT, 8, "bold")).pack(anchor="w")
        tk.Label(p, text="Click a shortcut, then press the key combination you want.",
                 bg=SURFACE, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(0, 10))

        keys = tk.Frame(p, bg=SURFACE)
        keys.pack(fill="x")
        keys.columnconfigure(0, weight=1)
        for row, (action, label) in enumerate(HOTKEY_ACTIONS):
            tk.Label(keys, text=label, bg=SURFACE, fg=TEXT, font=(FONT, 10),
                     anchor="w").grid(row=row, column=0, sticky="w", pady=5)
            btn = _KeyButton(keys, format_binding(self._hotkeys[action]),
                             command=lambda a=action: self._start_capture(a))
            btn.grid(row=row, column=1, sticky="e", padx=(10, 0), pady=5)
            self._binding_buttons[action] = btn

        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", pady=16)

        tk.Label(p, text="SELECTION TOOLBAR", bg=SURFACE, fg=SECTION,
                 font=(FONT, 8, "bold")).pack(anchor="w")
        tk.Label(p, text="Buttons that appear next to text you highlight with the mouse.",
                 bg=SURFACE, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(0, 10))

        srow = tk.Frame(p, bg=SURFACE)
        srow.pack(fill="x", pady=(0, 4))
        tk.Label(srow, text="Show toolbar when I select text", bg=SURFACE, fg=TEXT,
                 font=(FONT, 10)).pack(side="left")
        self._show_toolbar = ToggleSwitch(srow, value=self._config.get("selection_button", True),
                                          bg=SURFACE, command=lambda _v: self._sync_toolbar_enabled())
        self._show_toolbar.pack(side="right")

        self._tb_frame = tk.Frame(p, bg=SURFACE)
        self._tb_frame.pack(fill="x", padx=(14, 0), pady=(4, 0))
        saved_toolbar = self._config.get("toolbar", {})
        for action, label in TOOLBAR_ACTIONS:
            r = tk.Frame(self._tb_frame, bg=SURFACE)
            r.pack(fill="x", pady=3)
            lbl = tk.Label(r, text=label, bg=SURFACE, fg=TEXT, font=(FONT, 10))
            lbl.pack(side="left")
            sw = ToggleSwitch(r, value=bool(saved_toolbar.get(action, False)), bg=SURFACE)
            sw.pack(side="right")
            self._toolbar_switches[action] = (sw, lbl)
        self._sync_toolbar_enabled()

        actions = tk.Frame(p, bg=SURFACE)
        actions.pack(fill="x", pady=(20, 0))
        PillButton(actions, "Restore defaults", kind="ghost", bg=SURFACE, height=32,
                   font_size=9).pack(side="left")
        save = PillButton(actions, "Save shortcuts", kind="accent", bg=SURFACE, height=32)
        save._command = self._save
        save.pack(side="right")
        self._saved_note = tk.Label(actions, text="", bg=SURFACE, fg=GOOD, font=(FONT, 9, "bold"))
        self._saved_note.pack(side="right", padx=(0, 10))
        actions.winfo_children()[0]._command = self._restore_defaults

    def _sync_toolbar_enabled(self):
        on = self._show_toolbar.get()
        for sw, lbl in self._toolbar_switches.values():
            lbl.configure(fg=TEXT if on else MUTED)

    def _start_capture(self, action):
        if self._capturing_action and self._capturing_action != action:
            self._binding_buttons[self._capturing_action].set_text(
                format_binding(self._hotkeys[self._capturing_action]))
        self._capturing_action = action
        self._binding_buttons[action].set_text("Press keys…", active=True)

    def _on_key(self, event):
        if not self._capturing_action:
            return
        if event.keysym in _MODIFIER_KEYSYMS:
            return
        if event.keysym == "Escape":
            self._binding_buttons[self._capturing_action].set_text(
                format_binding(self._hotkeys[self._capturing_action]))
            self._capturing_action = None
            return
        vk = event.keycode
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
        self._binding_buttons[action].set_text(binding["label"])
        self._capturing_action = None

    def _restore_defaults(self):
        for action, _label in HOTKEY_ACTIONS:
            self._hotkeys[action] = dict(DEFAULT_HOTKEYS[action])
            self._binding_buttons[action].set_text(format_binding(self._hotkeys[action]))

    def _save(self):
        new_config = dict(self._config)
        hotkeys = {}
        for action, _label in HOTKEY_ACTIONS:
            b = dict(self._hotkeys[action])
            b["label"] = format_binding(b)
            hotkeys[action] = b
        new_config["hotkeys"] = hotkeys
        new_config["toolbar"] = {a: bool(sw.get()) for a, (sw, _l) in self._toolbar_switches.items()}
        new_config["selection_button"] = bool(self._show_toolbar.get())
        self._config = new_config
        try:
            self._on_save(new_config)
        except Exception:
            pass
        if self._saved_note is not None:
            self._saved_note.configure(text="✓ Saved")
            try:
                self._parent.after(2000, lambda: self._saved_note.configure(text=""))
            except Exception:
                pass


class _KeyButton(tk.Label):
    """A small dark, clickable binding chip."""

    def __init__(self, parent, text, command=None):
        super().__init__(parent, text=text, bg=SURFACE_2, fg=TEXT, font=(FONT, 9),
                         padx=14, pady=6, cursor="hand2", width=16)
        self._command = command
        self._active = False
        self.bind("<Button-1>", lambda _e: command() if command else None)
        self.bind("<Enter>", lambda _e: self.configure(bg=SURFACE_3) if not self._active else None)
        self.bind("<Leave>", lambda _e: self.configure(bg=SURFACE_2) if not self._active else None)

    def set_text(self, text, active=False):
        self._active = active
        self.configure(text=text, bg=ACCENT if active else SURFACE_2,
                       fg="#FFFFFF" if active else TEXT)
