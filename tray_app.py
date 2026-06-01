import pystray
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image
from keyboard_monitor import KeyboardMonitor
from text_replacer import TextReplacer
from ollama_client import OllamaClient
from openai_client import OpenAICompatibleClient
from claude_client import ClaudeClient
from prompt_builder import PromptBuilder
from suggestion_window import SuggestionWindow
from selection_button import SelectionToolbar
from settings_window import SettingsWindow
from shortcuts_window import ShortcutsWindow
from config import (
    load_config, save_config, PROVIDERS, DEFAULT_OPTIONS, ENGINES,
    DEFAULT_ENGINE, TONES, TONE_KEYS, TOOLBAR_ACTIONS,
)
from welcome_window import WelcomeWindow
from text_reader import read_focused_text
from focus_watcher import FocusWatcher
import updater
from version import APP_VERSION
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
        # When True, accepting the current overlay inserts new text at the
        # caret instead of replacing the last N typed characters (answer mode).
        self._pending_is_insert = False
        # When True, accepting pastes over the current selection (Fix action
        # from the floating toolbar, where text is already selected).
        self._pending_paste_selection = False
        # Floating action toolbar shown after a selection.
        self._selection_button = None
        self._selection_button_timer = None
        self._enable_selection_button = self._config.get("selection_button", True)
        self._toolbar_config = dict(self._config.get("toolbar") or {})
        # Speculation mode: cached eager answer pre-draft and the text it was
        # drafted for, so a later "Draft answer" returns instantly.
        self._speculative_answer = None
        self._speculative_answer_for = None
        self._suggest_seq = 0
        self._suggest_lock = threading.Lock()
        # Rate-limit auto-suggest error notifications so a misconfigured
        # provider doesn't flood the user with toasts on every keystroke pause.
        self._last_auto_error_ts = 0.0
        self._last_auto_error_msg = None
        self.monitor = KeyboardMonitor(
            on_hotkey=self._on_hotkey,
            on_text_ready=self._on_text_ready,
            on_accept_hotkey=self._on_accept_hotkey,
            on_typing=self._on_typing,
            on_context_hotkey=self._on_context_hotkey,
            on_answer_hotkey=self._on_answer_hotkey,
            on_selection_made=self._on_selection_made,
        )
        self.monitor.set_hotkeys(self._config.get("hotkeys") or {})
        self._focus_watcher = FocusWatcher(on_focus_change=self._on_foreground_changed)
        self._writing_context = self._config.get("writing_context", "") or ""
        self._paused_globally = False
        # Tracks an open Settings window so a double-click on the tray icon
        # (which fires the default action twice) doesn't spawn two of them.
        self._settings_open = False
        self._settings_open_lock = threading.Lock()
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
            # Tones are mutually exclusive — enabling one clears the others so
            # the AI gets a single, unambiguous tone instruction.
            if name in TONE_KEYS and not self.options.get(name):
                for other in TONE_KEYS:
                    if other != name:
                        self.options[other] = False

            self.options[name] = not self.options.get(name, False)
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
        if self._paused_globally:
            self._notify("Verbic", "Paused. Right-click tray to resume.")
            return
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
        if self._paused_globally:
            return
        # The typing-pause slot drives both auto-suggest grammar and
        # speculation-mode prediction; proceed if either is enabled.
        if not self.options.get("auto_suggest") and not self.options.get("speculation"):
            _dlog("tray", "text_ready: auto_suggest + speculation off")
            return

        # Atomic snapshot — text and char_count must come from the same
        # buffer state, otherwise a keystroke between get_buffer() and
        # get_char_count() would make the replacement length disagree with
        # the LLM input and leave fragments of original typing in place
        # (the "whWhat" bug).
        text, char_count = self.monitor.snapshot_buffer()
        if not text or not text.strip():
            _dlog("tray", "text_ready: empty buffer")
            return

        trimmed = text.strip()
        # Skip very short fragments and mid-phrase typing that won't yield a
        # useful correction. Threshold tuned for chat-style messages where a
        # 20-char sentence is common and a 30-char fragment is worth checking.
        if len(trimmed) < 15:
            _dlog("tray", f"text_ready: too short ({len(trimmed)})")
            return
        if not trimmed.endswith((".", "!", "?", "\n")) and len(trimmed) < 30:
            _dlog("tray", f"text_ready: no punct + <30 ({len(trimmed)})")
            return

        with self._suggest_lock:
            self._suggest_seq += 1
            seq = self._suggest_seq

        _dlog("tray", f"text_ready: spawning suggest seq={seq} len={len(trimmed)} count={char_count}")
        thread = threading.Thread(
            target=self._suggest_text,
            args=(text, char_count, seq),
            daemon=True,
        )
        thread.start()

    def _suggest_text(self, text, char_count, seq):
        with self._suggest_lock:
            if seq != self._suggest_seq:
                _dlog("tray", f"suggest seq={seq}: superseded before correction")
                return

        # Speculation mode repurposes the typing-pause slot to predict how the
        # user would continue, shown as an insert-at-caret suggestion. Grammar
        # correction is still available via the Fix hotkey.
        if self.options.get("speculation"):
            self._speculate_continuation(text, seq)
            return

        # Refuse to call the AI with no transformation requested — without
        # an instruction the model invents one, producing surreal rewrites.
        if not self._any_transformation_selected():
            _dlog("tray", f"suggest seq={seq}: no options checked, skipping")
            self._notify_auto_error(
                "No options checked. Enable Grammar (or a tone) in the tray menu."
            )
            return

        context = self._get_field_context(text)

        corrected = self._run_correction(text, context=context)
        if corrected is None:
            _dlog("tray", f"suggest seq={seq}: provider returned None")
            self._notify_auto_error(self._provider_failure_message())
            return

        with self._suggest_lock:
            if seq != self._suggest_seq:
                _dlog("tray", f"suggest seq={seq}: superseded after LLM")
                return

        if corrected.strip() == text.strip():
            _dlog("tray", f"suggest seq={seq}: corrected matches original")
            return

        if not self._looks_like_valid_correction(text, corrected):
            _dlog("tray", f"suggest seq={seq}: output failed sanity check")
            return

        _dlog("tray", f"suggest seq={seq}: showing overlay count={char_count}")
        self._show_suggestion(corrected, char_count)

    def _speculate_continuation(self, text, seq):
        """Predict the continuation of `text` and show it as an insert overlay."""
        wctx = self._writing_context if self._writing_context else None
        prompt = self.prompt_builder.build_predict(text, writing_context=wctx)
        prediction = self.client.generate(prompt)
        if not prediction or not prediction.strip():
            return

        with self._suggest_lock:
            if seq != self._suggest_seq:
                _dlog("tray", f"speculate seq={seq}: superseded after LLM")
                return

        cont = prediction.rstrip()
        # The model is told to lead with a space when needed; make sure of it
        # so the inserted continuation doesn't fuse onto the last word.
        if cont and not text.endswith((" ", "\n")) and not cont.startswith((" ", "\n", ".", ",", "!", "?", ";", ":")):
            cont = " " + cont
        # Insert mode: append at the caret, nothing to replace.
        self._show_suggestion(cont, 0, is_insert=True, header="Predictive (Flow)")

    def _any_transformation_selected(self):
        if self.options.get("grammar") or self.options.get("expand"):
            return True
        return any(self.options.get(k) for k in TONE_KEYS)

    def _provider_failure_message(self):
        provider = self._config.get("provider", "ollama")
        if provider == "ollama":
            return "Ollama not reachable. Start Ollama or pick a provider in Settings."
        label = PROVIDERS.get(provider, {}).get("label", provider)
        return f"{label} request failed. Check Settings."

    def _notify_auto_error(self, message):
        """Rate-limited tray notification for auto-suggest failures. The user
        shouldn't get a toast on every keystroke — once every 5 minutes per
        message is enough to alert them without spamming."""
        if not message:
            return
        now = time.monotonic()
        if self._last_auto_error_msg == message and (now - self._last_auto_error_ts) < 300:
            return
        self._last_auto_error_msg = message
        self._last_auto_error_ts = now
        self._notify("Verbic", message)

    def _looks_like_valid_correction(self, original, corrected):
        """Reject obviously broken AI output: refusals, empty strings, or
        wildly inflated/truncated rewrites. The strip-equality check above
        already covers the no-op case."""
        if not corrected or not corrected.strip():
            return False
        c = corrected.strip()
        # Common refusal patterns from small models and safety-tuned APIs.
        refusal_markers = (
            "i cannot", "i can't", "i'm unable", "i am unable",
            "i'm not able", "i am not able", "as an ai", "i apologize",
            "sorry, i can",
        )
        head = c[:80].lower()
        if any(head.startswith(m) for m in refusal_markers):
            return False
        # Length sanity: a correction shouldn't be a tenth or ten times the
        # input. Either is a model gone off the rails.
        olen = max(len(original.strip()), 1)
        clen = len(c)
        if clen > olen * 8 + 40:
            return False
        if olen >= 20 and clen < olen // 4:
            return False
        return True

    def _run_correction(self, text, context=None):
        """Run a correction request through the configured AI provider.
        Returns the corrected text, or None on failure."""
        wctx = self._writing_context if self._writing_context else None
        prompt = self.prompt_builder.build(text, self.options, context=context, writing_context=wctx)
        return self.client.generate(prompt)

    def _get_field_context(self, text):
        full_field, _ = read_focused_text()
        if not full_field or not full_field.strip() or full_field.strip() == text.strip():
            return None
        stripped = full_field.rstrip()
        text_stripped = text.rstrip()
        if text_stripped and stripped.endswith(text_stripped):
            stripped = stripped[: -len(text_stripped)]
        stripped = stripped.rstrip()
        if len(stripped) > 600:
            tail = stripped[-600:]
            # Truncate at the next sentence boundary so the model isn't fed a
            # half-sentence fragment from the middle of a word.
            for marker in (". ", "! ", "? ", "\n"):
                idx = tail.find(marker)
                if 0 <= idx < 200:
                    tail = tail[idx + len(marker):]
                    break
            stripped = "…" + tail
        return stripped or None

    def _show_suggestion(self, corrected, char_count, is_insert=False, paste_selection=False, header=None):
        existing = self._suggestion_window
        if existing is not None:
            try:
                existing.close()
            except Exception:
                pass

        overlay = SuggestionWindow(
            suggestion_text=corrected,
            on_click=self._on_overlay_click,
            on_dismiss=self._on_overlay_dismiss,
            on_copy=self._on_overlay_copy,
            header_label=header or self._active_mode_label(),
        )
        self._suggestion_window = overlay
        self._pending_corrected = corrected
        # char_count was captured at the same moment as the text we sent to
        # the LLM — using monitor.get_char_count() here would race with any
        # late typing and select the wrong number of characters.
        self._pending_char_count = char_count
        self._pending_is_insert = is_insert
        self._pending_paste_selection = paste_selection

        overlay.open()

        if self._suggestion_window is overlay:
            self._suggestion_window = None
            self._pending_corrected = None
            self._pending_char_count = 0
            self._pending_is_insert = False
            self._pending_paste_selection = False

    def _on_typing(self):
        with self._suggest_lock:
            self._suggest_seq += 1
        overlay = self._suggestion_window
        # Invalidate the accept payload immediately. The overlay's _poll_close
        # has a 50 ms latency before destroy(), so a fast Ctrl+Tab right after
        # the user resumes typing could otherwise still fire _on_accept_hotkey
        # with a stale _pending_corrected — replacing text that no longer
        # matches what's in the field. Clearing here closes that race.
        self._pending_corrected = None
        self._pending_char_count = 0
        self._pending_is_insert = False
        self._pending_paste_selection = False
        if overlay is not None:
            try:
                overlay.close()
            except Exception:
                pass
        # Typing also dismisses the floating context button.
        self._close_selection_button()

    def _on_foreground_changed(self, hwnd):
        # Win32 fired EVENT_SYSTEM_FOREGROUND. Push the new hwnd into the
        # keyboard monitor so it resets its buffer immediately, before the
        # user starts typing in the new app.
        self.monitor.notify_foreground_change(hwnd)
        # Switching apps fully invalidates the pending suggestion — its
        # captured char_count refers to the previous app's caret position.
        # FocusWatcher already filters our own windows, so this only fires
        # for genuine app/window changes, not for the overlay flashing into
        # the foreground briefly.
        overlay = self._suggestion_window
        self._pending_corrected = None
        self._pending_char_count = 0
        self._pending_is_insert = False
        self._pending_paste_selection = False
        if overlay is not None:
            try:
                overlay.close()
            except Exception:
                pass
        self._close_selection_button()
        with self._suggest_lock:
            self._suggest_seq += 1

    def _on_accept_hotkey(self):
        """Ctrl+Space handler — dual-purpose.

        If an overlay is visible: apply the suggestion. Otherwise fall through
        to the manual-correction path so the same key works on a selection or
        a freshly-typed sentence without an overlay. Only the keyboard hotkey
        falls through; clicking the overlay goes through `_on_overlay_click`
        which never falls through (a click on nothing should do nothing).
        """
        if not self._apply_pending_if_any():
            self._on_hotkey()

    def _on_overlay_click(self):
        """Apply-button handler on the SuggestionWindow.

        Pure 'accept what's shown'. If the payload was already invalidated
        (typing happened in the 50 ms close-poll window), do nothing — never
        fall through to manual correction. The old behavior of falling
        through here caused a stale clipboard to be fed back to the LLM and
        the user saw their previously-accepted correction reappear.
        """
        self._apply_pending_if_any()

    def _on_overlay_dismiss(self):
        """Dismiss-button (or ✕) handler — discard the suggestion without
        applying. Clears the pending payload so a later Ctrl+Space doesn't
        apply the just-dismissed text."""
        self._suggestion_window = None
        self._pending_corrected = None
        self._pending_char_count = 0
        self._pending_is_insert = False
        self._pending_paste_selection = False

    def _on_overlay_copy(self):
        """Copy-button handler — put the suggestion on the clipboard instead of
        applying it, then dismiss. Lets the user paste it wherever they like."""
        text = self._pending_corrected
        # Clear pending the same way Dismiss does — the overlay is going away.
        self._on_overlay_dismiss()
        if not text:
            return
        try:
            from text_replacer import _set_clipboard_text
            _set_clipboard_text(text)
            self._notify("Verbic", "Copied to clipboard.")
        except Exception:
            pass

    def _active_mode_label(self):
        """Human-readable label for the overlay header describing what kind of
        edit is being suggested (Grammar, a tone, Expand, or a combination)."""
        parts = []
        if self.options.get("grammar"):
            parts.append("Grammar")
        tone_names = {key: label for key, label, _prompt in TONES}
        for key in TONE_KEYS:
            if self.options.get(key):
                parts.append(tone_names.get(key, key.title()))
                break
        if self.options.get("expand"):
            parts.append("Expand")
        return " · ".join(parts) if parts else "Suggested edit"

    def _apply_pending_if_any(self):
        """Return True if a pending suggestion was applied, False otherwise."""
        overlay = self._suggestion_window
        corrected = self._pending_corrected
        char_count = self._pending_char_count
        is_insert = self._pending_is_insert
        paste_selection = self._pending_paste_selection
        if overlay is None or not corrected:
            return False

        try:
            overlay.close()
        except Exception:
            pass
        self._suggestion_window = None
        self._pending_corrected = None
        self._pending_char_count = 0
        self._pending_is_insert = False
        self._pending_paste_selection = False

        thread = threading.Thread(
            target=self._do_accept_replace,
            args=(char_count, corrected, is_insert, paste_selection),
            daemon=True,
        )
        thread.start()
        return True

    def _do_accept_replace(self, char_count, corrected, is_insert=False, paste_selection=False):
        try:
            self.monitor.pause()
            try:
                if paste_selection:
                    # Fix-from-toolbar: the original text is still selected in
                    # the app, so paste straight over it.
                    self.replacer.paste_over_selection(corrected)
                elif is_insert:
                    # Answer mode: nothing to replace, just drop the text in
                    # at the caret.
                    self.replacer.insert_text(corrected)
                elif char_count > 0:
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
        """Copy whatever is selected in the focused field and return it.

        Uses a sentinel to detect whether Ctrl+C actually copied something:
        the clipboard is overwritten with a unique marker *before* Ctrl+C, so
        a real copy leaves the selection on the clipboard while a no-op copy
        (nothing selected) leaves the marker untouched. This is what lets the
        user fix the *same* text repeatedly — the old "did the clipboard
        change?" check failed there (the text was already on the clipboard
        from the previous fix) and wrongly reported "no selection".

        The user's original clipboard is restored afterward so we don't
        clobber it.
        """
        import time
        try:
            from pynput.keyboard import Controller, Key
            from text_replacer import _get_clipboard_text, _set_clipboard_text
            kb = Controller()

            # The trigger hotkey (e.g. Ctrl+Alt+X) leaves Alt/Shift physically
            # held when we get here. If we synthesize Ctrl+C while Alt is still
            # down the OS sees Ctrl+Alt+C, which doesn't copy. Release the
            # modifiers first so the synthetic Ctrl+C is clean.
            for mod in (Key.alt_l, Key.alt_r, Key.alt, Key.shift, Key.ctrl):
                try:
                    kb.release(mod)
                except Exception:
                    pass
            time.sleep(0.05)

            old_clip = _get_clipboard_text()
            sentinel = "\x00\x01verbic-no-selection\x01\x00"
            _set_clipboard_text(sentinel)

            kb.press(Key.ctrl)
            kb.press("c")
            kb.release("c")
            kb.release(Key.ctrl)
            time.sleep(0.15)

            new_clip = _get_clipboard_text()

            # Restore the user's original clipboard so a fix/answer doesn't
            # leave the selection (or our sentinel) sitting on it.
            try:
                if old_clip is not None:
                    _set_clipboard_text(old_clip)
            except Exception:
                pass

            # A real selection replaced the sentinel; an empty field left it.
            if new_clip and new_clip != sentinel:
                return new_clip
            return None
        except Exception:
            return None

    def _process_text(self, text, char_count, use_selection=False, context=None, use_select_all=False):
        if not self._any_transformation_selected():
            self._notify("Verbic", "Enable Grammar (or a tone) in the tray menu first.")
            return

        corrected = self._run_correction(text, context=context)

        if corrected is None:
            self._notify("Verbic", self._provider_failure_message())
            return

        if corrected.strip() == text.strip():
            self._notify("Verbic", "Text looks good — no changes needed.")
            return

        if not self._looks_like_valid_correction(text, corrected):
            self._notify("Verbic", "The model returned an unusable response. Try again or switch engines.")
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
        # pystray.Icon.notify uses Shell_NotifyIcon balloon tips — reliable
        # on Windows 10/11. The old win10toast path used legacy WinRT APIs
        # that no-op silently on many Win11 builds, making every "auto-suggest
        # failed because…" message invisible to the user.
        if self._icon is not None:
            try:
                self._icon.notify(message, title=title)
                return
            except Exception:
                pass
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=3, threaded=True)
        except Exception:
            pass

    def _apply_runtime_config(self, new_config, rebuild_client=False):
        """Persist `new_config` and apply the parts that affect live behavior
        (AI client, hotkeys, toolbar) without a restart."""
        self._config = new_config
        save_config(self._config)
        if rebuild_client:
            self._build_client()
        self.monitor.set_hotkeys(self._config.get("hotkeys") or {})
        self._toolbar_config = dict(self._config.get("toolbar") or {})
        self._enable_selection_button = self._config.get("selection_button", True)
        try:
            if self._icon is not None:
                self._icon.update_menu()
                self._refresh_tooltip()
        except Exception:
            pass

    def _open_shortcuts(self, icon=None, item=None):
        def _run():
            try:
                ShortcutsWindow(self._config, lambda cfg: self._apply_runtime_config(cfg)).open()
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    def _open_settings(self, icon, item):
        # Guard against pystray's default-action firing twice on a double-click.
        with self._settings_open_lock:
            if self._settings_open:
                return
            self._settings_open = True

        def on_save(new_config):
            self._apply_runtime_config(new_config, rebuild_client=True)

        def build_test_client(engine, provider_key, provider_config):
            """Construct a one-shot client matching what the user has typed
            into the Settings UI (without requiring Save first)."""
            try:
                if engine != "ai":
                    return None
                if provider_key == "ollama":
                    return OllamaClient(model=provider_config.get("model") or "llama3.2:3b")
                if provider_key == "claude":
                    return ClaudeClient(
                        api_key=provider_config.get("api_key", ""),
                        model=provider_config.get("model") or "claude-sonnet-4-20250514",
                    )
                info = PROVIDERS.get(provider_key, PROVIDERS["custom"])
                base_url = provider_config.get("base_url") or info.get("base_url") or ""
                return OpenAICompatibleClient(
                    api_key=provider_config.get("api_key", ""),
                    model=provider_config.get("model") or info.get("default_model", ""),
                    base_url=base_url,
                    provider_name=info.get("label", provider_key),
                )
            except Exception:
                return None

        settings = SettingsWindow(self._config, on_save, build_test_client=build_test_client)

        def _run():
            try:
                settings.open()
            finally:
                # Settings.mainloop() returned, the window is gone. Clear the
                # guard so future opens succeed.
                with self._settings_open_lock:
                    self._settings_open = False

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _toggle_pause(self, icon, item):
        self._paused_globally = not self._paused_globally
        try:
            if self._paused_globally:
                self.monitor.pause()
            else:
                self.monitor.resume()
        except Exception:
            pass
        try:
            if self._icon is not None:
                self._icon.update_menu()
                self._refresh_tooltip()
        except Exception:
            pass
        self._notify(
            "Verbic",
            "Paused — corrections disabled." if self._paused_globally
            else "Resumed — corrections active.",
        )

    def _is_paused(self, item):
        return self._paused_globally

    def _check_updates(self, icon, item):
        # Manual check from the tray: show result, proceed with install if newer.
        updater.check_in_background(silent=False, notify=self._notify, ask=lambda v: True)

    def _open_about(self, icon, item):
        def _show():
            try:
                root = tk.Tk()
                root.title("About Verbic")
                root.geometry("420x340")
                root.resizable(False, False)
                pad = ttk.Frame(root, padding=20)
                pad.pack(fill="both", expand=True)
                tk.Label(pad, text="Verbic", font=("Segoe UI", 16, "bold")).pack(anchor="w")
                tk.Label(pad, text="Write better. Everywhere.", font=("Segoe UI", 10, "italic"), fg="#6366F1").pack(anchor="w")
                tk.Label(pad, text=f"Version {APP_VERSION}", font=("Segoe UI", 10), fg="#555").pack(anchor="w")
                tk.Label(pad, text="© Sand Castle LLC", font=("Segoe UI", 9), fg="#777").pack(anchor="w", pady=(0, 10))
                tk.Label(pad, text=(
                    "Hotkeys:\n"
                    "  Ctrl+Shift+G    Fix selected text or whole field\n"
                    "  Ctrl+Space      Apply suggestion (or fix selection if no overlay)\n"
                    "  Ctrl+Alt+X      Set highlighted text as writing context\n"
                    "  Ctrl+Alt+A      Draft an answer using the context"
                ), justify="left", font=("Segoe UI", 9), fg="#333").pack(anchor="w", pady=(0, 10))
                tk.Label(
                    pad,
                    text=(
                        "Verbic is provided AS IS, without warranty. Always review "
                        "automated changes before relying on them. Not for safety-critical, "
                        "legal, medical, or regulated use without independent review."
                    ),
                    justify="left", anchor="w", wraplength=380,
                    font=("Segoe UI", 8), fg="#7a4f00", bg="#fff8e1",
                    padx=8, pady=6,
                ).pack(fill="x", pady=(0, 10))
                btn_row = ttk.Frame(pad)
                btn_row.pack(fill="x")
                ttk.Button(btn_row, text="View License", command=self._open_eula).pack(side="left")
                ttk.Button(btn_row, text="Close", command=root.destroy).pack(side="right")
                root.mainloop()
            except Exception:
                pass
        threading.Thread(target=_show, daemon=True).start()

    def _on_context_hotkey(self):
        """Ctrl+Alt+X — capture current selection as writing context (runs in thread)."""
        threading.Thread(target=self._capture_context_from_selection, daemon=True).start()

    def _capture_context_from_selection(self):
        selected = self._get_selected_text()
        if not selected or not selected.strip():
            self._notify("Verbic", "No text selected. Highlight text first.")
            return
        self._close_selection_button()
        self._apply_context(selected)

    def _clear_context(self, icon=None, item=None):
        self._writing_context = ""
        self._config["writing_context"] = ""
        save_config(self._config)
        try:
            if self._icon is not None:
                self._icon.update_menu()
                self._refresh_tooltip()
        except Exception:
            pass
        self._notify("Verbic", "Writing context cleared.")

    def _set_clipboard_as_context(self, icon=None, item=None):
        clip = self._get_clipboard_context()
        if not clip or not clip.strip():
            self._notify("Verbic", "Clipboard is empty. Copy some text first.")
            return
        self._apply_context(clip)

    def _apply_context(self, text):
        """Set `text` as the active writing context, persist, and notify."""
        text = (text or "").strip()
        if not text:
            return
        self._writing_context = text
        self._config["writing_context"] = text
        save_config(self._config)
        try:
            if self._icon is not None:
                self._icon.update_menu()
                self._refresh_tooltip()
        except Exception:
            pass
        preview = text[:60] + "…" if len(text) > 60 else text
        self._notify("Verbic", f"Context set: {preview}")

        # Speculation mode: eagerly pre-draft the answer so pressing the answer
        # hotkey later returns instantly.
        self._speculative_answer = None
        self._speculative_answer_for = None
        if self.options.get("speculation"):
            threading.Thread(target=self._predraft_answer, args=(text,), daemon=True).start()

    def _predraft_answer(self, question):
        try:
            prompt = self.prompt_builder.build_answer(question, writing_context=question)
            answer = self.client.generate(prompt)
            if answer and answer.strip():
                self._speculative_answer = answer.strip()
                self._speculative_answer_for = question
                _dlog("tray", "speculation: pre-drafted answer ready")
        except Exception:
            pass

    def _on_selection_made(self, x, y, kind="drag"):
        """Mouse selection detected — pop the floating action toolbar near the
        release point, but only if there's actually a text selection.

        `kind` is "drag" (a reliable text gesture) or "click" (double/triple-
        click, which also fires on app icons, buttons, and list items). To
        avoid the toolbar appearing on every double-click, we verify a real
        text selection via UI Automation before showing it. The check runs in
        a worker thread so the mouse listener never blocks."""
        if self._paused_globally or not self._enable_selection_button:
            return
        if self._suggestion_window is not None:
            return
        threading.Thread(target=self._maybe_show_toolbar, args=(x, y, kind), daemon=True).start()

    def _maybe_show_toolbar(self, x, y, kind):
        has = self._focused_has_selection()
        if has is True:
            self._show_selection_button(x, y)
        elif has is False:
            # UIA is sure there's no selection — definitely not a text select.
            return
        else:
            # UIA couldn't tell (app exposes no TextPattern). Trust an explicit
            # drag gesture, but not an ambiguous double-click (which is what
            # pops the toolbar on app icons).
            if kind == "drag":
                self._show_selection_button(x, y)

    def _focused_has_selection(self, timeout=0.6):
        """Return True/False if UI Automation can tell whether the focused
        control has a non-empty text selection, or None if it can't (no
        TextPattern). No clipboard side effects."""
        result = {"val": None}

        def worker():
            try:
                import uiautomation as auto
                ctrl = auto.GetFocusedControl()
                if ctrl is None:
                    return
                tp = None
                for pid in (auto.PatternId.TextPattern2,
                            auto.PatternId.TextPattern,
                            auto.PatternId.TextEditPattern):
                    try:
                        tp = ctrl.GetPattern(pid)
                        if tp is not None:
                            break
                    except Exception:
                        continue
                if tp is None:
                    return  # can't tell — leave result as None
                try:
                    sels = tp.GetSelection()
                except Exception:
                    return
                if not sels:
                    result["val"] = False
                    return
                text = ""
                for r in sels:
                    try:
                        text += r.GetText(200) or ""
                    except Exception:
                        pass
                result["val"] = bool(text.strip())
            except Exception:
                return

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout)
        return result["val"]

    def _selection_toolbar_buttons(self):
        """Build the (label, callback) list for the floating toolbar from the
        user's enabled toolbar actions. Each callback spawns a worker thread so
        the Tk click handler returns immediately."""
        labels = {key: label for key, label in TOOLBAR_ACTIONS}
        # Surface the active tone on the Fix button so it's clear it reformats
        # in the configured tone (e.g. "✓ Fix · Professional").
        tone_names = {key: label for key, label, _prompt in TONES}
        active_tone = next((tone_names[k] for k in TONE_KEYS if self.options.get(k)), None)
        if active_tone:
            labels["fix_grammar"] = f"✓ Fix · {active_tone}"
        handlers = {
            "set_context": self._capture_context_from_selection,
            "draft_answer": self._draft_answer,
            "fix_grammar": self._fix_selection,
        }
        buttons = []
        for key, _label in TOOLBAR_ACTIONS:
            if not self._toolbar_config.get(key, False):
                continue
            worker = handlers.get(key)
            if worker is None:
                continue
            buttons.append((
                labels[key],
                lambda w=worker: threading.Thread(target=w, daemon=True).start(),
            ))
        return buttons

    def _show_selection_button(self, x, y):
        self._close_selection_button()

        buttons = self._selection_toolbar_buttons()
        if not buttons:
            return

        toolbar = SelectionToolbar(x, y, buttons)
        self._selection_button = toolbar

        # Auto-dismiss after 3.5s if the user ignores it.
        def _auto_close():
            if self._selection_button is toolbar:
                self._close_selection_button()
        self._selection_button_timer = threading.Timer(3.5, _auto_close)
        self._selection_button_timer.daemon = True
        self._selection_button_timer.start()

        threading.Thread(target=toolbar.open, daemon=True).start()

    def _close_selection_button(self):
        timer = self._selection_button_timer
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
            self._selection_button_timer = None
        button = self._selection_button
        self._selection_button = None
        if button is not None:
            try:
                button.close()
            except Exception:
                pass

    def _on_answer_hotkey(self):
        """Ctrl+Alt+A — draft a full answer using the current context."""
        threading.Thread(target=self._draft_answer, daemon=True).start()

    def _draft_answer(self):
        # The "question" to answer: prefer a live selection, then the pinned
        # writing context, then whatever the user has typed so far.
        question = self._get_selected_text()
        if question and question.strip():
            question = question.strip()
        elif self._writing_context.strip():
            question = self._writing_context.strip()
        else:
            buf, _count = self.monitor.snapshot_buffer()
            question = (buf or "").strip()

        if not question:
            self._notify("Verbic", "Nothing to answer. Select a question or set context first.")
            return

        # Speculation mode may have pre-drafted this exact question already.
        if self._speculative_answer and self._speculative_answer_for == question:
            _dlog("tray", "speculation: using pre-drafted answer")
            self._show_suggestion(self._speculative_answer, 0, is_insert=True, header="Draft answer")
            return

        prompt = self.prompt_builder.build_answer(question, writing_context=self._writing_context or None)
        answer = self.client.generate(prompt)
        if not answer or not answer.strip():
            self._notify("Verbic", self._provider_failure_message())
            return
        # Insert mode: there's no typed text to replace, so char_count=0 and
        # accepting pastes the answer at the caret.
        self._show_suggestion(answer.strip(), 0, is_insert=True, header="Draft answer")

    def _fix_selection(self):
        """Toolbar 'Fix' action — correct the current selection and show the
        result; accepting pastes it over the still-selected text."""
        if not self._any_transformation_selected():
            self._notify("Verbic", "Enable Grammar (or a tone) in the tray menu first.")
            return
        selected = self._get_selected_text()
        if not selected or not selected.strip():
            self._notify("Verbic", "No text selected to fix.")
            return
        corrected = self._run_correction(selected)
        if corrected is None:
            self._notify("Verbic", self._provider_failure_message())
            return
        if corrected.strip() == selected.strip():
            self._notify("Verbic", "Text looks good — no changes needed.")
            return
        if not self._looks_like_valid_correction(selected, corrected):
            self._notify("Verbic", "The model returned an unusable response.")
            return
        self._show_suggestion(corrected.strip(), 0, paste_selection=True)

    def _context_menu_label(self, item):
        if self._writing_context:
            short = self._writing_context[:35]
            if len(self._writing_context) > 35:
                short += "…"
            return f"Context: {short}"
        return "Context: none"

    def _toggle_selection_button(self, icon=None, item=None):
        self._enable_selection_button = not self._enable_selection_button
        self._config["selection_button"] = self._enable_selection_button
        save_config(self._config)
        if not self._enable_selection_button:
            self._close_selection_button()
        try:
            if self._icon is not None:
                self._icon.update_menu()
        except Exception:
            pass

    def _is_selection_button_on(self, item):
        return self._enable_selection_button

    def _quit(self, icon, item):
        self.monitor.stop()
        try:
            self._focus_watcher.stop()
        except Exception:
            pass
        icon.stop()

    def _provider_label(self, item):
        provider = self._config.get("provider", "ollama")
        provider_label = PROVIDERS.get(provider, {}).get("label", provider)
        return f"Provider: {provider_label}"

    def _tooltip_text(self):
        provider = self._config.get("provider", "ollama")
        provider_label = PROVIDERS.get(provider, {}).get("label", provider)
        status = "Paused" if self._paused_globally else "Active"
        ctx_line = ""
        if self._writing_context:
            short = self._writing_context[:40]
            if len(self._writing_context) > 40:
                short += "…"
            ctx_line = f"\nContext: {short}"
        return (
            f"Verbic — {status}\n"
            f"Provider: {provider_label}\n"
            f"Ctrl+Shift+G fix · Ctrl+Space apply"
            f"{ctx_line}"
        )

    def _open_eula(self, icon=None, item=None):
        import os as _os, sys as _sys, subprocess as _sp
        base_path = getattr(_sys, '_MEIPASS', _os.path.dirname(_os.path.abspath(__file__)))
        eula_path = _os.path.join(base_path, "EULA.txt")
        try:
            if _os.path.exists(eula_path):
                _sp.Popen(["notepad.exe", eula_path], creationflags=_sp.CREATE_NO_WINDOW)
        except Exception:
            pass

    def _refresh_tooltip(self):
        try:
            if self._icon is not None:
                self._icon.title = self._tooltip_text()
        except Exception:
            pass

    def _maybe_show_welcome(self):
        if self._config.get("welcome_seen"):
            return
        def _on_done(_picked=None):
            self._config["welcome_seen"] = True
            save_config(self._config)
            try:
                if self._icon is not None:
                    self._icon.update_menu()
                    self._refresh_tooltip()
            except Exception:
                pass
        WelcomeWindow(DEFAULT_ENGINE, _on_done).open()

    def run(self):
        import os
        import sys
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_path, "icon.png")
        image = Image.open(icon_path)

        # All tones live in one submenu so the tray stays compact even with the
        # expanded set. They're mutually exclusive (handled in _toggle_option).
        tone_submenu = pystray.Menu(
            *[
                pystray.MenuItem(label, self._toggle_option(key), checked=self._is_checked(key))
                for key, label, _prompt in TONES
            ]
        )

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: ("Resume" if self._paused_globally else "Pause") + " corrections",
                self._toggle_pause,
                checked=self._is_paused,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Fix Grammar", self._toggle_option("grammar"), checked=self._is_checked("grammar")),
            pystray.MenuItem("Tone", tone_submenu),
            pystray.MenuItem("Expand", self._toggle_option("expand"), checked=self._is_checked("expand")),
            pystray.MenuItem("Auto Suggest (typing)", self._toggle_option("auto_suggest"), checked=self._is_checked("auto_suggest")),
            pystray.MenuItem("Predictive (Flow) Mode", self._toggle_option("speculation"), checked=self._is_checked("speculation")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._context_menu_label, None, enabled=False),
            pystray.MenuItem("Set Clipboard as Context", self._set_clipboard_as_context),
            pystray.MenuItem("Draft Answer from Context", lambda icon, item: self._on_answer_hotkey()),
            pystray.MenuItem("Clear Context", self._clear_context, enabled=lambda item: bool(self._writing_context)),
            pystray.MenuItem("Show button on selection", self._toggle_selection_button, checked=self._is_selection_button_on),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._provider_label, None, enabled=False),
            pystray.MenuItem("Settings", self._open_settings, default=True),
            pystray.MenuItem("Shortcuts & Buttons", self._open_shortcuts),
            pystray.MenuItem("Check for Updates", self._check_updates),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("About", self._open_about),
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon("verbic", image, self._tooltip_text(), menu)
        self.monitor.start()
        self._focus_watcher.start()
        # Show first-run welcome dialog after a short delay so the tray icon
        # has a chance to appear behind it.
        threading.Timer(0.3, self._maybe_show_welcome).start()
        # Silently check for updates a few seconds after launch; auto-installs if newer.
        threading.Timer(4.0, lambda: updater.check_for_updates(
            silent=True, notify=self._notify, ask=None)).start()
        self._icon.run()
