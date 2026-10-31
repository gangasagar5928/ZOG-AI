"""Tests for Tier 2: Rigid-Body Dynamic & Actuator Gate."""

import numpy as np
import pytest

from radzero.core.types import BreachType, KinematicLimits
from radzero.invariants.tier2_dynamics_gate import Tier2DynamicsGate


def test_tier2_nominal_torque_passes():
    """Verify nominal within-bounds torque passes all kinematic checks."""
    limits = KinematicLimits(tau_max=0.05, alpha_max=0.5, omega_max=0.05)
    gate = Tier2DynamicsGate(limits=limits)

    tau_nominal = [0.001, -0.002, 0.0015]
    omega_nominal = [0.005, -0.002, 0.003]

    passed, breaches, alpha, next_omega = gate.validate(tau_nominal, omega_nominal)
    assert passed, f"Nominal actuation must pass Tier 2 gate, got breaches: {breaches}"
    assert len(breaches) == 0


def test_tier2_catches_torque_saturation():
    """Verify torque exceeding tau_max (0.05 N*m) triggers saturation breach."""
    limits = KinematicLimits(tau_max=0.05)
    gate = Tier2DynamicsGate(limits=limits)

    tau_excessive = [0.055, 0.01, 0.01]  # 0.055 > 0.05
    omega = [0.001, 0.001, 0.001]

    passed, breaches, _, _ = gate.validate(tau_excessive, omega)
    assert not passed, "Torque > tau_max must fail Tier 2 gate"
    assert any(b.breach_type == BreachType.TIER2_TORQUE_SATURATION for b in breaches)


def test_tier2_catches_angular_accel_breach():
    """Verify angular acceleration exceeding alpha_max (0.5 rad/s^2) triggers breach."""
    # Using small inertia to amplify acceleration for testing
    limits = KinematicLimits(
        tau_max=0.1,
        alpha_max=0.5,
        inertia_matrix=np.diag([0.001, 0.001, 0.001]),
    )
    gate = Tier2DynamicsGate(limits=limits)

    tau = [0.05, 0.0, 0.0]  # alpha = 0.05 / 0.001 = 50 rad/s^2 >> 0.5
    omega = [0.0, 0.0, 0.0]

    passed, breaches, alpha, _ = gate.validate(tau, omega)
    assert not passed, "Acceleration > alpha_max must fail Tier 2 gate"
    assert any(b.breach_type == BreachType.TIER2_ANGULAR_ACCEL for b in breaches)


def test_tier2_catches_slew_rate_breach():
    """Verify integrated slew rate exceeding omega_max (0.05 rad/s) triggers breach."""
    limits = KinematicLimits(
        tau_max=0.05,
        alpha_max=2.0,
        omega_max=0.05,
        delta_t=0.1,
        inertia_matrix=np.diag([0.01, 0.01, 0.01]),
    )
    gate = Tier2DynamicsGate(limits=limits)

    # Initial angular velocity already near boundary
    omega_high = [0.048, 0.0, 0.0]
    tau = [0.04, 0.0, 0.0]  # alpha = 4 rad/s^2 -> delta_omega = 0.4 -> next_omega = 0.448 > 0.05

    passed, breaches, _, next_omega = gate.validate(tau, omega_high)
    assert not passed, "Slew-rate > omega_max must fail Tier 2 gate"
    assert any(b.breach_type == BreachType.TIER2_SLEW_RATE for b in breaches)


def test_tier2_maximum_torque_on_z_axis_consistent_with_alpha_max():
    """Verify that commanding maximum legal torque (0.05 N*m) on the z-axis (I_zz=0.08) from rest passes both alpha_max and omega_max."""
    limits = KinematicLimits()  # Uses defaults: tau_max=0.05, alpha_max=0.65, omega_max=0.08, I_zz=0.08
    gate = Tier2DynamicsGate(limits=limits)

    # Command maximum legal torque on z-axis directly from rest
    # alpha_z = 0.05 / 0.08 = 0.625 rad/s^2 (<= 0.65 rad/s^2)
    # next_omega_z = 0.0 + 0.625 * 0.1 = +0.0625 rad/s (<= 0.08 rad/s)
    tau_max_z = np.array([0.0, 0.0, 0.05], dtype=np.float64)
    omega_rest = np.array([0.0, 0.0, 0.0], dtype=np.float64)

    passed, breaches, alpha, next_omega = gate.validate(tau_max_z, omega_rest)
    assert passed, f"Maximum legal torque on z-axis from rest must pass Tier 2 gate, got breaches: {breaches}"
    assert alpha[2] == pytest.approx(0.625, abs=1e-5)
    assert next_omega[2] == pytest.approx(0.0625, abs=1e-5)
