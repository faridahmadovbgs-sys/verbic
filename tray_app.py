import pystray
import subprocess
import threading
from PIL import Image
from keyboard_monitor import KeyboardMonitor
from text_replacer import TextReplacer
from ollama_client import OllamaClient
from openai_client import OpenAICompatibleClient
from claude_client import ClaudeClient
from prompt_builder import PromptBuilder
from suggestion_window import SuggestionWindow
from settings_window import SettingsWindow
from config import load_config, save_config, PROVIDERS, DEFAULT_OPTIONS
from text_reader import read_focused_text
from focus_watcher import FocusWatcher
from debug_log import log as _dlog


class GrammarTrayApp:
    def __init__(self):
        self._config = load_config()
        self.options = dict(DEFAULT_OPTIONS)
        self.options.update(self._config.get("options") or {})
        self._build_client()
        self.prompt_builder = PromptBuilder()
        self.replacer = TextReplacer()
        self._suggestion_window = None
        self._pending_corrected = None
        self._pending_char_count = 0
        self._suggest_seq = 0
        self._suggest_lock = threading.Lock()
        self.monitor = KeyboardMonitor(
            on_hotkey=self._on_hotkey,
            on_text_ready=self._on_text_ready,
            on_accept_hotkey=self._on_accept_hotkey,
            on_typing=self._on_typing,
        )
        self._focus_watcher = FocusWatcher(on_focus_change=self._on_foreground_changed)
        self._icon = None

    def _build_client(self):
        provider = self._config.get("provider", "ollama")
        provider_config = self._config.get("providers", {}).get(provider, {})

        if provider == "ollama":
            self.client = OllamaClient(
                model=provider_config.get("model", "llama3.1:8b"),
            )
        elif provider == "claude":
            self.client = ClaudeClient(
                api_key=provider_config.get("api_key", ""),
                model=provider_config.get("model", "claude-sonnet-4-20250514"),
            )
        else:
            info = PROVIDERS.get(provider, PROVIDERS["custom"])
            base_url = provider_config.get("base_url") or info.get("base_url") or ""
            self.client = OpenAICompatibleClient(
                api_key=provider_config.get("api_key", ""),
                model=provider_config.get("model", info.get("default_model", "")),
                base_url=base_url,
                provider_name=info.get("label", provider),
            )

        if provider == "ollama":
            # Pre-load the model so the first auto-suggest doesn't pay the
            # cold-start penalty (which otherwise causes the in-flight request
            # to be invalidated when the user keeps typing).
            threading.Thread(target=self.client.warm_up, daemon=True).start()

    def _toggle_option(self, name):
        def handler(icon, item):
            if name == "formal" and not self.options["formal"]:
                self.options["casual"] = False
            elif name == "casual" and not self.options["casual"]:
                self.options["formal"] = False
            elif name == "concise" and not self.options["concise"]:
                self.options["expand"] = False
            elif name == "expand" and not self.options["expand"]:
                self.options["concise"] = False

            self.options[name] = not self.options[name]
            self._persist_options()
            # pystray caches the menu's visual checkmark state — force a refresh
            # so the on-screen state matches `self.options` after the toggle.
            try:
                if self._icon is not None:
                    self._icon.update_menu()
            except Exception:
                pass
        return handler

    def _persist_options(self):
        try:
            self._config["options"] = dict(self.options)
            save_config(self._config)
        except Exception:
            pass

    def _is_checked(self, name):
        def handler(item):
            return self.options[name]
        return handler

    def _on_hotkey(self):
        text, char_count = self.monitor.consume_buffer()

        use_selection = False
        use_select_all = False
        if not text.strip():
            text = self._get_selected_text()
            if text and text.strip():
                char_count = len(text)
                use_selection = True
            else:
                full_text, _ = read_focused_text()
                if full_text and full_text.strip():
                    text = full_text
                    char_count = len(full_text)
                    use_select_all = True
                else:
                    return

        context = self._get_clipboard_context()

        thread = threading.Thread(
            target=self._process_text,
            args=(text, char_count, use_selection, context, use_select_all),
            daemon=True,
        )
        thread.start()

    def _on_text_ready(self):
        if not self.options.get("auto_suggest"):
            _dlog("tray", "text_ready: auto_suggest off")
            return

        text = self.monitor.get_buffer()
        if not text or not text.strip():
            _dlog("tray", "text_ready: empty buffer")
            return

        trimmed = text.strip()
        if len(trimmed) < 20:
            _dlog("tray", f"text_ready: too short ({len(trimmed)})")
            return
        if not trimmed.endswith((".", "!", "?", "\n")) and len(trimmed) < 40:
            _dlog("tray", f"text_ready: no punct + <40 ({len(trimmed)})")
            return

        with self._suggest_lock:
            self._suggest_seq += 1
            seq = self._suggest_seq

        _dlog("tray", f"text_ready: spawning suggest seq={seq} len={len(trimmed)}")
        thread = threading.Thread(target=self._suggest_text, args=(text, seq), daemon=True)
        thread.start()

    def _suggest_text(self, text, seq):
        with self._suggest_lock:
            if seq != self._suggest_seq:
                _dlog("tray", f"suggest seq={seq}: superseded before LLM")
                return

        full_field, _ = read_focused_text()
        context = None
        if full_field and full_field.strip() and full_field.strip() != text.strip():
            # Strip the just-typed snippet from the end of the field so the LLM
            # doesn't re-emit it as part of the surrounding context.
            stripped = full_field.rstrip()
            text_stripped = text.rstrip()
            if text_stripped and stripped.endswith(text_stripped):
                stripped = stripped[: -len(text_stripped)]
            stripped = stripped.rstrip()
            if len(stripped) > 600:
                stripped = "…" + stripped[-600:]
            if stripped:
                context = stripped

        corrected = self.client.generate(self.prompt_builder.build(text, self.options, context=context))
        if corrected is None:
            _dlog("tray", f"suggest seq={seq}: LLM returned None")
            return

        with self._suggest_lock:
            if seq != self._suggest_seq:
                _dlog("tray", f"suggest seq={seq}: superseded after LLM")
                return

        if corrected.strip() == text.strip():
            _dlog("tray", f"suggest seq={seq}: corrected matches original")
            return

        _dlog("tray", f"suggest seq={seq}: showing overlay")
        self._show_suggestion(corrected)

    def _show_suggestion(self, corrected):
        existing = self._suggestion_window
        if existing is not None:
            try:
                existing.close()
            except Exception:
                pass

        overlay = SuggestionWindow(suggestion_text=corrected, on_click=self._on_accept_hotkey)
        self._suggestion_window = overlay
        self._pending_corrected = corrected
        self._pending_char_count = self.monitor.get_char_count()

        overlay.open()

        if self._suggestion_window is overlay:
            self._suggestion_window = None
            self._pending_corrected = None
            self._pending_char_count = 0

    def _on_typing(self):
        with self._suggest_lock:
            self._suggest_seq += 1
        overlay = self._suggestion_window
        if overlay is not None:
            try:
                overlay.close()
            except Exception:
                pass

    def _on_foreground_changed(self, hwnd):
        # Win32 fired EVENT_SYSTEM_FOREGROUND. Push the new hwnd into the
        # keyboard monitor so it resets its buffer immediately, before the
        # user starts typing in the new app.
        self.monitor.notify_foreground_change(hwnd)
        # Also dismiss any visible overlay — its caret position is stale.
        overlay = self._suggestion_window
        if overlay is not None:
            try:
                overlay.close()
            except Exception:
                pass
        with self._suggest_lock:
            self._suggest_seq += 1

    def _on_accept_hotkey(self):
        overlay = self._suggestion_window
        corrected = self._pending_corrected
        char_count = self._pending_char_count
        if overlay is None or not corrected:
            return

        try:
            overlay.close()
        except Exception:
            pass
        self._suggestion_window = None
        self._pending_corrected = None
        self._pending_char_count = 0

        thread = threading.Thread(
            target=self._do_accept_replace,
            args=(char_count, corrected),
            daemon=True,
        )
        thread.start()

    def _do_accept_replace(self, char_count, corrected):
        try:
            self.monitor.pause()
            try:
                if char_count > 0:
                    self.replacer.replace_text(char_count, corrected)
            finally:
                self.monitor.resume()
        except Exception:
            pass

    def _get_clipboard_context(self):
        try:
            no_window = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=2,
                creationflags=no_window,
            )
            clip = result.stdout.rstrip("\r\n")
            return clip if clip else None
        except Exception:
            return None

    def _get_selected_text(self):
        import time
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            no_window = subprocess.CREATE_NO_WINDOW

            old_clip = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=2,
                creationflags=no_window,
            ).stdout.rstrip("\r\n")

            kb.press(Key.ctrl)
            kb.press("c")
            kb.release("c")
            kb.release(Key.ctrl)
            time.sleep(0.15)

            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=2,
                creationflags=no_window,
            )
            new_clip = result.stdout.rstrip("\r\n")

            if new_clip and new_clip != old_clip:
                return new_clip
            return new_clip if new_clip else None
        except Exception:
            return None

    def _process_text(self, text, char_count, use_selection=False, context=None, use_select_all=False):
        prompt = self.prompt_builder.build(text, self.options, context=context)
        corrected = self.client.generate(prompt)

        if corrected is None:
            provider = self._config.get("provider", "ollama")
            if provider == "ollama":
                self._notify("Grammar Tool", "Ollama is not running. Please start it.")
            else:
                label = PROVIDERS.get(provider, {}).get("label", provider)
                self._notify("Grammar Tool", f"{label} request failed. Check Settings.")
            return

        if corrected.strip() == text.strip():
            self._notify("Grammar Tool", "Text looks good — no changes needed.")
            return

        self.monitor.pause()
        try:
            if use_select_all:
                self.replacer.replace_all(corrected)
            elif use_selection:
                self.replacer.paste_over_selection(corrected)
            else:
                self.replacer.replace_text(char_count, corrected)
        finally:
            self.monitor.resume()

    def _notify(self, title, message):
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=3, threaded=True)
        except Exception:
            pass

    def _open_settings(self, icon, item):
        def on_save(new_config):
            self._config = new_config
            save_config(self._config)
            self._build_client()

        settings = SettingsWindow(self._config, on_save)
        thread = threading.Thread(target=settings.open, daemon=True)
        thread.start()

    def _quit(self, icon, item):
        self.monitor.stop()
        try:
            self._focus_watcher.stop()
        except Exception:
            pass
        icon.stop()

    def _provider_label(self, item):
        provider = self._config.get("provider", "ollama")
        label = PROVIDERS.get(provider, {}).get("label", provider)
        return f"Provider: {label}"

    def run(self):
        import os
        import sys
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_path, "icon.png")
        image = Image.open(icon_path)

        menu = pystray.Menu(
            pystray.MenuItem("Fix Grammar", self._toggle_option("grammar"), checked=self._is_checked("grammar")),
            pystray.MenuItem("Formal Tone", self._toggle_option("formal"), checked=self._is_checked("formal")),
            pystray.MenuItem("Casual Tone", self._toggle_option("casual"), checked=self._is_checked("casual")),
            pystray.MenuItem("Concise", self._toggle_option("concise"), checked=self._is_checked("concise")),
            pystray.MenuItem("Expand", self._toggle_option("expand"), checked=self._is_checked("expand")),
            pystray.MenuItem("Auto Suggest (typing)", self._toggle_option("auto_suggest"), checked=self._is_checked("auto_suggest")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._provider_label, None, enabled=False),
            pystray.MenuItem("Settings", self._open_settings),
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon("grammar-tool", image, "Grammar Tool", menu)
        self.monitor.start()
        self._focus_watcher.start()
        self._icon.run()
