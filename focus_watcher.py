"""Event-driven foreground-window watcher using SetWinEventHook.

This is more reliable than polling GetForegroundWindow on every keystroke
because Windows guarantees the callback fires the moment focus changes,
even if the user hasn't pressed a key yet (e.g., Alt+Tab + click in new app
+ start typing). With polling, the first keystroke in the new app could
slip through with stale buffer state.
"""
import ctypes
import os
import threading
from ctypes import wintypes


EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000

_OWN_PID = os.getpid()


def _is_own_window(hwnd):
    """Return True if hwnd belongs to the current process (e.g. our suggestion overlay)."""
    try:
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == _OWN_PID
    except Exception:
        return False


_WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD,
)


class FocusWatcher:
    def __init__(self, on_focus_change):
        self._on_focus_change = on_focus_change
        self._thread = None
        self._stop = threading.Event()
        self._proc_ref = None
        self._hook = None

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        user32 = ctypes.windll.user32

        def _callback(_hook, _event, hwnd, _id_obj, _id_child, _thread_id, _ms_time):
            try:
                # Ignore foreground events for our own windows (e.g. the
                # suggestion overlay briefly appearing) — they aren't real
                # app switches and would dismiss the overlay we just opened.
                if hwnd and _is_own_window(hwnd):
                    return
                if self._on_focus_change:
                    self._on_focus_change(hwnd)
            except Exception:
                pass

        # Keep a reference so the C trampoline isn't garbage-collected.
        self._proc_ref = _WinEventProcType(_callback)
        self._hook = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            0,
            self._proc_ref,
            0,
            0,
            WINEVENT_OUTOFCONTEXT,
        )
        if not self._hook:
            return

        # SetWinEventHook with WINEVENT_OUTOFCONTEXT requires a message pump on
        # the calling thread to deliver callbacks.
        msg = wintypes.MSG()
        while not self._stop.is_set():
            ret = user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1)
            if ret:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                self._stop.wait(0.05)

        try:
            user32.UnhookWinEvent(self._hook)
        except Exception:
            pass
        self._hook = None
