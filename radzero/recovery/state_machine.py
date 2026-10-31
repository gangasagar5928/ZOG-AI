"""RadZero Recovery State Machine & Runtime Sentinel.

Executes closed-loop inference, multi-tier anomaly detection, concurrency-safe
in-situ hot-patching, post-recovery re-verification, and deterministic safe-hold escalation.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple
import numpy as np
import torch

from radzero.core.adcs_model import DeterministicADCSModel, enforce_deterministic_runtime
from radzero.core.rwlock import ReadWriteLock
from radzero.core.safe_hold import SafeHoldController
from radzero.core.types import (
    BreachType,
    InvariantBreach,
    KinematicLimits,
    SystemState,
    TelemetryPacket,
)
from radzero.invariants.tier1_tripwire import Tier1Tripwire
from radzero.invariants.tier2_dynamics_gate import Tier2DynamicsGate
from radzero.invariants.tier3_scrubber import Tier3Scrubber
from radzero.recovery.checkpoint_mirror import DualCheckpointMirror


class RadZeroRuntimeSentinel:
    """Integrated Fault-Tolerant Inference Runtime Sentinel."""

    def __init__(
        self,
        limits: KinematicLimits | None = None,
        device: torch.device | None = None,
        k_chebyshev: float = 4.5,
    ) -> None:
        enforce_deterministic_runtime()

        self.limits = limits or KinematicLimits()
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.state = SystemState.NOMINAL

        # Core subsystems
        self.rwlock = ReadWriteLock()
        self.model = DeterministicADCSModel(max_torque=self.limits.tau_max).to(self.device)
        self.safe_hold = SafeHoldController(limits=self.limits)
        self.mirror = DualCheckpointMirror(self.model)

        # Capture pristine golden baseline weights for full reset
        self._golden_state_dict = {
            k: v.cpu().clone() for k, v in self.model.state_dict().items()
        }

        # Invariant sentinels
        self.tier1 = Tier1Tripwire(k_chebyshev=k_chebyshev)
        self.tier2 = Tier2DynamicsGate(limits=self.limits)
        self.tier3 = Tier3Scrubber(self.model)

        # Calibrate Tier 1 Chebyshev bounds with nominal state space
        self._calibrate_invariants()
        self.tier1.attach(self.model)

        # Metrics and counters
        self.recovery_count: int = 0
        self.last_system_latency_ms: float = 0.0
        self.last_device_latency_ms: float = 0.0
        self.last_breach_msg: Optional[str] = None
        self.active_breaches: List[InvariantBreach] = []

    def _calibrate_invariants(self) -> None:
        """Calibrate Tier 1 bounds using nominal and slewing quaternion/velocity distributions."""
        sample_states = []
        for _ in range(100):
            # Unit quaternion [q_w, q_x, q_y, q_z]
            q = np.random.randn(4)
            q /= np.linalg.norm(q)
            # Angular velocity covering nominal and slewing envelopes up to limits [-0.06, 0.06] rad/s
            w = np.random.uniform(-0.06, 0.06, size=3)
            sample_states.append(np.concatenate([q, w]))

        # Include boundary corner cases (+/- 0.08 rad/s)
        for sign in [-1.0, 1.0]:
            sample_states.append(np.array([1.0, 0.0, 0.0, 0.0, sign * 0.08, 0.0, 0.0]))
            sample_states.append(np.array([1.0, 0.0, 0.0, 0.0, 0.0, sign * 0.08, 0.0]))
            sample_states.append(np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, sign * 0.08]))

        sample_tensor = torch.tensor(
            np.array(sample_states), dtype=torch.float32, device=self.device
        )
        self.tier1.calibrate_bounds(self.model, sample_tensor, num_runs=50)

    def step(self, state_input: np.ndarray | List[float]) -> TelemetryPacket:
        """Execute one complete 100 ms control frame step.

        Args:
            state_input: 7-element array [q_w, q_x, q_y, q_z, omega_x, omega_y, omega_z].

        Returns:
            TelemetryPacket containing complete vehicle and runtime telemetry.
        """
        now_ns = time.perf_counter_ns()
        self.last_system_latency_ms = 0.0
        self.last_device_latency_ms = 0.0
        state_vec = np.asarray(state_input, dtype=np.float64).flatten()
        quaternion = state_vec[:4]
        omega = state_vec[4:7]

        # Convert to PyTorch tensor for model forward pass
        input_tensor = torch.tensor(
            state_vec, dtype=torch.float32, device=self.device
        )

        tau_dispatch: np.ndarray
        alpha_dispatch: np.ndarray
        next_omega_dispatch: np.ndarray
        tier1_passed: bool = True
        tier2_passed: bool = True
        tier3_passed: bool = True

        # If currently in SAFE_HOLD, execute classical rate damping directly
        if self.state == SystemState.SAFE_HOLD:
            tau_safe, _ = self.safe_hold.compute_torque(omega)
            tau_dispatch = tau_safe
            _, _, alpha_dispatch, next_omega_dispatch = self.tier2.validate(tau_dispatch, omega)
            return self._build_telemetry(
                now_ns, quaternion, omega, tau_dispatch, alpha_dispatch,
                next_omega_dispatch, tier1_passed=False, tier2_passed=True,
                tier3_passed=True, safe_hold_active=True
            )

        # -------------------------------------------------------------
        # STEP 1: Acquired Shared Parameter Read Lock & Forward Pass
        # -------------------------------------------------------------
        with self.rwlock.read_lock():
            with torch.inference_mode():
                raw_tau = self.model(input_tensor)

        # -------------------------------------------------------------
        # STEP 2: Tier 1 In-Line Activation Tripwire Evaluation
        # -------------------------------------------------------------
        tier1_passed, tier1_breaches = self.tier1.check_and_clear_breaches()

        # -------------------------------------------------------------
        # STEP 3: Tier 2 Rigid-Body Dynamics Gate Evaluation (if Tier 1 OK)
        # -------------------------------------------------------------
        tau_candidate = raw_tau.detach().cpu().numpy().astype(np.float64)

        if tier1_passed:
            tier2_passed, tier2_breaches, alpha, next_omega = self.tier2.validate(
                tau_candidate, omega
            )
        else:
            tier2_passed = False
            tier2_breaches = []
            alpha = np.zeros(3, dtype=np.float64)
            next_omega = omega.copy()

        # -------------------------------------------------------------
        # NOMINAL PATH
        # -------------------------------------------------------------
        if tier1_passed and tier2_passed:
            self.state = SystemState.NOMINAL
            tau_dispatch = tau_candidate
            alpha_dispatch = alpha
            next_omega_dispatch = next_omega

            # Step 4: Background Slack Time: Tier 3 Scrubber (1 block per 100 ms)
            tier3_passed, tier3_breach, _, _ = self.tier3.audit_next_block()
            if not tier3_passed and tier3_breach is not None:
                self.last_breach_msg = tier3_breach.message
                # Trigger in-situ recovery for latent corrupted block
                rec_ok, tau_rec, alpha_rec, next_w_rec, _, _ = self._execute_in_situ_recovery(
                    omega, input_tensor, initial_breaches=[tier3_breach]
                )
                if rec_ok:
                    self.state = SystemState.NOMINAL
                    tau_dispatch = tau_rec
                    alpha_dispatch = alpha_rec
                    next_omega_dispatch = next_w_rec
                    safe_hold_active = False
                else:
                    self.state = SystemState.SAFE_HOLD
                    tau_safe, _ = self.safe_hold.compute_torque(omega)
                    tau_dispatch = tau_safe
                    _, _, alpha_dispatch, next_omega_dispatch = self.tier2.validate(tau_dispatch, omega)
                    safe_hold_active = True
                return self._build_telemetry(
                    now_ns, quaternion, omega, tau_dispatch, alpha_dispatch,
                    next_omega_dispatch, tier1_passed=rec_ok, tier2_passed=rec_ok,
                    tier3_passed=False, safe_hold_active=safe_hold_active
                )

            return self._build_telemetry(
                now_ns, quaternion, omega, tau_dispatch, alpha_dispatch,
                next_omega_dispatch, tier1_passed, tier2_passed, tier3_passed,
                safe_hold_active=False
            )

        # -------------------------------------------------------------
        # BREACH DETECTED: INITIATE IN-SITU RECOVERY
        # -------------------------------------------------------------
        breaches = tier1_breaches + tier2_breaches
        self.last_breach_msg = breaches[0].message if breaches else "Unknown breach"

        (
            recovery_success,
            tau_recovered,
            alpha_recovered,
            next_omega_recovered,
            system_lat_ms,
            device_lat_ms,
        ) = self._execute_in_situ_recovery(omega, input_tensor, initial_breaches=breaches)

        if recovery_success:
            self.state = SystemState.NOMINAL
            tau_dispatch = tau_recovered
            alpha_dispatch = alpha_recovered
            next_omega_dispatch = next_omega_recovered
            safe_hold_active = False
        else:
            # Safe-Hold Escalation: Engage hard-coded proportional rate damping
            self.state = SystemState.SAFE_HOLD
            tau_safe, _ = self.safe_hold.compute_torque(omega)
            tau_dispatch = tau_safe
            _, _, alpha_dispatch, next_omega_dispatch = self.tier2.validate(tau_dispatch, omega)
            safe_hold_active = True

        return self._build_telemetry(
            now_ns, quaternion, omega, tau_dispatch, alpha_dispatch,
            next_omega_dispatch, tier1_passed=recovery_success,
            tier2_passed=recovery_success, tier3_passed=True,
            safe_hold_active=safe_hold_active
        )

    def _execute_in_situ_recovery(
        self,
        omega: np.ndarray,
        input_tensor: torch.Tensor,
        initial_breaches: List[InvariantBreach],
    ) -> Tuple[bool, np.ndarray, np.ndarray, np.ndarray, float, float]:
        """Execute concurrency-safe in-situ parameter restoration and re-verification.

        Returns:
            Tuple of:
              - success: bool
              - tau: np.ndarray [3]
              - alpha: np.ndarray [3]
              - next_omega: np.ndarray [3]
              - system_latency_ms: float
              - device_latency_ms: float
        """
        self.state = SystemState.RECOVERING
        self.recovery_count += 1

        # Monotonic system clock start (NFR-1)
        start_sys_ns = time.perf_counter_ns()

        # Device timer (torch.cuda.Event if CUDA available)
        use_cuda = torch.cuda.is_available() and self.device.type == "cuda"
        if use_cuda:
            ev_start = torch.cuda.Event(enable_timing=True)
            ev_end = torch.cuda.Event(enable_timing=True)
            ev_start.record()

        # Step A: Parameter Read-Write Mutex (Exclusive Write Lock Acquired)
        with self.rwlock.write_lock():
            # Step B: Device-wide synchronization (drain active accelerator streams)
            if use_cuda:
                torch.cuda.synchronize()

            # Step C: In-situ memory replacement from host mirrors
            hotpatch_ok, _, mirror_breach = self.mirror.hot_patch_all(self.model, self.device)
            if not hotpatch_ok:
                self.last_breach_msg = mirror_breach.message if mirror_breach else "Mirror fault"
                sys_lat = (time.perf_counter_ns() - start_sys_ns) / 1e6
                self.last_system_latency_ms = sys_lat
                return False, np.zeros(3), np.zeros(3), omega, sys_lat, 0.0

            # Drain device streams post-DMA
            if use_cuda:
                torch.cuda.synchronize()

            # Refresh scrubber cached CRCs to match restored state
            self.tier3.refresh_cached_crcs()

        # Step D: Post-Recovery Re-Verification
        with self.rwlock.read_lock():
            with torch.inference_mode():
                re_tau = self.model(input_tensor)

        re_tier1_ok, re_t1_breaches = self.tier1.check_and_clear_breaches()
        tau_recovered = re_tau.detach().cpu().numpy().astype(np.float64)
        re_t2_breaches: List[InvariantBreach] = []

        if re_tier1_ok:
            re_tier2_ok, re_t2_breaches, alpha, next_omega = self.tier2.validate(
                tau_recovered, omega
            )
        else:
            re_tier2_ok = False
            re_t2_breaches = []
            alpha = np.zeros(3, dtype=np.float64)
            next_omega = omega

        # Compute Latencies
        sys_lat_ms = (time.perf_counter_ns() - start_sys_ns) / 1e6
        self.last_system_latency_ms = sys_lat_ms

        if use_cuda:
            ev_end.record()
            torch.cuda.synchronize()
            dev_lat_ms = float(ev_start.elapsed_time(ev_end))
        else:
            dev_lat_ms = sys_lat_ms
        self.last_device_latency_ms = dev_lat_ms

        # Safe-Hold Escalation Conditions:
        # 1. Recovery latency breaches 100 ms deadline
        if sys_lat_ms > self.limits.control_deadline_ms:
            self.last_breach_msg = (
                f"Recovery latency deadline breached: {sys_lat_ms:.2f} ms > {self.limits.control_deadline_ms} ms"
            )
            return False, np.zeros(3), np.zeros(3), omega, sys_lat_ms, dev_lat_ms

        # 2. Re-evaluation fails Tier 1 or Tier 2
        if not (re_tier1_ok and re_tier2_ok):
            fail_breaches = re_t1_breaches + re_t2_breaches
            self.last_breach_msg = fail_breaches[0].message if fail_breaches else "Re-verification failed"
            return False, np.zeros(3), np.zeros(3), omega, sys_lat_ms, dev_lat_ms

        return True, tau_recovered, alpha, next_omega, sys_lat_ms, dev_lat_ms

    def reset_nominal(self) -> None:
        """Reset state from SAFE_HOLD back to NOMINAL, restore clean mirrors and clear momentum."""
        self.safe_hold.reset_momentum()
        self.state = SystemState.NOMINAL
        self.last_breach_msg = None
        # Restore model and mirrors to pristine baseline
        self.model.load_state_dict(self._golden_state_dict)
        self.mirror = DualCheckpointMirror(self.model)
        self.tier3 = Tier3Scrubber(self.model)

    def _build_telemetry(
        self,
        timestamp_ns: int,
        quaternion: np.ndarray,
        omega: np.ndarray,
        tau: np.ndarray,
        alpha: np.ndarray,
        next_omega: np.ndarray,
        tier1_passed: bool,
        tier2_passed: bool,
        tier3_passed: bool,
        safe_hold_active: bool,
    ) -> TelemetryPacket:
        """Assemble telemetry packet with CRC hex list."""
        return TelemetryPacket(
            timestamp_ns=timestamp_ns,
            state=self.state,
            quaternion=quaternion.tolist(),
            angular_velocity=omega.tolist(),
            torque_cmd=tau.tolist(),
            angular_accel=alpha.tolist(),
            next_omega=next_omega.tolist(),
            tier1_passed=tier1_passed,
            tier2_passed=tier2_passed,
            tier3_passed=tier3_passed,
            last_breach=self.last_breach_msg,
            recovery_latency_system_ms=self.last_system_latency_ms,
            recovery_latency_device_ms=self.last_device_latency_ms,
            recovery_count=self.recovery_count,
            safe_hold_active=safe_hold_active,
            momentum_storage=self.safe_hold.momentum_storage.tolist(),
            block_crcs=self.tier3.get_block_crc_hex_list(),
        )
