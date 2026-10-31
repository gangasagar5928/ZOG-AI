"""RadZero: In-Situ Fault-Tolerant Inference Runtime for Embedded Edge AI.

Version: 2.3.0-FROZEN
Deployment Target: Dual-Node COTS Edge Architecture
"""

__version__ = "2.3.0-FROZEN"

from radzero.core.types import (
    SystemState,
    BitfieldTarget,
    BreachType,
    KinematicLimits,
    InvariantBreach,
    TelemetryPacket,
)
from radzero.core.adcs_model import DeterministicADCSModel
from radzero.core.rwlock import ReadWriteLock
from radzero.core.safe_hold import SafeHoldController
from radzero.invariants.tier1_tripwire import Tier1Tripwire
from radzero.invariants.tier2_dynamics_gate import Tier2DynamicsGate
from radzero.invariants.tier3_scrubber import Tier3Scrubber
from radzero.mutation.ieee754_injector import IEEE754Injector, SEUStrikeRecord
from radzero.recovery.checkpoint_mirror import DualCheckpointMirror
from radzero.recovery.state_machine import RadZeroRuntimeSentinel

__all__ = [
    "SystemState",
    "BitfieldTarget",
    "BreachType",
    "KinematicLimits",
    "InvariantBreach",
    "TelemetryPacket",
    "DeterministicADCSModel",
    "ReadWriteLock",
    "SafeHoldController",
    "Tier1Tripwire",
    "Tier2DynamicsGate",
    "Tier3Scrubber",
    "IEEE754Injector",
    "SEUStrikeRecord",
    "DualCheckpointMirror",
    "RadZeroRuntimeSentinel",
]
