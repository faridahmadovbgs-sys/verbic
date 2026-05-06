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
