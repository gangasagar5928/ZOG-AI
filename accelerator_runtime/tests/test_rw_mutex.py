"""
Unit tests for ReadWriteMutex concurrency safety and mutual exclusion.
"""

import time
import threading
import unittest
from src.concurrency.rw_mutex import ReadWriteMutex


class TestReadWriteMutex(unittest.TestCase):

    def setUp(self):
        self.mutex = ReadWriteMutex("TestMutex")

    def test_concurrent_readers(self):
        """Multiple threads should be able to hold the read lock simultaneously."""
        concurrency_count = 5
        acquired_readers = []
        barrier = threading.Barrier(concurrency_count)

        def reader_task():
            with self.mutex.read_lock():
                acquired_readers.append(threading.get_ident())
                barrier.wait(timeout=2.0)
                time.sleep(0.05)

        threads = [threading.Thread(target=reader_task) for _ in range(concurrency_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3.0)

        self.assertEqual(len(acquired_readers), concurrency_count)
        self.assertEqual(self.mutex.get_status()["active_readers"], 0)

    def test_writer_mutual_exclusion(self):
        """An exclusive writer must prevent readers from entering until released."""
        writer_inside = False
        reader_entered_during_write = False

        def writer_task():
            nonlocal writer_inside
            with self.mutex.write_lock():
                writer_inside = True
                time.sleep(0.15)
                writer_inside = False

        def reader_task():
            nonlocal reader_entered_during_write
            time.sleep(0.05)  # Let writer acquire first
            with self.mutex.read_lock():
                if writer_inside:
                    reader_entered_during_write = True

        tw = threading.Thread(target=writer_task)
        tr = threading.Thread(target=reader_task)

        tw.start()
        tr.start()

        tw.join(timeout=2.0)
        tr.join(timeout=2.0)

        self.assertFalse(reader_entered_during_write, "Reader accessed shared resource while writer was active!")
        self.assertEqual(self.mutex.get_status()["total_writes"], 1)

    def test_writer_priority(self):
        """Waiting writer should prevent new readers from jumping the queue."""
        reader_sequence = []
        writer_finished = False

        # Start initial long reader
        self.mutex.acquire_read()

        def writer_task():
            nonlocal writer_finished
            with self.mutex.write_lock():
                writer_finished = True
                reader_sequence.append("WRITER")

        def prospective_reader():
            with self.mutex.read_lock():
                reader_sequence.append("LATE_READER")

        tw = threading.Thread(target=writer_task)
        tw.start()
        time.sleep(0.05)  # Ensure writer is queued in wait condition

        tr = threading.Thread(target=prospective_reader)
        tr.start()
        time.sleep(0.05)

        # Now release initial reader; queued writer should execute BEFORE prospective reader
        self.mutex.release_read()

        tw.join(timeout=2.0)
        tr.join(timeout=2.0)

        self.assertTrue(writer_finished)
        self.assertEqual(reader_sequence, ["WRITER", "LATE_READER"])


if __name__ == "__main__":
    unittest.main()
