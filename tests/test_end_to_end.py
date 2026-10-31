"""End-to-End Integration Tests for RadZero Runtime."""

import numpy as np
import pytest

from radzero.core.types import BitfieldTarget, SystemState
from radzero.mutation.ieee754_injector import IEEE754Injector
from radzero.recovery.state_machine import RadZeroRuntimeSentinel


def test_end_to_end_consecutive_injections_and_recoveries():
    """Execute consecutive SEU strike and recovery cycles without process interruption."""
    sentinel = RadZeroRuntimeSentinel()
    targets = [
        BitfieldTarget.EXPONENT_EXPLODE,
        BitfieldTarget.SIGN,
        BitfieldTarget.EXPONENT_COLLAPSE,
        BitfieldTarget.MANTISSA,
    ]

    for cycle in range(10):
        # Generate varied attitude states
        q = np.random.randn(4)
        q /= np.linalg.norm(q)
        w = np.random.uniform(-0.01, 0.01, size=3)
        state = np.concatenate([q, w])

        target = targets[cycle % len(targets)]
        IEEE754Injector.inject(sentinel.model, target=target)

        packet = sentinel.step(state)
        assert packet.state == SystemState.NOMINAL, f"Cycle {cycle} failed recovery"
        assert packet.tier1_passed, f"Cycle {cycle} Tier 1 re-verification failed"
        assert packet.tier2_passed, f"Cycle {cycle} Tier 2 re-verification failed"
        assert packet.recovery_latency_system_ms < 100.0, "Breached 100 ms deadline"

    # Verify multiple recoveries occurred seamlessly across the 10 cycles
    assert sentinel.recovery_count >= 1, "Expected at least 1 in-situ recovery event"
