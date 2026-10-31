"""Classical Safe-Hold Controller (Proportional Rate-Damping Sentinel).

Implements hard-coded, zero-dependence rate damping:
    tau_safe = -Kd * omega
Enforces reaction-wheel torque saturation (||tau_cmd||_inf <= tau_max)
and monitors angular momentum accumulation against reaction-wheel storage limits (h_max).
"""

from __future__ import annotations

from typing import Tuple
import numpy as np
from radzero.core.types import KinematicLimits


class SafeHoldController:
    """Rigid-body proportional rate-damping controller for contingency detumbling."""

    def __init__(self, limits: KinematicLimits | None = None) -> None:
        self.limits = limits or KinematicLimits()
        self.momentum_storage = np.zeros(3, dtype=np.float64)
        self.saturation_count: int = 0
        self.momentum_saturated: bool = False
        self.desaturation_requested: bool = False

    def compute_torque(self, omega: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Compute safe-hold rate damping torque.

        Args:
            omega: Body angular velocity vector [omega_x, omega_y, omega_z] in rad/s.
        Returns:
            Tuple of (tau_safe [N*m], momentum_saturated [bool]).
        """
        omega = np.asarray(omega, dtype=np.float64)
        
        # Proportional rate damping: tau_unclamped = -Kd * omega
        tau_unclamped = -self.limits.kd_safe * omega

        # Actuator torque saturation: ||tau_cmd||_inf <= tau_max
        tau_safe = np.clip(tau_unclamped, -self.limits.tau_max, self.limits.tau_max)

        # Track reaction-wheel momentum storage: h_RW = integral(tau * dt)
        delta_h = tau_safe * self.limits.delta_t
        self.momentum_storage += delta_h

        # Verify reaction-wheel momentum storage capacity: ||h||_2 <= h_max
        h_norm = float(np.linalg.norm(self.momentum_storage))
        self.desaturation_requested = (h_norm >= self.limits.h_desat_threshold)
        if h_norm >= self.limits.h_max:
            self.momentum_saturated = True
            self.saturation_count += 1
            # Clamp reaction wheel momentum at physical saturation limit
            self.momentum_storage = (self.momentum_storage / h_norm) * self.limits.h_max
            # Zero commanded torque to prevent mechanical overspin into saturated wheels
            tau_safe = np.zeros(3, dtype=np.float64)
            # Engage magnetic torquer (MTQ) momentum desaturation law (unloads momentum to geomagnetic B-field)
            self.desaturate_momentum(dump_ratio=0.10)
        else:
            self.momentum_saturated = False

        return tau_safe, self.momentum_saturated

    def desaturate_momentum(self, dump_ratio: float = 0.10) -> None:
        """Magnetic torquer (MTQ) cross-product momentum dumping law."""
        self.momentum_storage *= max(0.0, 1.0 - dump_ratio)
        h_norm = float(np.linalg.norm(self.momentum_storage))
        if h_norm < self.limits.h_desat_threshold:
            self.desaturation_requested = False
        if h_norm < 0.90 * self.limits.h_max:
            self.momentum_saturated = False

    def reset_momentum(self) -> None:
        """Reset reaction wheel accumulated momentum."""
        self.momentum_storage.fill(0.0)
        self.momentum_saturated = False
        self.desaturation_requested = False
        self.saturation_count = 0
