"""Tests for Classical Safe-Hold Controller."""

import numpy as np
import pytest

from radzero.core.safe_hold import SafeHoldController
from radzero.core.types import KinematicLimits


def test_safe_hold_rate_damping_calculation():
    """Verify tau_safe = -Kd * omega."""
    limits = KinematicLimits(tau_max=0.05, kd_safe=0.1, h_max=0.1, delta_t=0.1)
    controller = SafeHoldController(limits=limits)

    omega = np.array([0.02, -0.01, 0.03])
    tau, saturated = controller.compute_torque(omega)

    expected = -0.1 * omega  # [-0.002, 0.001, -0.003]
    np.testing.assert_allclose(tau, expected, atol=1e-6)
    assert not saturated


def test_safe_hold_torque_saturation():
    """Verify torque is clamped to [-tau_max, tau_max]."""
    limits = KinematicLimits(tau_max=0.05, kd_safe=1.0)
    controller = SafeHoldController(limits=limits)

    omega_high = np.array([0.2, -0.5, 0.0])  # Unclamped: [-0.2, 0.5, 0.0]
    tau, _ = controller.compute_torque(omega_high)

    assert tau[0] == -0.05
    assert tau[1] == 0.05
    assert tau[2] == 0.0


def test_safe_hold_momentum_capacity_limit():
    """Verify reaction-wheel momentum storage tracks integral and clamps at h_max."""
    limits = KinematicLimits(tau_max=0.05, kd_safe=1.0, h_max=0.01, delta_t=0.1)
    controller = SafeHoldController(limits=limits)

    # Apply sustained high angular velocity
    omega = np.array([0.5, 0.0, 0.0])
    for _ in range(5):
        tau, saturated = controller.compute_torque(omega)

    # Capacity clamped
    assert saturated
    assert np.linalg.norm(controller.momentum_storage) <= limits.h_max + 1e-6
