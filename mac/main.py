"""Verbic Mac Lite — tray app for clipboard-based grammar correction.

Workflow:
  1. User copies any text to the clipboard.
  2. User presses Cmd+Shift+G (or clicks Fix Clipboard in the tray menu).
  3. Verbic reads the clipboard, runs it through the configured engine,
     writes the corrected text back to the clipboard.
  4. A native macOS notification confirms the fix; the user pastes.

This is the macOS Lite version. The full inline-overlay version that mirrors
the Windows feature set is tracked in ../VERBIC-MAC-PLAN.md.
"""
from __future__ import annotations

import sys
import threading
import traceback

try:
    import rumps
    import pyperclip
    from pynput import keyboard
except ImportError as e:
    print(f"Missing dependency: {e}. Run `pip install -r requirements.txt` first.", file=sys.stderr)
    sys.exit(1)

import config as cfgmod
from engines import build_system_prompt, make_engine


HOTKEY_COMBO = "<cmd>+<shift>+g"


class Verbic(rumps.App):
    def __init__(self) -> None:
        super().__init__(
            name="Verbic",
            title="✎",  # menu-bar glyph — replace with an icon file when packaging
            quit_button=None,
        )
        self._cfg = cfgmod.load_config()
        self._engine_lock = threading.Lock()
        self._busy = False
        self._build_menu()
        self._start_hotkey()

    # ---------- menu ----------

    def _build_menu(self) -> None:
        self.menu = [
            rumps.MenuItem("Fix Clipboard (⌘⇧G)", callback=self._on_fix_clicked),
            None,
            self._tone_submenu(),
            rumps.MenuItem("Expand short phrases", callback=lambda s: self._toggle_option("expand")),
            None,
            rumps.MenuItem("Settings…", callback=self._on_settings),
            rumps.MenuItem("About Verbic", callback=self._on_about),
            None,
            rumps.MenuItem("Quit", callback=self._on_quit),
        ]
        # Reflect the Expand checkmark.
        try:
            self.menu["Expand short phrases"].state = 1 if self._cfg.get("options", {}).get("expand") else 0
        except Exception:
            pass

    def _tone_submenu(self) -> rumps.MenuItem:
        root = rumps.MenuItem("Tone")
        opts = self._cfg.get("options", {})
        for opt_key, label, _prompt in cfgmod.TONES:
            item = rumps.MenuItem(label, callback=lambda sender, k=opt_key: self._toggle_tone(k))
            item.state = 1 if opts.get(opt_key) else 0
            root.add(item)
        return root

    # ---------- actions ----------

    def _toggle_tone(self, opt_key: str) -> None:
        # Tones are mutually exclusive — clear the others when enabling one.
        opts = self._cfg.setdefault("options", {})
        turning_on = not opts.get(opt_key, False)
        if turning_on:
            for k in cfgmod.TONE_KEYS:
                opts[k] = False
        opts[opt_key] = turning_on
        cfgmod.save_config(self._cfg)
        self._build_menu()

    def _toggle_option(self, opt_key: str) -> None:
        opts = self._cfg.setdefault("options", {})
        opts[opt_key] = not opts.get(opt_key, False)
        cfgmod.save_config(self._cfg)
        self._build_menu()

    def _on_settings(self, _sender) -> None:
        # rumps Window is modal Tk; fine for the Lite version.
        provider = self._cfg.get("provider", "ollama")
        provider_cfg = self._cfg.get("providers", {}).get(provider, {})
        win = rumps.Window(
            title=f"{cfgmod.PROVIDERS[provider]['label']} settings",
            message=f"Provider: {provider}\nModel: {provider_cfg.get('model', '')}\n\nPaste your API key below (leave blank for local Ollama).",
            default_text=provider_cfg.get("api_key", ""),
            ok="Save",
            cancel="Cancel",
            dimensions=(420, 80),
        )
        response = win.run()
        if response.clicked:
            self._cfg.setdefault("providers", {}).setdefault(provider, {})["api_key"] = response.text.strip()
            cfgmod.save_config(self._cfg)
            rumps.notification("Verbic", "Saved", "API key updated.")

    def _on_about(self, _sender) -> None:
        rumps.alert(
            title="Verbic Mac Lite",
            message="Clipboard-based grammar & tone fixes.\n\n"
                    "Cmd+Shift+G to correct whatever's on your clipboard.\n\n"
                    "Settings live in ~/Library/Application Support/Verbic/config.json",
        )

    def _on_quit(self, _sender) -> None:
        rumps.quit_application()

    def _on_fix_clicked(self, _sender) -> None:
        # Off the main thread so the menu closes immediately.
        threading.Thread(target=self._fix_clipboard, daemon=True).start()

    # ---------- core correction ----------

    def _fix_clipboard(self) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            text = pyperclip.paste() or ""
            if not text.strip():
                rumps.notification("Verbic", "Nothing to fix", "Clipboard is empty.")
                return
            with self._engine_lock:
                engine = make_engine(self._cfg)
                prompt = build_system_prompt(self._cfg.get("options", {}))
                corrected = engine.correct(text, prompt) if hasattr(engine, "correct") else None
            if corrected is None or corrected == text:
                rumps.notification("Verbic", "No changes", "Text already looks clean.")
                return
            pyperclip.copy(corrected)
            preview = corrected[:120] + ("…" if len(corrected) > 120 else "")
            rumps.notification("Verbic", "Fixed — paste it now", preview)
        except Exception:
            traceback.print_exc()
            rumps.notification("Verbic", "Error", "Correction failed. Check Settings.")
        finally:
            self._busy = False

    # ---------- hotkey ----------

    def _start_hotkey(self) -> None:
        def on_activate() -> None:
            self._on_fix_clicked(None)

        def listener_thread() -> None:
            try:
                with keyboard.GlobalHotKeys({HOTKEY_COMBO: on_activate}) as hk:
                    hk.join()
            except Exception:
                # Most likely the user hasn't granted Accessibility permission.
                traceback.print_exc()

        threading.Thread(target=listener_thread, daemon=True).start()


def main() -> None:
    Verbic().run()


if __name__ == "__main__":
    main()
