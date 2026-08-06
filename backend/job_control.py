# backend/job_control.py
"""Track the single active pipeline subprocess for Stop."""

from __future__ import annotations

import subprocess
import threading
from typing import Optional

_lock = threading.Lock()
_current: Optional[subprocess.Popen] = None
_label: str = ""


def set_current(proc: subprocess.Popen | None, label: str = "") -> None:
    global _current, _label
    with _lock:
        _current = proc
        _label = label or ""


def get_label() -> str:
    with _lock:
        return _label


def is_running() -> bool:
    with _lock:
        if _current is None:
            return False
        return _current.poll() is None


def stop(timeout: float = 5.0) -> str:
    """
    Kill the active job. Does NOT undo files already written.
    Returns a short status message for the UI.
    """
    global _current, _label
    with _lock:
        proc = _current
        label = _label or "job"

    if proc is None or proc.poll() is not None:
        return "No job is currently running."

    try:
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        msg = (
            f"Stopped: {label} (PID {proc.pid}). "
            "Already written files were kept — there is no undo."
        )
    except Exception as e:
        msg = f"Stop failed: {type(e).__name__}: {e}"
    finally:
        set_current(None, "")
    return msg