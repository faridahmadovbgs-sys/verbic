# Grammar Tool — Design Spec

## Overview

A system tray desktop application for Windows that monitors keystrokes and corrects grammar (plus optional tone/style adjustments) in-place in any application. Powered by a local Ollama LLM (Llama 3.2), so it's completely free with no API costs.

## User Flow

1. Launch the app — it minimizes to the system tray (icon near the clock).
2. Type normally in any application (Word, Chrome, Slack, Notepad, etc.).
3. The app silently tracks keystrokes in a buffer.
4. Press **Ctrl+Shift+G** to trigger correction.
5. The app:
   - Takes the buffered text.
   - Sends it to Ollama with the selected options.
   - Selects the original text and replaces it with the corrected version.
6. A small toast notification confirms "Text corrected!".

## Features

### Toggleable Options (via system tray right-click menu)

| Option        | Description                              | Default |
|---------------|------------------------------------------|---------|
| Fix Grammar   | Corrects spelling, punctuation, grammar  | On      |
| Formal Tone   | Rewrites in professional/formal language | Off     |
| Casual Tone   | Rewrites in friendly/conversational tone | Off     |
| Concise       | Shortens text while keeping meaning      | Off     |
| Expand        | Elaborates and adds detail               | Off     |

**Mutual exclusivity rules:**
- Formal Tone and Casual Tone are mutually exclusive (selecting one deselects the other).
- Concise and Expand are mutually exclusive (same logic).
- Options can be combined across groups (e.g. Fix Grammar + Formal + Concise).

### System Tray Menu

Right-clicking the tray icon shows:
- Checkable toggles for each option above
- A separator
- **Settings** — opens a Tkinter settings window (change hotkey, select Ollama model)
- **Quit** — exits the app

### Hotkey

- Default: **Ctrl+Shift+G**
- Configurable via the Settings window.

## Architecture

```
User typing in any app
        |
        v
keyboard_monitor.py  (pynput listener)
  - Captures keystrokes globally
  - Maintains a character buffer
  - Tracks character count for replacement
  - Resets buffer on hotkey trigger
        |
        v  (hotkey pressed)
prompt_builder.py
  - Reads the buffer contents
  - Reads current toggle states from tray_app
  - Constructs an LLM prompt combining text + options
        |
        v
ollama_client.py
  - Sends POST to http://localhost:11434/api/generate
  - Model: llama3.2:3b (configurable)
  - Returns corrected text
        |
        v
text_replacer.py
  - Calculates how many characters to select back
  - Simulates Shift+Left Arrow (repeated) to select typed text
  - Simulates Ctrl+V to paste corrected text from clipboard
  - Shows toast notification on completion
```

## File Structure

```
grammar-tool/
├── main.py              # Entry point, launches tray app
├── tray_app.py          # System tray icon, menu, toggle state
├── keyboard_monitor.py  # Global keystroke listener and buffer
├── text_replacer.py     # Selects and replaces typed text in-place
├── ollama_client.py     # HTTP calls to Ollama API
├── prompt_builder.py    # Builds LLM prompts from text + options
├── settings_window.py   # Tkinter dialog for hotkey/model config
├── icon.png             # Tray icon image
└── requirements.txt     # Python dependencies
```

## Dependencies

| Package      | Purpose                          |
|--------------|----------------------------------|
| pynput       | Global keyboard monitoring       |
| pystray      | System tray icon and menu        |
| Pillow       | Icon image handling for tray     |
| requests     | HTTP calls to Ollama             |
| win10toast   | Windows toast notifications      |

## Prompt Strategy

The prompt sent to Ollama is constructed dynamically based on active toggles. Example:

```
You are a text correction assistant. Apply the following transformations to the text below:
- Fix all grammar, spelling, and punctuation errors
- Rewrite in a formal tone
- Make the text more concise

IMPORTANT: Return ONLY the corrected text. No explanations, no quotes, no prefixes.

Text to correct:
"""
{user_text}
"""
```

Only active toggles are included in the prompt instructions.

## Keyboard Buffer Logic

- The buffer accumulates printable characters as the user types.
- Backspace removes the last character from the buffer.
- Enter adds a newline to the buffer.
- Arrow keys, mouse clicks, and window switches reset the buffer (since cursor position becomes unknown, making accurate replacement impossible).
- On hotkey trigger: the buffer contents are sent for correction, the character count is used for text selection/replacement, and the buffer is reset.

## Text Replacement Logic

1. Store the corrected text in the system clipboard.
2. Simulate `Shift+Left Arrow` repeated N times (where N = character count in buffer) to select the original text.
3. Simulate `Ctrl+V` to paste the corrected text over the selection.
4. Restore the original clipboard contents after a short delay.

## Error Handling

- **Ollama not running:** Toast notification "Ollama is not running. Please start it." when hotkey is pressed and Ollama is unreachable.
- **Empty buffer:** No action if the buffer is empty when hotkey is pressed.
- **Model not found:** Toast notification "Model not found. Run: ollama pull llama3.2:3b" if the model hasn't been downloaded.

## Setup Requirements

1. Python 3.10 or higher.
2. Install Ollama from https://ollama.com (Windows installer).
3. Download the model: `ollama pull llama3.2:3b` (one-time, ~2GB).
4. Install Python dependencies: `pip install -r requirements.txt`.
5. Launch: `python main.py`.

## Known Limitations

- **Keystroke monitoring:** Antivirus software may flag the app because it uses a global keyboard listener. This is the same technique used by legitimate tools like AutoHotkey and text expanders.
- **Buffer reset on mouse/arrow:** If the user clicks or uses arrow keys, the buffer resets because the app can no longer track cursor position accurately. The user must retype or type new text before triggering correction.
- **Replacement accuracy:** The Shift+Left Arrow replacement approach works reliably in most text fields but may behave unexpectedly in some rich text editors or terminal emulators.
- **Local resources:** The Llama 3.2 3B model uses ~2-4GB of RAM while loaded. Correction takes a few seconds depending on text length and hardware.
