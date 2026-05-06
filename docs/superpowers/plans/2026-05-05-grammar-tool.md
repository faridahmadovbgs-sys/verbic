# Grammar Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a system tray app that monitors keystrokes and replaces typed text with grammar-corrected text via a local Ollama LLM, triggered by a hotkey.

**Architecture:** A background Python app with four layers: a global keyboard listener that buffers keystrokes, an Ollama HTTP client for LLM inference, a prompt builder that combines user text with active options, and a text replacer that selects/replaces the original text. The app lives in the Windows system tray with toggleable options.

**Tech Stack:** Python 3.12, pynput (keyboard), pystray (system tray), Pillow (icon), requests (HTTP), win10toast (notifications), Ollama + Llama 3.2:3b (local LLM)

---

## File Structure

```
grammar-tool/
├── main.py              # Entry point — wires all components, starts tray app
├── tray_app.py          # System tray icon, right-click menu, toggle state management
├── keyboard_monitor.py  # Global keystroke listener, character buffer, hotkey detection
├── text_replacer.py     # Selects typed text and replaces it with corrected text
├── ollama_client.py     # HTTP POST to Ollama API, error handling
├── prompt_builder.py    # Constructs LLM prompt from text + active toggle options
├── settings_window.py   # Tkinter dialog for configuring hotkey and model
├── icon.png             # 64x64 tray icon (generated programmatically in Task 1)
├── requirements.txt     # Python dependencies
├── tests/
│   ├── test_prompt_builder.py
│   ├── test_ollama_client.py
│   └── test_keyboard_monitor.py
└── DESIGN.md            # Design spec (already exists)
```

---

### Task 0: Environment Setup

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Install Python 3.12**

Download and install Python 3.12 from https://www.python.org/downloads/. During installation, check "Add Python to PATH". After install, restart your terminal.

Verify:
```bash
python --version
```
Expected: `Python 3.12.x`

- [ ] **Step 2: Install Ollama**

Download and install Ollama from https://ollama.com/download/windows. Run the installer. After install, Ollama starts automatically as a background service.

Verify:
```bash
curl http://localhost:11434/api/version
```
Expected: JSON with version info like `{"version":"0.x.x"}`

- [ ] **Step 3: Pull the Llama 3.2 model**

```bash
ollama pull llama3.2:3b
```
Expected: Downloads ~2GB model. Shows progress bar, then "success".

- [ ] **Step 4: Create requirements.txt**

```
pynput==1.7.7
pystray==0.19.5
Pillow==11.1.0
requests==2.32.3
win10toast==0.9
```

- [ ] **Step 5: Create virtual environment and install dependencies**

```bash
cd C:/Git/grammar-tool
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```
Expected: All packages install without errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt DESIGN.md
git commit -m "chore: add requirements and design spec"
```

---

### Task 1: Ollama Client

**Files:**
- Create: `ollama_client.py`
- Create: `tests/test_ollama_client.py`

- [ ] **Step 1: Create tests directory**

```bash
mkdir tests
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_ollama_client.py`:

```python
import unittest
from unittest.mock import patch, MagicMock
from ollama_client import OllamaClient


class TestOllamaClient(unittest.TestCase):
    def test_generate_returns_response_text(self):
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Hello, world!"}

        with patch("ollama_client.requests.post", return_value=mock_response):
            result = client.generate("Fix this: hello world")

        self.assertEqual(result, "Hello, world!")

    def test_generate_returns_none_when_ollama_not_running(self):
        client = OllamaClient()

        with patch("ollama_client.requests.post", side_effect=Exception("Connection refused")):
            result = client.generate("Fix this")

        self.assertIsNone(result)

    def test_generate_uses_correct_model(self):
        client = OllamaClient(model="llama3.2:3b")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "fixed"}

        with patch("ollama_client.requests.post", return_value=mock_response) as mock_post:
            client.generate("test prompt")

        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["json"]["model"], "llama3.2:3b")

    def test_generate_sends_prompt_in_body(self):
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "ok"}

        with patch("ollama_client.requests.post", return_value=mock_response) as mock_post:
            client.generate("my prompt text")

        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["json"]["prompt"], "my prompt text")

    def test_custom_model_name(self):
        client = OllamaClient(model="mistral:7b")
        self.assertEqual(client.model, "mistral:7b")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
python -m pytest tests/test_ollama_client.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'ollama_client'`

- [ ] **Step 4: Write minimal implementation**

Create `ollama_client.py`:

```python
import requests


class OllamaClient:
    def __init__(self, model="llama3.2:3b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt):
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=60,
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return None
        except Exception:
            return None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_ollama_client.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add ollama_client.py tests/test_ollama_client.py
git commit -m "feat: add Ollama client with tests"
```

---

### Task 2: Prompt Builder

**Files:**
- Create: `prompt_builder.py`
- Create: `tests/test_prompt_builder.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_prompt_builder.py`:

```python
import unittest
from prompt_builder import PromptBuilder


class TestPromptBuilder(unittest.TestCase):
    def test_grammar_only(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": False, "expand": False}
        prompt = builder.build("i dont no what to do", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("i dont no what to do", prompt)
        self.assertNotIn("formal", prompt.lower().split("text to correct")[0])
        self.assertNotIn("concise", prompt.lower().split("text to correct")[0])

    def test_grammar_and_formal(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": True, "casual": False, "concise": False, "expand": False}
        prompt = builder.build("hey whats up", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("formal", prompt.lower())

    def test_grammar_and_concise(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": True, "expand": False}
        prompt = builder.build("some long text here", options)

        self.assertIn("concise", prompt.lower())

    def test_casual_tone(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": True, "concise": False, "expand": False}
        prompt = builder.build("Dear Sir", options)

        self.assertIn("casual", prompt.lower())

    def test_expand_option(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": False, "expand": True}
        prompt = builder.build("short text", options)

        self.assertIn("elaborate", prompt.lower())

    def test_all_options_combined(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": True, "casual": False, "concise": True, "expand": False}
        prompt = builder.build("test", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("formal", prompt.lower())
        self.assertIn("concise", prompt.lower())

    def test_prompt_includes_return_only_instruction(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": False, "expand": False}
        prompt = builder.build("test", options)

        self.assertIn("Return ONLY the corrected text", prompt)

    def test_empty_text(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": False, "expand": False}
        prompt = builder.build("", options)

        self.assertIn('"""\n\n"""', prompt)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_prompt_builder.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'prompt_builder'`

- [ ] **Step 3: Write minimal implementation**

Create `prompt_builder.py`:

```python
class PromptBuilder:
    def build(self, text, options):
        instructions = []

        if options.get("grammar"):
            instructions.append("- Fix all grammar, spelling, and punctuation errors")
        if options.get("formal"):
            instructions.append("- Rewrite in a formal, professional tone")
        if options.get("casual"):
            instructions.append("- Rewrite in a casual, friendly, conversational tone")
        if options.get("concise"):
            instructions.append("- Make the text more concise while keeping the meaning")
        if options.get("expand"):
            instructions.append("- Elaborate and expand the text with more detail")

        instruction_block = "\n".join(instructions)

        return (
            f"You are a text correction assistant. Apply the following transformations to the text below:\n"
            f"{instruction_block}\n\n"
            f"IMPORTANT: Return ONLY the corrected text. No explanations, no quotes, no prefixes.\n\n"
            f"Text to correct:\n"
            f'"""\n{text}\n"""'
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_prompt_builder.py -v
```
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add prompt_builder.py tests/test_prompt_builder.py
git commit -m "feat: add prompt builder with tests"
```

---

### Task 3: Keyboard Monitor

**Files:**
- Create: `keyboard_monitor.py`
- Create: `tests/test_keyboard_monitor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_keyboard_monitor.py`:

```python
import unittest
from unittest.mock import MagicMock
from keyboard_monitor import KeyboardMonitor


class TestKeyboardMonitor(unittest.TestCase):
    def test_buffer_starts_empty(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        self.assertEqual(monitor.get_buffer(), "")

    def test_add_character_to_buffer(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("h")
        monitor.add_char("i")
        self.assertEqual(monitor.get_buffer(), "hi")

    def test_backspace_removes_last_char(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("h")
        monitor.add_char("i")
        monitor.handle_backspace()
        self.assertEqual(monitor.get_buffer(), "h")

    def test_backspace_on_empty_buffer(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.handle_backspace()
        self.assertEqual(monitor.get_buffer(), "")

    def test_add_newline(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("a")
        monitor.add_newline()
        monitor.add_char("b")
        self.assertEqual(monitor.get_buffer(), "a\nb")

    def test_reset_clears_buffer(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("x")
        monitor.add_char("y")
        monitor.reset_buffer()
        self.assertEqual(monitor.get_buffer(), "")

    def test_get_char_count(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("a")
        monitor.add_char("b")
        monitor.add_char("c")
        self.assertEqual(monitor.get_char_count(), 3)

    def test_consume_buffer_returns_and_resets(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("h")
        monitor.add_char("i")
        text, count = monitor.consume_buffer()
        self.assertEqual(text, "hi")
        self.assertEqual(count, 2)
        self.assertEqual(monitor.get_buffer(), "")

    def test_newline_counts_as_one_char(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("a")
        monitor.add_newline()
        self.assertEqual(monitor.get_char_count(), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_keyboard_monitor.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'keyboard_monitor'`

- [ ] **Step 3: Write minimal implementation**

Create `keyboard_monitor.py`:

```python
import threading
from pynput import keyboard


class KeyboardMonitor:
    def __init__(self, on_hotkey):
        self._buffer = []
        self._char_count = 0
        self._lock = threading.Lock()
        self._on_hotkey = on_hotkey
        self._listener = None
        self._hotkey_keys = {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.KeyCode.from_char("g")}
        self._pressed_keys = set()

    def add_char(self, char):
        with self._lock:
            self._buffer.append(char)
            self._char_count += 1

    def add_newline(self):
        with self._lock:
            self._buffer.append("\n")
            self._char_count += 1

    def handle_backspace(self):
        with self._lock:
            if self._buffer:
                self._buffer.pop()
                self._char_count = max(0, self._char_count - 1)

    def reset_buffer(self):
        with self._lock:
            self._buffer.clear()
            self._char_count = 0

    def get_buffer(self):
        with self._lock:
            return "".join(self._buffer)

    def get_char_count(self):
        with self._lock:
            return self._char_count

    def consume_buffer(self):
        with self._lock:
            text = "".join(self._buffer)
            count = self._char_count
            self._buffer.clear()
            self._char_count = 0
            return text, count

    def _on_press(self, key):
        self._pressed_keys.add(key)
        if self._hotkey_keys.issubset(self._pressed_keys):
            self._on_hotkey()
            return

        try:
            if hasattr(key, "char") and key.char is not None:
                self.add_char(key.char)
        except AttributeError:
            pass

        if key == keyboard.Key.enter:
            self.add_newline()
        elif key == keyboard.Key.backspace:
            self.handle_backspace()
        elif key in (keyboard.Key.left, keyboard.Key.right, keyboard.Key.up, keyboard.Key.down):
            self.reset_buffer()

    def _on_release(self, key):
        self._pressed_keys.discard(key)

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_keyboard_monitor.py -v
```
Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add keyboard_monitor.py tests/test_keyboard_monitor.py
git commit -m "feat: add keyboard monitor with buffer and hotkey detection"
```

---

### Task 4: Text Replacer

**Files:**
- Create: `text_replacer.py`

- [ ] **Step 1: Write the implementation**

This module simulates keyboard input to select and replace text. It cannot be unit tested meaningfully because it drives the OS keyboard. We will test it manually in Task 6 (integration).

Create `text_replacer.py`:

```python
import time
import threading
from pynput.keyboard import Controller, Key


class TextReplacer:
    def __init__(self):
        self._keyboard = Controller()

    def replace_text(self, char_count, corrected_text):
        thread = threading.Thread(target=self._do_replace, args=(char_count, corrected_text), daemon=True)
        thread.start()

    def _do_replace(self, char_count, corrected_text):
        time.sleep(0.1)

        for _ in range(char_count):
            self._keyboard.press(Key.shift)
            self._keyboard.press(Key.left)
            self._keyboard.release(Key.left)
            self._keyboard.release(Key.shift)
            time.sleep(0.005)

        time.sleep(0.05)

        for char in corrected_text:
            if char == "\n":
                self._keyboard.press(Key.enter)
                self._keyboard.release(Key.enter)
            else:
                self._keyboard.type(char)
            time.sleep(0.005)
```

- [ ] **Step 2: Commit**

```bash
git add text_replacer.py
git commit -m "feat: add text replacer for in-place text substitution"
```

---

### Task 5: System Tray App

**Files:**
- Create: `tray_app.py`
- Create: `icon.png`

- [ ] **Step 1: Generate a tray icon programmatically**

Create a simple script to generate the icon, then run it:

```bash
python -c "
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([4, 4, 60, 60], radius=12, fill=(59, 130, 246))
draw.text((16, 12), 'Gr', fill='white')
img.save('icon.png')
"
```
Expected: `icon.png` created in the project root.

- [ ] **Step 2: Write the tray app**

Create `tray_app.py`:

```python
import pystray
from PIL import Image
from keyboard_monitor import KeyboardMonitor
from text_replacer import TextReplacer
from ollama_client import OllamaClient
from prompt_builder import PromptBuilder
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
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon("grammar-tool", image, "Grammar Tool", menu)
        self.monitor.start()
        self._icon.run()
```

- [ ] **Step 3: Commit**

```bash
git add tray_app.py icon.png
git commit -m "feat: add system tray app with toggle menu"
```

---

### Task 6: Main Entry Point and Integration Test

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write the entry point**

Create `main.py`:

```python
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tray_app import GrammarTrayApp


def main():
    app = GrammarTrayApp()
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all unit tests**

```bash
python -m pytest tests/ -v
```
Expected: All tests pass (22 total across 3 test files).

- [ ] **Step 3: Manual integration test**

1. Make sure Ollama is running: `curl http://localhost:11434/api/version`
2. Launch the app: `python main.py`
3. Verify the tray icon appears near the system clock.
4. Right-click the icon — verify all menu options show with checkboxes.
5. Open Notepad.
6. Type: `i dont no what too do about this problm`
7. Press **Ctrl+Shift+G**.
8. Wait 2-5 seconds — the text should be selected and replaced with a grammatically correct version.
9. Right-click tray icon → toggle "Formal Tone" on.
10. Type: `hey whats up can u help me with this`
11. Press **Ctrl+Shift+G** — text should be replaced with a formal version.
12. Right-click tray icon → Quit.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add main entry point — app is functional"
```

---

### Task 7: Settings Window

**Files:**
- Create: `settings_window.py`
- Modify: `tray_app.py`

- [ ] **Step 1: Write the settings window**

Create `settings_window.py`:

```python
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
```

- [ ] **Step 2: Add Settings menu item to tray_app.py**

In `tray_app.py`, add the import at the top:

```python
from settings_window import SettingsWindow
```

Add this method to `GrammarTrayApp`:

```python
    def _open_settings(self, icon, item):
        def on_save(model):
            self.ollama = OllamaClient(model=model)

        settings = SettingsWindow(self.ollama.model, on_save)
        thread = threading.Thread(target=settings.open, daemon=True)
        thread.start()
```

Add the Settings menu item to the menu in the `run` method, between the separator and Quit:

```python
            pystray.MenuItem("Settings", self._open_settings),
```

The full menu becomes:
```python
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
```

- [ ] **Step 3: Manual test**

1. Launch: `python main.py`
2. Right-click tray icon → Settings.
3. Verify the settings window opens with the model name pre-filled.
4. Change model to `llama3.2:1b`, click Save.
5. Type some text in Notepad, press Ctrl+Shift+G — should still work (if that model is pulled).
6. Quit the app.

- [ ] **Step 4: Commit**

```bash
git add settings_window.py tray_app.py
git commit -m "feat: add settings window for model configuration"
```

---

### Task 8: Final Polish

**Files:**
- Modify: `keyboard_monitor.py` (mouse click reset)
- Create: `README.md`

- [ ] **Step 1: Add mouse click buffer reset**

In `keyboard_monitor.py`, update `__init__` to also set up a mouse listener, and add a `_on_click` method:

Add import at top:
```python
from pynput import keyboard, mouse
```

Add to `__init__`:
```python
        self._mouse_listener = None
```

Add method:
```python
    def _on_click(self, x, y, button, pressed):
        if pressed:
            self.reset_buffer()
```

Update `start` method:
```python
    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()
```

Update `stop` method:
```python
    def stop(self):
        if self._listener:
            self._listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()
```

- [ ] **Step 2: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 3: Create README**

Create `README.md`:

```markdown
# Grammar Tool

A system tray app that corrects your grammar in any application using a local AI model.

## How It Works

1. Launch the app — it sits in your system tray.
2. Type in any app (Word, Chrome, Slack, Notepad, etc.).
3. Press **Ctrl+Shift+G** to correct your text in-place.

## Features

Toggle via right-click on the tray icon:
- **Fix Grammar** — corrects spelling, punctuation, grammar (on by default)
- **Formal Tone** — rewrites in professional language
- **Casual Tone** — rewrites in friendly language
- **Concise** — shortens text
- **Expand** — adds more detail

## Setup

### Prerequisites
- Python 3.10+
- Ollama (https://ollama.com)

### Install

1. Install Ollama and pull the model:
   ```bash
   ollama pull llama3.2:3b
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run:
   ```bash
   python main.py
   ```
```

- [ ] **Step 4: Full manual integration test**

1. Launch: `python main.py`
2. Test grammar correction in Notepad.
3. Test formal tone toggle.
4. Test casual tone toggle.
5. Test concise toggle.
6. Test mouse click resets buffer (click elsewhere, then type new text).
7. Test Settings window.
8. Test Quit.

- [ ] **Step 5: Commit**

```bash
git add keyboard_monitor.py README.md
git commit -m "feat: add mouse click buffer reset and README"
```
