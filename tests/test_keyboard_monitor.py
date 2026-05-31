import os
import unittest
from unittest.mock import MagicMock, patch
from keyboard_monitor import KeyboardMonitor, _is_own_window


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

    def test_newline_resets_buffer(self):
        # Enter ends a paragraph (chat: message sent; editor: new line). The
        # previous text shouldn't ride along on the next auto-suggest.
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("a")
        monitor.add_newline()
        monitor.add_char("b")
        self.assertEqual(monitor.get_buffer(), "b")

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

    def test_snapshot_buffer_does_not_reset(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("a")
        monitor.add_char("b")
        monitor.add_char("c")
        text, count = monitor.snapshot_buffer()
        self.assertEqual(text, "abc")
        self.assertEqual(count, 3)
        # Buffer survives — unlike consume_buffer, snapshot is read-only.
        self.assertEqual(monitor.get_buffer(), "abc")
        self.assertEqual(monitor.get_char_count(), 3)

    def test_snapshot_buffer_atomic_pair(self):
        # The whole point of snapshot_buffer is that text length and count
        # come from the same buffer state. If they were captured separately
        # (get_buffer then get_char_count), a concurrent keystroke between
        # the two calls could leave them mismatched.
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        for ch in "hello":
            monitor.add_char(ch)
        text, count = monitor.snapshot_buffer()
        self.assertEqual(len(text), count)

    def test_newline_clears_char_count(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock())
        monitor.add_char("a")
        monitor.add_newline()
        self.assertEqual(monitor.get_char_count(), 0)


class TestOwnWindowFilter(unittest.TestCase):
    def test_zero_hwnd_returns_false(self):
        self.assertFalse(_is_own_window(0))
        self.assertFalse(_is_own_window(None))

    def test_own_pid_detected(self):
        # Fake the Win32 call so it returns this process's PID.
        own_pid = os.getpid()

        def fake_get_thread_pid(hwnd, pid_ptr):
            import ctypes
            pid_ptr._obj.value = own_pid
            return 1

        fake_user32 = MagicMock()
        fake_user32.GetWindowThreadProcessId = fake_get_thread_pid
        with patch("keyboard_monitor.ctypes.windll") as windll:
            windll.user32 = fake_user32
            self.assertTrue(_is_own_window(12345))

    def test_check_foreground_change_ignores_own_window(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock(), on_typing=MagicMock())
        monitor._last_fg_hwnd = 1111  # pretend we were tracking a foreign window
        monitor.add_char("a")  # put something in the buffer

        with patch("keyboard_monitor._is_own_window", return_value=True), \
             patch("keyboard_monitor.ctypes.windll") as windll:
            windll.user32.GetForegroundWindow.return_value = 2222  # own overlay
            monitor._check_foreground_change()

        # Buffer survived: the overlay foreground flash didn't reset it.
        self.assertEqual(monitor.get_buffer(), "a")
        # And we didn't update _last_fg_hwnd to point at the overlay.
        self.assertEqual(monitor._last_fg_hwnd, 1111)

    def test_check_foreground_change_resets_on_real_app_switch(self):
        monitor = KeyboardMonitor(on_hotkey=MagicMock(), on_typing=MagicMock())
        monitor._last_fg_hwnd = 1111
        monitor.add_char("a")

        with patch("keyboard_monitor._is_own_window", return_value=False), \
             patch("keyboard_monitor.ctypes.windll") as windll:
            windll.user32.GetForegroundWindow.return_value = 9999
            monitor._check_foreground_change()

        self.assertEqual(monitor.get_buffer(), "")
        self.assertEqual(monitor._last_fg_hwnd, 9999)


class TestMouseClickHandling(unittest.TestCase):
    """The mouse hook resets the buffer (cursor likely moved) but must NOT
    fire on_typing — otherwise it races against tk's window-level click
    handler when the click was on our overlay, wiping the accept payload
    before tk can read it. The race made click-to-accept fail on HighDPI."""

    def test_press_resets_buffer(self):
        on_typing = MagicMock()
        monitor = KeyboardMonitor(on_hotkey=MagicMock(), on_typing=on_typing)
        monitor.add_char("h")
        monitor.add_char("i")

        monitor._on_click(100, 200, "left", True)

        self.assertEqual(monitor.get_buffer(), "")

    def test_press_does_not_fire_on_typing(self):
        # The core regression fix in v1.0.8: mouse press must NOT invoke
        # the on_typing callback, otherwise click-on-overlay loses to the
        # mouse-vs-tk race and the user sees nothing happen on click.
        on_typing = MagicMock()
        monitor = KeyboardMonitor(on_hotkey=MagicMock(), on_typing=on_typing)
        monitor.add_char("x")

        monitor._on_click(100, 200, "left", True)

        on_typing.assert_not_called()

    def test_release_is_ignored(self):
        # _on_click also fires on release with pressed=False. Releases must
        # never reset state — only the press matters.
        on_typing = MagicMock()
        monitor = KeyboardMonitor(on_hotkey=MagicMock(), on_typing=on_typing)
        monitor.add_char("x")

        monitor._on_click(100, 200, "left", False)

        self.assertEqual(monitor.get_buffer(), "x")
        on_typing.assert_not_called()

    def test_bounds_lookup_still_works(self):
        # SuggestionWindow.point_is_inside_any_visible is kept around as a
        # public API even though _on_click no longer consults it. It may be
        # useful for future hit-testing needs.
        from suggestion_window import SuggestionWindow

        rect = (200, 300, 600, 360)
        with SuggestionWindow._bounds_lock:
            SuggestionWindow._visible_bounds.append(rect)
        try:
            self.assertTrue(SuggestionWindow.point_is_inside_any_visible(400, 320))
            self.assertFalse(SuggestionWindow.point_is_inside_any_visible(100, 100))
            self.assertFalse(SuggestionWindow.point_is_inside_any_visible(700, 320))
        finally:
            with SuggestionWindow._bounds_lock:
                SuggestionWindow._visible_bounds.remove(rect)


if __name__ == "__main__":
    unittest.main()
