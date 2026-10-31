"""
Read-Write Parameter Mutex (RWLock).
Coordinates nominal inference (shared read lock) and the recovery engine (exclusive write lock).

Key guarantees:
1. Shared Read Lock: Multiple concurrent inference executions can occur simultaneously.
2. Exclusive Write Lock: Recovery engine gets exclusive access to device parameters.
   No inference can read while weights are in-place overwritten from host-pinned shadow mirrors.
3. Writer-Priority: Recovery tasks do not suffer from read starvation under high inference load.
4. Dual-mode API: Supports both sync ('with mutex.read_lock():') and async ('async with mutex.read_lock():').
"""

import threading
import asyncio
import time
from contextlib import contextmanager, asynccontextmanager
from typing import Dict, Any


class ReadWriteMutex:
    """
    Writer-preferring Read-Write Mutex with dual sync/async support and telemetry instrumentation.
    """

    def __init__(self, name: str = "ParamMutex"):
        self.name = name
        self._lock = threading.Condition(threading.Lock())
        self._async_lock = asyncio.Condition(asyncio.Lock()) if hasattr(asyncio, "Condition") else None

        self._readers: int = 0
        self._writers_waiting: int = 0
        self._writer_active: bool = False
        self._writer_tid: int = 0

        # Telemetry counters
        self._total_reads: int = 0
        self._total_writes: int = 0
        self._contention_events: int = 0
        self._last_lock_wait_ns: int = 0

    # ---------------- Synchronous Interface ----------------

    def acquire_read(self, timeout: float = None) -> bool:
        """Acquire shared read lock. Blocks if a writer is active or waiting."""
        t_start = time.perf_counter_ns()
        with self._lock:
            # Wait while writer is active or writers are queued (writer-priority)
            while self._writer_active or self._writers_waiting > 0:
                self._contention_events += 1
                if not self._lock.wait(timeout=timeout):
                    return False
            self._readers += 1
            self._total_reads += 1
            self._last_lock_wait_ns = time.perf_counter_ns() - t_start
            return True

    def release_read(self):
        """Release shared read lock. Notifies waiting writer if last reader exits."""
        with self._lock:
            if self._readers <= 0:
                raise RuntimeError("Read lock released more times than acquired")
            self._readers -= 1
            if self._readers == 0:
                self._lock.notify_all()

    def acquire_write(self, timeout: float = None) -> bool:
        """Acquire exclusive write lock for recovery. Blocks all new readers."""
        t_start = time.perf_counter_ns()
        with self._lock:
            self._writers_waiting += 1
            try:
                # Wait until all active readers and any active writer drain
                while self._readers > 0 or self._writer_active:
                    self._contention_events += 1
                    if not self._lock.wait(timeout=timeout):
                        return False
                self._writer_active = True
                self._writer_tid = threading.get_ident()
                self._total_writes += 1
                self._last_lock_wait_ns = time.perf_counter_ns() - t_start
                return True
            finally:
                self._writers_waiting -= 1

    def release_write(self):
        """Release exclusive write lock. Notifies all waiting readers and writers."""
        with self._lock:
            if not self._writer_active:
                raise RuntimeError("Write lock released while not held")
            self._writer_active = False
            self._writer_tid = 0
            self._lock.notify_all()

    @contextmanager
    def read_lock(self, timeout: float = None):
        """Context manager for shared read lock."""
        acquired = self.acquire_read(timeout=timeout)
        if not acquired:
            raise TimeoutError("Timeout acquiring shared read lock")
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write_lock(self, timeout: float = None):
        """Context manager for exclusive write lock."""
        acquired = self.acquire_write(timeout=timeout)
        if not acquired:
            raise TimeoutError("Timeout acquiring exclusive write lock")
        try:
            yield
        finally:
            self.release_write()

    # ---------------- Asynchronous Interface ----------------

    async def async_acquire_read(self):
        """Asynchronous acquisition of shared read lock using asyncio loop threadpool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.acquire_read)

    async def async_release_read(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.release_read)

    async def async_acquire_write(self):
        """Asynchronous acquisition of exclusive write lock using asyncio loop threadpool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.acquire_write)

    async def async_release_write(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.release_write)

    @asynccontextmanager
    async def async_read_lock(self):
        await self.async_acquire_read()
        try:
            yield
        finally:
            await self.async_release_read()

    @asynccontextmanager
    async def async_write_lock(self):
        await self.async_acquire_write()
        try:
            yield
        finally:
            await self.async_release_write()

    # ---------------- Status & Telemetry ----------------

    def get_status(self) -> Dict[str, Any]:
        """Telemetry representation of current lock state."""
        with self._lock:
            return {
                "name": self.name,
                "active_readers": self._readers,
                "writers_waiting": self._writers_waiting,
                "writer_active": self._writer_active,
                "total_reads": self._total_reads,
                "total_writes": self._total_writes,
                "contention_events": self._contention_events,
                "last_lock_wait_ms": round(self._last_lock_wait_ns / 1_000_000.0, 4)
            }
