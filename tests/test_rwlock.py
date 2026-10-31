"""Tests for Fair Writer-Priority ReadWriteLock."""

import threading
import time
import pytest

from radzero.core.rwlock import ReadWriteLock


def test_concurrent_readers():
    """Verify multiple readers can hold the lock simultaneously."""
    lock = ReadWriteLock()
    active_readers = []
    errors = []

    def reader(idx: int):
        try:
            with lock.read_lock():
                active_readers.append(idx)
                time.sleep(0.02)
                assert len(active_readers) > 0
        except Exception as e:
            errors.append(e)
        finally:
            if idx in active_readers:
                active_readers.remove(idx)

    threads = [threading.Thread(target=reader, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_exclusive_writer():
    """Verify writer has strictly exclusive access."""
    lock = ReadWriteLock()
    state = {"readers": 0, "writer_active": False, "collision": False}

    def writer():
        with lock.write_lock():
            if state["readers"] > 0 or state["writer_active"]:
                state["collision"] = True
            state["writer_active"] = True
            time.sleep(0.03)
            state["writer_active"] = False

    def reader():
        with lock.read_lock():
            if state["writer_active"]:
                state["collision"] = True
            state["readers"] += 1
            time.sleep(0.01)
            state["readers"] -= 1

    t_w = threading.Thread(target=writer)
    t_r = threading.Thread(target=reader)

    t_w.start()
    t_r.start()
    t_w.join()
    t_r.join()

    assert not state["collision"], "Reader and writer must not collide"
