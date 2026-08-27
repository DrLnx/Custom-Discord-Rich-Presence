"""A cross-platform single-instance lock.

Checking ``/proc`` told us whether a pid was still alive on Linux and nothing
at all on Windows.  An advisory lock on the pidfile answers the same question
everywhere and cannot go stale: if the lock can be taken, nobody is holding
it, whatever the file happens to say.
"""

from __future__ import annotations

import os
from pathlib import Path

from .paths import WINDOWS

if WINDOWS:  # pragma: no cover - platform specific
    import msvcrt
else:  # pragma: no cover - platform specific
    import fcntl


def _try_lock(handle) -> bool:
    try:
        if WINDOWS:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(handle) -> None:
    try:
        if WINDOWS:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


class PidLock:
    """Held for the daemon's lifetime; released by the OS however it dies."""

    def __init__(self, path: Path):
        self.path = path
        self._handle = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, "a+")
        if not _try_lock(handle):
            handle.close()
            return False
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is None:
            return
        _unlock(self._handle)
        self._handle.close()
        self._handle = None
        try:
            self.path.unlink()
        except OSError:
            pass


def running_pid(path: Path) -> int | None:
    """The pid of the live daemon, or None when the lock is free."""
    if not path.exists():
        return None
    try:
        handle = open(path, "a+")
    except OSError:
        return None
    try:
        if _try_lock(handle):
            # Nobody home. The file is a leftover; the caller may clean it up.
            _unlock(handle)
            return None
        handle.seek(0)
        try:
            return int(handle.read().strip() or 0) or None
        except ValueError:
            return -1  # locked by something, pid unreadable
    finally:
        handle.close()
