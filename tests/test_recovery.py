"""Tests for Concurrency-Safe Hot-Patching and Recovery State Machine."""

import numpy as np
import pytest
import torch

from radzero.core.types import BitfieldTarget, KinematicLimits, SystemState
from radzero.mutation.ieee754_injector import IEEE754Injector
from radzero.recovery.checkpoint_mirror import DualCheckpointMirror
from radzero.recovery.state_machine import RadZeroRuntimeSentinel


def test_dual_checkpoint_mirror_initialization():
    """Verify primary and backup mirrors are initialized with identical weights and valid CRC-32."""
    limits = KinematicLimits()
    sentinel = RadZeroRuntimeSentinel(limits=limits)
    mirror = sentinel.mirror

    assert mirror.verify_full_mirror(use_backup=False), "Primary mirror must pass CRC-32 verification"
    assert mirror.verify_full_mirror(use_backup=True), "Backup mirror must pass CRC-32 verification"


def test_in_situ_recovery_restores_parameters_after_seu():
    """Verify corrupted parameter is restored in-situ without restarting process."""
    sentinel = RadZeroRuntimeSentinel()
    param = sentinel.model.block0.weight

    # Capture original tensor values
    orig_tensor = param.detach().cpu().clone()

    # Inject bit mutation
    strike = IEEE754Injector.inject(sentinel.model, layer_name="block0.weight", target=BitfieldTarget.EXPONENT_EXPLODE)
    assert not torch.equal(param.data, orig_tensor), "Parameter should be modified post-injection"

    # Execute step with nominal attitude input
    state = np.array([1.0, 0.0, 0.0, 0.0, 0.01, -0.01, 0.01])
    packet = sentinel.step(state)

    # In-situ recovery should have restored parameters and returned state to NOMINAL
    assert packet.state == SystemState.NOMINAL
    assert torch.allclose(param.data, orig_tensor, atol=1e-7), "Weights must match pre-mutation state"
    assert sentinel.recovery_count >= 1
    assert packet.recovery_latency_system_ms > 0.0


def test_safe_hold_escalation_when_mirrors_corrupted():
    """Verify escalation to SAFE_HOLD when shadow mirrors fail CRC-32 check."""
    sentinel = RadZeroRuntimeSentinel()

    # Corrupt both primary and backup mirrors
    sentinel.mirror.corrupt_mirror_for_testing("block0.weight", corrupt_backup=False)
    sentinel.mirror.corrupt_mirror_for_testing("block0.weight", corrupt_backup=True)

    # Inject SEU to force recovery
    IEEE754Injector.inject(sentinel.model, layer_name="block0.weight", target=BitfieldTarget.EXPONENT_EXPLODE)

    # Step runtime sentinel
    state = np.array([1.0, 0.0, 0.0, 0.0, 0.01, -0.01, 0.01])
    packet = sentinel.step(state)

    assert packet.state == SystemState.SAFE_HOLD, "Must transition to SAFE_HOLD when mirrors fail CRC"
    assert packet.safe_hold_active, "Safe-hold rate damping must be active"


def test_recovery_latency_profiling():
    """Verify dual-domain latency profiling records positive execution times."""
    sentinel = RadZeroRuntimeSentinel()
    IEEE754Injector.inject(
        sentinel.model, layer_name="block0.weight", target=BitfieldTarget.EXPONENT_EXPLODE
    )

    state = np.array([1.0, 0.0, 0.0, 0.0, 0.005, -0.005, 0.005])
    packet = sentinel.step(state)

    assert sentinel.recovery_count >= 1, "Expected recovery to trigger"
    assert packet.recovery_latency_system_ms > 0.0
    assert packet.recovery_latency_system_ms < 100.0, "Recovery latency must stay within 100 ms deadline"


def test_extreme_rate_input_no_unbound_local_error():
    """Verify that extreme rate input (omega >> omega_max) does not raise UnboundLocalError."""
    sentinel = RadZeroRuntimeSentinel()
    # Step with extreme angular velocity 1.5 rad/s (re-verification stress test)
    packet = sentinel.step([1.0, 0.0, 0.0, 0.0, 1.5, 0.0, 0.0])
    assert packet is not None
    assert packet.state in (SystemState.NOMINAL, SystemState.SAFE_HOLD)
