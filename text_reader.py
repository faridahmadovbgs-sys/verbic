"""Reads the focused text control's contents via Windows UI Automation."""
import threading


_uia_lock = threading.Lock()


def read_focused_text(timeout_seconds=1.5):
    """Return (full_text, caret_offset_or_None) for the focused control, or (None, None).

    UIA calls go through COM and can occasionally hang on misbehaving apps;
    a worker thread plus join-with-timeout keeps the caller responsive.
    """
    result = {"text": None, "caret": None}

    def worker():
        try:
            import uiautomation as auto
            # A previous worker hung inside a misbehaving app's UIA provider
            # still holds the lock. Give up instead of queuing behind it —
            # every blocked daemon thread would otherwise leak until the
            # process exits.
            if not _uia_lock.acquire(timeout=2.0):
                return
            try:
                control = auto.GetFocusedControl()
                if control is None:
                    return
                try:
                    vp = control.GetValuePattern()
                    if vp is not None:
                        val = vp.Value
                        if val is not None:
                            result["text"] = val
                except Exception:
                    pass
                if result["text"] is None:
                    try:
                        tp = control.GetTextPattern()
                        if tp is not None:
                            doc_range = tp.DocumentRange
                            text = doc_range.GetText(-1)
                            if text is not None:
                                result["text"] = text
                    except Exception:
                        pass
            finally:
                _uia_lock.release()
        except Exception:
            pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout_seconds)
    if t.is_alive():
        return None, None
    return result["text"], result["caret"]
