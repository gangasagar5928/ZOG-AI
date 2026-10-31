"""Read-Write Lock (Parameter RW-Mutex) for Concurrency-Safe Hot-Patching.

Allows shared read locks for deterministic inference passes and exclusive
write locks for in-situ memory patching and parameter restoration.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Generator


class ReadWriteLock:
    """Fair Read-Write Lock supporting shared reader and exclusive writer acquisition."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._readers_ok = threading.Condition(self._lock)
        self._writers_ok = threading.Condition(self._lock)
        self._readers: int = 0
        self._writers_waiting: int = 0
        self._writer_active: bool = False

    def acquire_read(self) -> None:
        """Acquire shared read lock. Blocks if writer is active or waiting (prevents writer starvation)."""
        with self._lock:
            while self._writer_active or self._writers_waiting > 0:
                self._readers_ok.wait()
            self._readers += 1

    def release_read(self) -> None:
        """Release shared read lock."""
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                self._writers_ok.notify()

    def acquire_write(self) -> None:
        """Acquire exclusive write lock. Blocks until all active readers and writers finish."""
        with self._lock:
            self._writers_waiting += 1
            while self._writer_active or self._readers > 0:
                self._writers_ok.wait()
            self._writers_waiting -= 1
            self._writer_active = True

    def release_write(self) -> None:
        """Release exclusive write lock."""
        with self._lock:
            self._writer_active = False
            # Prioritize waking waiting readers, else writers
            if self._writers_waiting > 0:
                self._writers_ok.notify()
            else:
                self._readers_ok.notify_all()

    @contextmanager
    def read_lock(self) -> Generator[None, None, None]:
        """Context manager for shared parameter read lock."""
        self.acquire_read()
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write_lock(self) -> Generator[None, None, None]:
        """Context manager for exclusive parameter write lock."""
        self.acquire_write()
        try:
            yield
        finally:
            self.release_write()
