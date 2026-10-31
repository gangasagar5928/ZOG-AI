"""
Unit tests for REST endpoints and telemetry schemas.
"""

import unittest
import asyncio
from src.concurrency.rw_mutex import ReadWriteMutex
from src.model.member1_model import create_or_load_member1_model
from src.model.shadow_mirror import HostPinnedShadowMirror
from src.profiling.latency_profiler import DualDomainLatencyProfiler
from src.runtime.cuda_engine import CUDAExecutionEngine
from src.runtime.recovery_barrier import HardwareRecoveryBarrier
from src.runtime.fault_injector import FaultInjectionEngine
from src.api.routes import create_router, InjectFaultRequest, SetModeRequest
from src.config import OperationalMode, FaultType


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.model = create_or_load_member1_model()
        self.rw_mutex = ReadWriteMutex("APITestMutex")
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
        self.router = create_router(
            self.engine,
            self.barrier,
            self.injector,
            self.shadow_mirror,
            self.profiler,
            self.rw_mutex
        )

    def test_routes_existence(self):
        """Validates all required REST control endpoints are registered."""
        # Find route endpoints
        endpoint_functions = [route.endpoint.__name__ for route in self.router.routes]
        self.assertIn("get_health", endpoint_functions)
        self.assertIn("inject_fault", endpoint_functions)
        self.assertIn("trigger_recovery", endpoint_functions)
        self.assertIn("reset_runtime", endpoint_functions)
        self.assertIn("get_mode", endpoint_functions)
        self.assertIn("set_mode", endpoint_functions)
        self.assertIn("run_inference", endpoint_functions)
        self.assertIn("get_latest_telemetry", endpoint_functions)

    def test_direct_handler_execution(self):
        """Executes handler coroutines directly to verify response structures."""
        # Find endpoints
        handlers = {route.endpoint.__name__: route.endpoint for route in self.router.routes}

        # 1. Health
        health_resp = asyncio.run(handlers["get_health"]())
        self.assertEqual(health_resp["status"], "HEALTHY")
        self.assertEqual(health_resp["target_hardware"], "NVIDIA GeForce RTX 3050 Mobile")

        # 2. Inject
        req_inject = InjectFaultRequest(fault_type=FaultType.BIT_FLIP, element_count=5)
        inject_resp = asyncio.run(handlers["inject_fault"](req_inject))
        self.assertEqual(inject_resp["status"], "SUCCESS")

        # 3. Telemetry latest (Polling fallback)
        telem_resp = asyncio.run(handlers["get_latest_telemetry"]())
        self.assertIn("node", telem_resp)
        self.assertIn("gpu_hardware", telem_resp)
        self.assertIn("concurrency_lock", telem_resp)
        self.assertIn("profiling", telem_resp)
        self.assertTrue(telem_resp["integrity"]["has_active_fault"])

        # 4. Recover
        recover_resp = asyncio.run(handlers["trigger_recovery"]())
        self.assertEqual(recover_resp["status"], "RECOVERY_COMPLETE")

        # 5. Telemetry after recovery
        telem_after = asyncio.run(handlers["get_latest_telemetry"]())
        self.assertFalse(telem_after["integrity"]["has_active_fault"])
        self.assertTrue(telem_after["integrity"]["is_intact"])

        # 6. Mode switch
        req_mode = SetModeRequest(mode=OperationalMode.BENCHMARK)
        mode_resp = asyncio.run(handlers["set_mode"](req_mode))
        self.assertEqual(mode_resp["new_mode"], OperationalMode.BENCHMARK)
        self.assertEqual(self.engine.current_mode, OperationalMode.BENCHMARK)


if __name__ == "__main__":
    unittest.main()
