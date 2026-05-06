import pystray
import subprocess
from PIL import Image
from keyboard_monitor import KeyboardMonitor
from text_replacer import TextReplacer
from ollama_client import OllamaClient
from openai_client import OpenAIClient
from prompt_builder import PromptBuilder
from settings_window import SettingsWindow
from config import load_config, save_config
import threading


class GrammarTrayApp:
    def __init__(self):
        self.options = {
            "grammar": True,
            "formal": False,
            "casual": False,
            "concise": False,
            "expand": False,
        }
        self._config = load_config()
        self._build_client()
        self.prompt_builder = PromptBuilder()
        self.replacer = TextReplacer()
        self.monitor = KeyboardMonitor(on_hotkey=self._on_hotkey)
        self._icon = None

    def _build_client(self):
        provider = self._config.get("provider", "ollama")
        if provider == "openai":
            self.client = OpenAIClient(
                api_key=self._config.get("api_key", ""),
                model=self._config.get("openai_model", "gpt-4o-mini"),
            )
        else:
            self.client = OllamaClient(
                model=self._config.get("ollama_model", "llama3.1:8b"),
            )

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
        return handler

    def _is_checked(self, name):
        def handler(item):
            return self.options[name]
        return handler

    def _on_hotkey(self):
        print("[Hotkey] Ctrl+Shift+G triggered")
        text, char_count = self.monitor.consume_buffer()

        use_selection = False
        if not text.strip():
            text = self._get_selected_text()
            if not text or not text.strip():
                return
            char_count = len(text)
            use_selection = True

        context = self._get_clipboard_context()

        thread = threading.Thread(target=self._process_text, args=(text, char_count, use_selection, context), daemon=True)
        thread.start()

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
        import subprocess
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

    def _process_text(self, text, char_count, use_selection=False, context=None):
        prompt = self.prompt_builder.build(text, self.options, context=context)
        corrected = self.client.generate(prompt)

        if corrected is None:
            provider = self._config.get("provider", "ollama")
            if provider == "openai":
                self._notify("Grammar Tool", "OpenAI request failed. Check your API key in Settings.")
            else:
                self._notify("Grammar Tool", "Ollama is not running. Please start it.")
            return

        if corrected.strip() == text.strip():
            self._notify("Grammar Tool", "Text looks good — no changes needed.")
            return

        self.monitor.pause()
        try:
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
            self._config.update(new_config)
            save_config(self._config)
            self._build_client()

        settings = SettingsWindow(self._config, on_save)
        thread = threading.Thread(target=settings.open, daemon=True)
        thread.start()

    def _quit(self, icon, item):
        self.monitor.stop()
        icon.stop()

    def _provider_label(self, item):
        provider = self._config.get("provider", "ollama")
        return f"Provider: {provider}"

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
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._provider_label, None, enabled=False),
            pystray.MenuItem("Settings", self._open_settings),
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon("grammar-tool", image, "Grammar Tool", menu)
        self.monitor.start()
        self._icon.run()
