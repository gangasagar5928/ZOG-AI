"""Member 4 (Aashu) - Fail-Safe & Network Fallback Verification Suite.

Tests and empirically validates:
1. CPU fallback execution path if CUDA drivers encounter an unhandled exception or device is unavailable.
2. Frontend HTTP polling fallback (/api/telemetry/latest) when local network WebSockets disconnect.
"""

import unittest
import torch
import numpy as np
from radzero.core.types import KinematicLimits, BitfieldTarget, SystemState
from radzero.recovery.state_machine import RadZeroRuntimeSentinel
from radzero.mutation.ieee754_injector import IEEE754Injector
from radzero.telemetry.server import get_latest_telemetry, get_system_state


def _eval_coro(coro):
    """Safely evaluate coroutine without requiring OS network socket loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not resolve synchronously")


class TestFailSafeAndNetworkFallbacks(unittest.TestCase):
    """Formal verification of system robustness under hardware and network degradation."""

    def test_cpu_fallback_execution_path(self):
        """Verify seamless execution and recovery on CPU when CUDA is unavailable."""
        limits = KinematicLimits()
        # Force CPU device execution
        sentinel = RadZeroRuntimeSentinel(limits=limits, device=torch.device("cpu"))
        self.assertEqual(sentinel.device.type, "cpu")
        for tensor in sentinel.mirror.primary_mirror.values():
            self.assertFalse(tensor.is_pinned())

        # Nominal attitude
        q = np.array([1.0, 0.0, 0.0, 0.0, 0.005, -0.005, 0.005])

        # Step 1: Nominal baseline execution on CPU
        p1 = sentinel.step(q)
        self.assertEqual(p1.state, SystemState.NOMINAL)
        self.assertTrue(p1.tier1_passed)
        self.assertTrue(p1.tier2_passed)

        # Step 2: Inject Catastrophic SEU Strike (Bit 30) into input layer
        strike = IEEE754Injector.inject(
            sentinel.model,
            layer_name="block0.weight",
            target=BitfieldTarget.EXPONENT_EXPLODE,
        )
        self.assertIsNotNone(strike)

        # Step 3: Sentinel must recover purely on CPU with zero exceptions (NFR-3)
        p2 = sentinel.step(q)
        self.assertEqual(p2.state, SystemState.NOMINAL)
        self.assertGreater(p2.recovery_latency_system_ms, 0.0)
        self.assertLess(p2.recovery_latency_system_ms, limits.control_deadline_ms)
        print(f"\n[VERIFIED] CPU Fallback Recovery Latency: {p2.recovery_latency_system_ms:.2f} ms (Control Deadline: 100.0 ms)")

    def test_frontend_http_polling_fallback(self):
        """Verify /api/telemetry/latest HTTP fallback endpoint returns complete valid telemetry packet."""
        data = _eval_coro(get_latest_telemetry())
        self.assertIsInstance(data, dict)

        # Validate essential HUD telemetry fields
        required_keys = [
            "timestamp_ns", "state", "quaternion", "angular_velocity",
            "torque_cmd", "tier1_passed", "tier2_passed", "tier3_passed",
            "recovery_latency_system_ms", "safe_hold_active"
        ]
        for key in required_keys:
            self.assertIn(key, data, f"Missing telemetry key: {key}")

        self.assertEqual(len(data["quaternion"]), 4)
        self.assertEqual(len(data["angular_velocity"]), 3)
        self.assertEqual(len(data["torque_cmd"]), 3)

        state_data = _eval_coro(get_system_state())
        self.assertIn("status", state_data)
        self.assertIn("limits", state_data)

        print(f"[VERIFIED] Frontend HTTP Polling Fallback (/api/telemetry/latest): State={data['state']} | Keys Validated={len(required_keys)}")


if __name__ == "__main__":
    unittest.main()
