"""Auto-start tests.

These exercise the real registry, but against a scratch key
(HKCU\\Software\\Verbic\\TestRun) instead of the live Run key, so running the
suite can never switch a user's actual auto-start on or off. The legacy Startup
shortcut is likewise redirected into a temp directory.
"""
import os
import sys
import tempfile
import unittest

import autostart

try:
    import winreg
except ImportError:
    winreg = None

_TEST_KEY = r"Software\Verbic\TestRun"


@unittest.skipUnless(autostart.is_supported(), "Windows-only")
class TestAutostartRegistry(unittest.TestCase):
    def setUp(self):
        self._real_key = autostart._RUN_KEY
        self._real_shortcut = autostart._startup_shortcut_path
        autostart._RUN_KEY = _TEST_KEY
        self._tmp = tempfile.TemporaryDirectory()
        self._shortcut = os.path.join(self._tmp.name, "Verbic.lnk")
        autostart._startup_shortcut_path = lambda: self._shortcut

    def tearDown(self):
        for key in (_TEST_KEY, r"Software\Verbic"):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
            except OSError:
                pass
        autostart._RUN_KEY = self._real_key
        autostart._startup_shortcut_path = self._real_shortcut
        self._tmp.cleanup()

    def test_disabled_by_default(self):
        self.assertFalse(autostart.is_enabled())

    def test_enable_then_disable(self):
        self.assertTrue(autostart.enable())
        self.assertTrue(autostart.is_enabled())
        self.assertEqual(autostart._read_run_value(), autostart._launch_command())
        self.assertTrue(autostart.disable())
        self.assertFalse(autostart.is_enabled())
        self.assertIsNone(autostart._read_run_value())

    def test_disable_is_idempotent(self):
        self.assertTrue(autostart.disable())
        self.assertTrue(autostart.disable())

    def test_legacy_shortcut_counts_as_enabled(self):
        open(self._shortcut, "w").close()
        self.assertTrue(autostart.is_enabled())

    def test_enable_removes_legacy_shortcut(self):
        # Both mechanisms at once would launch two copies at logon.
        open(self._shortcut, "w").close()
        self.assertTrue(autostart.enable())
        self.assertFalse(os.path.exists(self._shortcut))

    def test_disable_removes_legacy_shortcut(self):
        open(self._shortcut, "w").close()
        self.assertTrue(autostart.disable())
        self.assertFalse(os.path.exists(self._shortcut))
        self.assertFalse(autostart.is_enabled())

    def test_set_enabled_round_trip(self):
        autostart.set_enabled(True)
        self.assertTrue(autostart.is_enabled())
        autostart.set_enabled(False)
        self.assertFalse(autostart.is_enabled())


class TestLaunchCommand(unittest.TestCase):
    def test_quoted(self):
        cmd = autostart._launch_command()
        self.assertTrue(cmd.startswith('"'))
        self.assertTrue(cmd.endswith('"'))

    def test_source_mode_points_at_main(self):
        if getattr(sys, "frozen", False):
            self.skipTest("frozen build launches the exe directly")
        self.assertIn("main.py", autostart._launch_command())


if __name__ == "__main__":
    unittest.main()
