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
