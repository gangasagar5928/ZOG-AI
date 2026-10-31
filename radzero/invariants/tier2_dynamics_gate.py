"""Tier 2: Rigid-Body Dynamic & Actuator Gate.

Evaluates commanded reaction-wheel torques against spacecraft physical dynamics:
  1. Actuator torque saturation: ||tau_cmd||_inf <= tau_max (0.05 N*m)
  2. Dynamic angular acceleration: ||alpha||_2 <= alpha_max (0.65 rad/s^2)
     where alpha = I^-1 * [ tau_cmd - omega x (I * omega) ]
  3. Slew-rate integration: ||omega_{k+1}||_2 <= omega_max (0.08 rad/s)
     where omega_{k+1} = omega_k + alpha * Delta_t (Delta_t = 100 ms)
"""

from __future__ import annotations

import time
from typing import List, Tuple
import numpy as np

from radzero.core.types import BreachType, InvariantBreach, KinematicLimits


class Tier2DynamicsGate:
    """Rigid-body kinematic validator preventing unphysical spacecraft actuations."""

    def __init__(self, limits: KinematicLimits | None = None) -> None:
        self.limits = limits or KinematicLimits()
        self.momentum_storage = np.zeros(3, dtype=np.float64)
        self.desaturation_requested: bool = False

    def validate(
        self,
        tau_cmd: np.ndarray | List[float],
        omega: np.ndarray | List[float],
    ) -> Tuple[bool, List[InvariantBreach], np.ndarray, np.ndarray]:
        """Validate commanded torque against rigid-body dynamics constraints.

        Args:
            tau_cmd: Commanded torque vector [tau_x, tau_y, tau_z] in N*m.
            omega: Current body angular velocity [omega_x, omega_y, omega_z] in rad/s.

        Returns:
            Tuple of:
              - passed: bool
              - breaches: List[InvariantBreach]
              - alpha: angular acceleration vector [rad/s^2]
              - next_omega: integrated angular velocity [rad/s]
        """
        tau = np.asarray(tau_cmd, dtype=np.float64).flatten()
        w = np.asarray(omega, dtype=np.float64).flatten()
        breaches: List[InvariantBreach] = []
        now_ns = time.perf_counter_ns()

        # 1. Per-axis torque saturation check: ||tau_cmd||_inf <= tau_max
        max_abs_tau = float(np.max(np.abs(tau)))
        if max_abs_tau > self.limits.tau_max:
            breaches.append(
                InvariantBreach(
                    tier=2,
                    breach_type=BreachType.TIER2_TORQUE_SATURATION,
                    message=(
                        f"Torque saturation breach: ||tau||_inf = {max_abs_tau:.5f} N*m "
                        f"> limit {self.limits.tau_max:.5f} N*m"
                    ),
                    observed_value=max_abs_tau,
                    threshold_value=self.limits.tau_max,
                    timestamp_ns=now_ns,
                )
            )

        # 2. Dynamic angular acceleration calculation:
        #    alpha = I^-1 * [ tau_cmd - omega x (I * omega) ]
        #    Gyroscopic torque: tau_gyro = omega x (I * omega)
        i_omega = self.limits.inertia_matrix @ w
        tau_gyro = np.cross(w, i_omega)
        net_torque = tau - tau_gyro
        alpha = self.limits.inv_inertia @ net_torque

        alpha_norm = float(np.linalg.norm(alpha))
        if alpha_norm > self.limits.alpha_max:
            breaches.append(
                InvariantBreach(
                    tier=2,
                    breach_type=BreachType.TIER2_ANGULAR_ACCEL,
                    message=(
                        f"Angular acceleration breach: ||alpha||_2 = {alpha_norm:.5f} rad/s^2 "
                        f"> limit {self.limits.alpha_max:.5f} rad/s^2"
                    ),
                    observed_value=alpha_norm,
                    threshold_value=self.limits.alpha_max,
                    timestamp_ns=now_ns,
                )
            )

        # 3. Integrated slew-rate bounds check:
        #    omega_{k+1} = omega_k + alpha * Delta_t (Delta_t = 100 ms)
        next_omega = w + alpha * self.limits.delta_t
        next_omega_norm = float(np.linalg.norm(next_omega))
        if next_omega_norm > self.limits.omega_max:
            breaches.append(
                InvariantBreach(
                    tier=2,
                    breach_type=BreachType.TIER2_SLEW_RATE,
                    message=(
                        f"Integrated slew-rate breach: ||omega_{{k+1}}||_2 = {next_omega_norm:.5f} rad/s "
                        f"> limit {self.limits.omega_max:.5f} rad/s"
                    ),
                    observed_value=next_omega_norm,
                    threshold_value=self.limits.omega_max,
                    timestamp_ns=now_ns,
                )
            )

        # 4. Predictive Reaction-Wheel Momentum Budgeter:
        #    h_{k+1} = h_k + tau_cmd * Delta_t
        #    Signals desaturation when projected momentum >= 80% of h_max
        projected_h = self.momentum_storage + tau * self.limits.delta_t
        projected_h_norm = float(np.linalg.norm(projected_h))
        if projected_h_norm >= self.limits.h_desat_threshold:
            self.desaturation_requested = True

        if projected_h_norm > self.limits.h_max:
            breaches.append(
                InvariantBreach(
                    tier=2,
                    breach_type=BreachType.TIER2_MOMENTUM_SATURATION,
                    message=(
                        f"Wheel momentum capacity breach: projected ||h||_2 = {projected_h_norm:.5f} N*m*s "
                        f"> limit {self.limits.h_max:.5f} N*m*s"
                    ),
                    observed_value=projected_h_norm,
                    threshold_value=self.limits.h_max,
                    timestamp_ns=now_ns,
                )
            )

        passed = (len(breaches) == 0)
        return passed, breaches, alpha, next_omega

    def update_momentum(self, tau_dispatched: np.ndarray | List[float]) -> bool:
        """Accumulate dispatched torque into running reaction-wheel momentum storage.

        Returns True if desaturation threshold (80% of h_max) is reached.
        """
        tau = np.asarray(tau_dispatched, dtype=np.float64).flatten()
        self.momentum_storage += tau * self.limits.delta_t
        h_norm = float(np.linalg.norm(self.momentum_storage))
        self.desaturation_requested = (h_norm >= self.limits.h_desat_threshold)
        return self.desaturation_requested

    def desaturate_momentum(self, dump_ratio: float = 0.10) -> None:
        """Bleed wheel momentum via external torquers (LEO MTQ m x B or deep-space RCS pulses)."""
        self.momentum_storage *= max(0.0, 1.0 - dump_ratio)
        h_norm = float(np.linalg.norm(self.momentum_storage))
        if h_norm < self.limits.h_desat_threshold:
            self.desaturation_requested = False

    def reset_momentum(self) -> None:
        """Reset reaction-wheel accumulated momentum."""
        self.momentum_storage.fill(0.0)
        self.desaturation_requested = False
