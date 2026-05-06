import pystray
from PIL import Image
from keyboard_monitor import KeyboardMonitor
from text_replacer import TextReplacer
from ollama_client import OllamaClient
from prompt_builder import PromptBuilder
from settings_window import SettingsWindow
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
        self.ollama = OllamaClient()
        self.prompt_builder = PromptBuilder()
        self.replacer = TextReplacer()
        self.monitor = KeyboardMonitor(on_hotkey=self._on_hotkey)
        self._icon = None

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
        text, char_count = self.monitor.consume_buffer()
        if not text.strip():
            return

        thread = threading.Thread(target=self._process_text, args=(text, char_count), daemon=True)
        thread.start()

    def _process_text(self, text, char_count):
        prompt = self.prompt_builder.build(text, self.options)
        corrected = self.ollama.generate(prompt)

        if corrected is None:
            self._notify("Grammar Tool", "Ollama is not running. Please start it.")
            return

        if corrected.strip() == text.strip():
            self._notify("Grammar Tool", "Text looks good — no changes needed.")
            return

        self.replacer.replace_text(char_count, corrected)

    def _notify(self, title, message):
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=3, threaded=True)
        except Exception:
            pass

    def _open_settings(self, icon, item):
        def on_save(model):
            self.ollama = OllamaClient(model=model)

        settings = SettingsWindow(self.ollama.model, on_save)
        thread = threading.Thread(target=settings.open, daemon=True)
        thread.start()

    def _quit(self, icon, item):
        self.monitor.stop()
        icon.stop()

    def run(self):
        image = Image.open("icon.png")

        menu = pystray.Menu(
            pystray.MenuItem("Fix Grammar", self._toggle_option("grammar"), checked=self._is_checked("grammar")),
            pystray.MenuItem("Formal Tone", self._toggle_option("formal"), checked=self._is_checked("formal")),
            pystray.MenuItem("Casual Tone", self._toggle_option("casual"), checked=self._is_checked("casual")),
            pystray.MenuItem("Concise", self._toggle_option("concise"), checked=self._is_checked("concise")),
            pystray.MenuItem("Expand", self._toggle_option("expand"), checked=self._is_checked("expand")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self._open_settings),
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon("grammar-tool", image, "Grammar Tool", menu)
        self.monitor.start()
        self._icon.run()
