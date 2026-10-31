"""RadZero Core Types and Enumerations.

System states, invariant breaches, telemetry packet schemas, and kinematic vehicle constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import numpy as np


class SystemState(str, Enum):
    """RadZero runtime execution states."""
    NOMINAL = "NOMINAL"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    SAFE_HOLD = "SAFE_HOLD"


class BitfieldTarget(str, Enum):
    """IEEE-754 FP32 bitfield targets for SEU mutation."""
    SIGN = "SIGN"                       # Bit 31: polarity reversal
    EXPONENT_EXPLODE = "EXPONENT_EXPLODE" # Bits 30-23 (0 -> 1): dynamic range explosion
    EXPONENT_COLLAPSE = "EXPONENT_COLLAPSE" # Bits 30-23 (1 -> 0): subnormal/zero regime
    MANTISSA = "MANTISSA"               # Bits 22-0: precision shift


class BreachType(str, Enum):
    """Multi-tier invariant and dynamic breach categories."""
    TIER1_NAN = "TIER1_NAN"
    TIER1_INF = "TIER1_INF"
    TIER1_CHEBYSHEV = "TIER1_CHEBYSHEV"
    TIER2_TORQUE_SATURATION = "TIER2_TORQUE_SATURATION"
    TIER2_ANGULAR_ACCEL = "TIER2_ANGULAR_ACCEL"
    TIER2_SLEW_RATE = "TIER2_SLEW_RATE"
    TIER3_CRC_MISMATCH = "TIER3_CRC_MISMATCH"
    TIMEOUT_BREACH = "TIMEOUT_BREACH"
    MIRROR_CORRUPTION = "MIRROR_CORRUPTION"
    DMA_EXCEPTION = "DMA_EXCEPTION"


@dataclass
class KinematicLimits:
    """Rigid-body kinematic limits and physical properties for 12U/27U SmallSat / CubeSat ADCS."""
    tau_max: float = 0.05              # N*m per axis (FR-3: ||tau_cmd||_inf <= 0.05)
    alpha_max: float = 0.65            # rad/s^2 (FR-3: ||alpha||_2 <= 0.65, accommodates I_z = 0.08 kg*m^2 at tau_max = 0.05 N*m)
    omega_max: float = 0.05            # rad/s (FR-3: ||omega_{k+1}||_2 <= 0.05)
    delta_t: float = 0.1               # 100 ms control timestep (FR-3: Delta t = 100 ms)
    h_max: float = 0.1                 # N*m*s reaction-wheel momentum storage limit
    kd_safe: float = 0.08              # Rate-damping proportional gain (tau = -Kd * omega)
    control_deadline_ms: float = 100.0 # Control frame deadline (FR-5)
    
    # 3x3 Spacecraft Moment of Inertia Tensor (kg*m^2)
    # Default: Diagonal principal moments for 12U/27U SmallSat matched to tau_max=0.05 and alpha_max=0.65
    inertia_matrix: np.ndarray = field(
        default_factory=lambda: np.diag([0.10, 0.10, 0.08]).astype(np.float64)
    )

    def __post_init__(self):
        if not isinstance(self.inertia_matrix, np.ndarray):
            self.inertia_matrix = np.array(self.inertia_matrix, dtype=np.float64)
        self.inv_inertia = np.linalg.inv(self.inertia_matrix)


@dataclass
class InvariantBreach:
    """Detailed record of an invariant breach."""
    tier: int
    breach_type: BreachType
    message: str
    layer_name: Optional[str] = None
    observed_value: Optional[float] = None
    threshold_value: Optional[float] = None
    timestamp_ns: int = 0


@dataclass
class TelemetryPacket:
    """Telemetry packet broadcast at 30 Hz to mission control."""
    timestamp_ns: int
    state: SystemState
    quaternion: List[float]            # [q_w, q_x, q_y, q_z]
    angular_velocity: List[float]      # [omega_x, omega_y, omega_z] (rad/s)
    torque_cmd: List[float]            # [tau_x, tau_y, tau_z] (N*m)
    angular_accel: List[float]         # [alpha_x, alpha_y, alpha_z] (rad/s^2)
    next_omega: List[float]            # [omega_k+1_x, y, z] (rad/s)
    tier1_passed: bool
    tier2_passed: bool
    tier3_passed: bool
    last_breach: Optional[str] = None
    recovery_latency_system_ms: float = 0.0
    recovery_latency_device_ms: float = 0.0
    recovery_count: int = 0
    safe_hold_active: bool = False
    momentum_storage: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    block_crcs: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert telemetry to serializable JSON dictionary."""
        return {
            "timestamp_ns": self.timestamp_ns,
            "state": self.state.value,
            "quaternion": [float(x) for x in self.quaternion],
            "angular_velocity": [float(x) for x in self.angular_velocity],
            "torque_cmd": [float(x) for x in self.torque_cmd],
            "angular_accel": [float(x) for x in self.angular_accel],
            "next_omega": [float(x) for x in self.next_omega],
            "tier1_passed": self.tier1_passed,
            "tier2_passed": self.tier2_passed,
            "tier3_passed": self.tier3_passed,
            "last_breach": self.last_breach,
            "recovery_latency_system_ms": float(self.recovery_latency_system_ms),
            "recovery_latency_device_ms": float(self.recovery_latency_device_ms),
            "recovery_count": int(self.recovery_count),
            "safe_hold_active": self.safe_hold_active,
            "momentum_storage": [float(x) for x in self.momentum_storage],
            "block_crcs": self.block_crcs,
        }
