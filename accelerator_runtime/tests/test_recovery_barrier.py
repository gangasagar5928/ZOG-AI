"""
Unit tests for HardwareRecoveryBarrier and In-Place DMA Restoration.
"""

import unittest
from src.concurrency.rw_mutex import ReadWriteMutex
from src.model.member1_model import create_or_load_member1_model
from src.model.shadow_mirror import HostPinnedShadowMirror
from src.profiling.latency_profiler import DualDomainLatencyProfiler
from src.runtime.cuda_engine import CUDAExecutionEngine
from src.runtime.recovery_barrier import HardwareRecoveryBarrier
from src.runtime.fault_injector import FaultInjectionEngine
from src.config import FaultType


class TestHardwareRecoveryBarrier(unittest.TestCase):

    def setUp(self):
        self.model = create_or_load_member1_model()
        self.rw_mutex = ReadWriteMutex("TestBarrierMutex")
        self.shadow_mirror = HostPinnedShadowMirror(self.model, pin_memory=False)
        self.profiler = DualDomainLatencyProfiler()
        self.engine = CUDAExecutionEngine(self.model, self.rw_mutex)
        self.barrier = HardwareRecoveryBarrier(
            self.engine,
            self.shadow_mirror,
            self.rw_mutex,
            self.profiler
        )
        self.injector = FaultInjectionEngine(self.engine, self.rw_mutex)

    def test_fault_injection_and_atomic_recovery(self):
        """Simulates fault injection followed by atomic recovery barrier restoration."""
        # 1. Baseline check
        is_intact, corrupted = self.shadow_mirror.verify_integrity(self.engine.model)
        self.assertTrue(is_intact)

        # 2. Inject fault
        fault = self.injector.inject_fault(
            fault_type=FaultType.BIT_FLIP,
            element_count=10
        )
        self.assertIsNotNone(fault)
        self.assertTrue(self.injector.active_fault is not None)

        # 3. Model should now be detected as corrupted
        is_intact, corrupted = self.shadow_mirror.verify_integrity(self.engine.model)
        self.assertFalse(is_intact)
        self.assertGreater(len(corrupted), 0)

        # 4. Trigger Hardware Recovery Barrier
        recovery_result = self.barrier.execute_recovery()
        self.injector.clear_fault_state()

        self.assertEqual(recovery_result["status"], "RECOVERY_COMPLETE")
        self.assertTrue(recovery_result["barrier_enforced"])
        self.assertGreater(recovery_result["bytes_transferred"], 0)

        # 5. Model must now be 100% restored
        is_intact, corrupted = self.shadow_mirror.verify_integrity(self.engine.model)
        self.assertTrue(is_intact)
        self.assertEqual(len(corrupted), 0)

        # 6. Verify profiler telemetry
        stats = self.profiler.get_recovery_stats()
        self.assertEqual(stats["total_recoveries"], 1)
        self.assertGreater(stats["latest"]["host_end_to_end_ms"], 0)


if __name__ == "__main__":
    unittest.main()
