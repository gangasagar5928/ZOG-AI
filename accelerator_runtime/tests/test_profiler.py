"""
Unit tests for DualDomainLatencyProfiler.
"""

import unittest
from src.profiling.latency_profiler import DualDomainLatencyProfiler, LatencyRecord


class TestDualDomainLatencyProfiler(unittest.TestCase):

    def setUp(self):
        self.profiler = DualDomainLatencyProfiler(history_size=50)

    def test_record_and_throughput_computation(self):
        """Profiler should accurately compute PCIe DMA throughput and latency metrics."""
        bytes_transferred = 10 * 1024 * 1024  # 10 MB
        dma_ms = 2.0  # 2 ms -> 0.002 sec
        # Expected throughput: (10 MB / 1024) / 0.002 = 0.009765 GB / 0.002 s = ~4.88 GB/s

        record = self.profiler.register_recovery(
            dma_ms=dma_ms,
            infer_ms=1.5,
            barrier_ms=0.2,
            end_to_end_ns=4_000_000,  # 4 ms
            lock_wait_ns=100_000,     # 0.1 ms
            bytes_transferred=bytes_transferred
        )

        self.assertAlmostEqual(record.device_dma_ms, 2.0, places=3)
        self.assertAlmostEqual(record.host_end_to_end_ms, 4.0, places=3)
        self.assertGreater(record.throughput_gbps, 4.0)

        stats = self.profiler.get_recovery_stats()
        self.assertEqual(stats["total_recoveries"], 1)
        self.assertIsNotNone(stats["latest"])
        self.assertEqual(stats["latest"]["operation"], "RECOVERY_DMA_RESTORE")

    def test_inference_profiling(self):
        """Profiler should record inference times and compute FPS."""
        self.profiler.register_inference(10.0)  # 10 ms -> ~100 FPS
        self.profiler.register_inference(10.0)

        stats = self.profiler.get_inference_stats()
        self.assertEqual(stats["total_inferences"], 2)
        self.assertAlmostEqual(stats["avg_ms"], 10.0, places=2)
        self.assertAlmostEqual(stats["estimated_fps"], 100.0, places=1)


if __name__ == "__main__":
    unittest.main()
