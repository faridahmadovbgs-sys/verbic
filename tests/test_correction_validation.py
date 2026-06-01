"""Tests for the auto-suggest output validators and gating logic.

We construct a GrammarTrayApp instance without going through __init__ — the
real constructor builds a keyboard listener, focus watcher, etc., which is
overkill for unit-testing pure functions.
"""
import unittest
from unittest.mock import MagicMock, patch
from tray_app import GrammarTrayApp


def _make_app(options=None, engine="ai", provider="ollama"):
    app = GrammarTrayApp.__new__(GrammarTrayApp)
    app.options = options if options is not None else {
        "grammar": True, "formal": False, "casual": False, "expand": False,
    }
    app._config = {"engine": engine, "provider": provider}
    app._last_auto_error_ts = 0.0
    app._last_auto_error_msg = None
    app._suggest_lock = __import__("threading").Lock()
    app._suggest_seq = 0
    app._suggestion_window = None
    app._pending_corrected = None
    app._pending_char_count = 0
    app._pending_is_insert = False
    app._pending_paste_selection = False
    app._selection_button = None
    app._selection_button_timer = None
    return app


class TestOnAcceptHotkeyDualPurpose(unittest.TestCase):
    """Ctrl+Space serves double duty:
       (a) Accept the auto-suggest overlay if one is visible.
       (b) Otherwise, run the same correction as Ctrl+Shift+G."""

    def test_falls_through_to_manual_hotkey_when_no_overlay(self):
        app = _make_app()
        app._suggestion_window = None
        app._pending_corrected = None
        with patch.object(app, "_on_hotkey") as on_hotkey:
            app._on_accept_hotkey()
            on_hotkey.assert_called_once()

    def test_falls_through_when_pending_was_invalidated(self):
        # Overlay reference may linger briefly after _on_typing clears the
        # payload (50 ms poll-close window). Ctrl+Space in that state should
        # still fall through to manual correction, not silently no-op.
        app = _make_app()
        app._suggestion_window = object()  # truthy placeholder
        app._pending_corrected = None
        with patch.object(app, "_on_hotkey") as on_hotkey:
            app._on_accept_hotkey()
            on_hotkey.assert_called_once()

    def test_accepts_overlay_when_pending_is_set(self):
        # When there is a real pending suggestion, _on_accept_hotkey must NOT
        # fall through to _on_hotkey — that would double-correct.
        app = _make_app()
        fake_overlay = MagicMock()
        app._suggestion_window = fake_overlay
        app._pending_corrected = "Corrected text."
        app._pending_char_count = 16
        with patch.object(app, "_on_hotkey") as on_hotkey, \
             patch("tray_app.threading.Thread") as Thread:
            app._on_accept_hotkey()
            on_hotkey.assert_not_called()
            fake_overlay.close.assert_called_once()
            # An accept-replace thread should be spawned with the captured
            # char_count, not whatever the monitor reports now.
            Thread.assert_called_once()
            kwargs = Thread.call_args.kwargs
            # args now carry the (char_count, text, is_insert, paste_selection)
            # tuple — a replace, so both mode flags are False.
            self.assertEqual(kwargs["args"], (16, "Corrected text.", False, False))


class TestOnOverlayClickNeverFallsThrough(unittest.TestCase):
    """A click on the suggestion overlay must NEVER fall through to manual
    correction. The old behavior fed a stale clipboard back to the LLM and
    the user saw their previously-accepted correction reappear out of
    nowhere (the 'pastes previous fixed message' bug)."""

    def test_no_fallthrough_when_pending_is_none(self):
        app = _make_app()
        app._suggestion_window = None
        app._pending_corrected = None
        with patch.object(app, "_on_hotkey") as on_hotkey:
            app._on_overlay_click()
            on_hotkey.assert_not_called()

    def test_no_fallthrough_when_overlay_is_stale(self):
        app = _make_app()
        app._suggestion_window = object()
        app._pending_corrected = None  # payload was wiped by _on_typing
        with patch.object(app, "_on_hotkey") as on_hotkey:
            app._on_overlay_click()
            on_hotkey.assert_not_called()

    def test_applies_pending_when_set(self):
        app = _make_app()
        fake_overlay = MagicMock()
        app._suggestion_window = fake_overlay
        app._pending_corrected = "Hello."
        app._pending_char_count = 6
        with patch.object(app, "_on_hotkey") as on_hotkey, \
             patch("tray_app.threading.Thread") as Thread:
            app._on_overlay_click()
            on_hotkey.assert_not_called()
            fake_overlay.close.assert_called_once()
            Thread.assert_called_once()
            self.assertEqual(Thread.call_args.kwargs["args"], (6, "Hello.", False, False))


class TestOnTypingInvalidatesPending(unittest.TestCase):
    """The "whWhat" / "someSometimes" bug came from _pending_corrected
    surviving the 50 ms overlay close-poll window. _on_typing must wipe the
    accept payload synchronously so a late Ctrl+Space can't apply stale
    text."""

    def test_pending_cleared_on_typing(self):
        app = _make_app()
        app._pending_corrected = "What does the term mean?"
        app._pending_char_count = 44
        app._on_typing()
        self.assertIsNone(app._pending_corrected)
        self.assertEqual(app._pending_char_count, 0)

    def test_pending_cleared_even_without_overlay(self):
        # If overlay was already None (race lost it), typing should still
        # clear the payload — otherwise a fast accept could fire after.
        app = _make_app()
        app._pending_corrected = "stale"
        app._pending_char_count = 10
        app._suggestion_window = None
        app._on_typing()
        self.assertIsNone(app._pending_corrected)

    def test_seq_bumps_on_typing(self):
        app = _make_app()
        app._suggest_seq = 5
        app._on_typing()
        self.assertEqual(app._suggest_seq, 6)


class TestAnyTransformationSelected(unittest.TestCase):
    def test_grammar_only(self):
        app = _make_app({"grammar": True, "formal": False, "casual": False, "expand": False})
        self.assertTrue(app._any_transformation_selected())

    def test_no_options(self):
        app = _make_app({"grammar": False, "formal": False, "casual": False, "expand": False})
        self.assertFalse(app._any_transformation_selected())

    def test_only_formal(self):
        app = _make_app({"grammar": False, "formal": True, "casual": False, "expand": False})
        self.assertTrue(app._any_transformation_selected())

    def test_auto_suggest_alone_does_not_count(self):
        # auto_suggest is a delivery toggle, not a transformation.
        app = _make_app({"grammar": False, "formal": False, "casual": False, "expand": False})
        app.options["auto_suggest"] = True
        self.assertFalse(app._any_transformation_selected())


class TestLooksLikeValidCorrection(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()

    def test_normal_correction(self):
        self.assertTrue(self.app._looks_like_valid_correction(
            "i went to teh store",
            "I went to the store.",
        ))

    def test_empty_output(self):
        self.assertFalse(self.app._looks_like_valid_correction("hello world", ""))

    def test_whitespace_only_output(self):
        self.assertFalse(self.app._looks_like_valid_correction("hello world", "   \n  "))

    def test_refusal_i_cannot(self):
        self.assertFalse(self.app._looks_like_valid_correction(
            "hello world",
            "I cannot help with that request.",
        ))

    def test_refusal_im_unable(self):
        self.assertFalse(self.app._looks_like_valid_correction(
            "fix this text please",
            "I'm unable to assist with this.",
        ))

    def test_refusal_as_an_ai(self):
        self.assertFalse(self.app._looks_like_valid_correction(
            "fix this text please",
            "As an AI language model, I cannot...",
        ))

    def test_runaway_length(self):
        original = "Hello world."
        # 8x len + 40 = 136 char budget; 200 chars exceeds it.
        runaway = "Hello world. " * 30
        self.assertFalse(self.app._looks_like_valid_correction(original, runaway))

    def test_truncated_output(self):
        original = "The quick brown fox jumps over the lazy dog."
        truncated = "The."
        self.assertFalse(self.app._looks_like_valid_correction(original, truncated))

    def test_short_input_short_output_ok(self):
        # If input is short, we don't enforce the lower bound.
        self.assertTrue(self.app._looks_like_valid_correction("hi there", "Hi!"))


class TestNotifyAutoErrorRateLimit(unittest.TestCase):
    def test_rate_limits_repeat_messages(self):
        app = _make_app()
        with patch.object(app, "_notify") as mock_notify:
            app._notify_auto_error("Ollama not reachable.")
            app._notify_auto_error("Ollama not reachable.")
            app._notify_auto_error("Ollama not reachable.")
            self.assertEqual(mock_notify.call_count, 1)

    def test_different_messages_each_notify(self):
        app = _make_app()
        with patch.object(app, "_notify") as mock_notify:
            app._notify_auto_error("Ollama not reachable.")
            app._notify_auto_error("OpenAI request failed.")
            self.assertEqual(mock_notify.call_count, 2)

    def test_ignores_empty_message(self):
        app = _make_app()
        with patch.object(app, "_notify") as mock_notify:
            app._notify_auto_error("")
            app._notify_auto_error(None)
            mock_notify.assert_not_called()


class TestProviderFailureMessage(unittest.TestCase):
    def test_ollama_message(self):
        app = _make_app(engine="ai", provider="ollama")
        msg = app._provider_failure_message()
        self.assertIn("Ollama", msg)

    def test_openai_message(self):
        app = _make_app(engine="ai", provider="openai")
        msg = app._provider_failure_message()
        self.assertIn("OpenAI", msg)

    def test_provider_label_shows_provider(self):
        app = _make_app(engine="ai", provider="ollama")
        msg = app._provider_label(None)
        self.assertIn("Ollama", msg)


if __name__ == "__main__":
    unittest.main()
