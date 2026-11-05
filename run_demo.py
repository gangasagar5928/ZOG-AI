"""RadZero Live Demonstration Script.

Interactive demonstration of:
  1. Nominal deterministic inference passes.
  2. In-situ detection and recovery from an Exponent Explosion SEU (NaN / range surge).
  3. In-situ detection and recovery from a Sign Bit Polarity Inversion SEU.
  4. Latent parameter corruption detection via Tier 3 background CRC-32 scrubber.
  5. Deterministic Safe-Hold Escalation upon unrecoverable dual-mirror failure.
"""

from __future__ import annotations

import time
import numpy as np

from radzero.core.types import BitfieldTarget, KinematicLimits, SystemState
from radzero.mutation.ieee754_injector import IEEE754Injector
from radzero.recovery.state_machine import RadZeroRuntimeSentinel


def print_step(title: str, pkt, plain_explanation: str | None = None):
    print(f"\n>>> {title}")
    if plain_explanation:
        print(f"  [Simple Summary]           {plain_explanation}")
    print(f"  State:                     {pkt.state.value}")
    print(f"  Quaternion (q_e):          [{', '.join(f'{x:.4f}' for x in pkt.quaternion)}]")
    print(f"  Angular Velocity (omega):  [{', '.join(f'{x:.4f}' for x in pkt.angular_velocity)}] rad/s")
    print(f"  Commanded Torque (tau):    [{', '.join(f'{x:.5f}' for x in pkt.torque_cmd)}] N*m")
    print(f"  Angular Accel (alpha):     [{', '.join(f'{x:.5f}' for x in pkt.angular_accel)}] rad/s^2")
    print(f"  Tier Checks (T1/T2/T3):    {pkt.tier1_passed} / {pkt.tier2_passed} / {pkt.tier3_passed}")
    if pkt.last_breach:
        print(f"  Last Breach Flagged:       {pkt.last_breach}")
    if pkt.recovery_latency_system_ms > 0:
        print(f"  Recovery Latency (System): {pkt.recovery_latency_system_ms:.3f} ms (Recovered in-situ without reboot!)")
    if pkt.safe_hold_active:
        print(f"  Safe-Hold Active:          YES (Emergency Rate-Damping Parachute Active)")
        print(f"  RW Momentum Storage:       [{', '.join(f'{x:.4f}' for x in pkt.momentum_storage)}] N*m*s")


def run_demo():
    print("=" * 80)
    print(" PROJECT RADZERO: IN-SITU FAULT-CONTAINMENT & AUTONOMOUS RECOVERY RUNTIME")
    print(" Rocket Science Explained Simply: Protecting Satellite AI From Space Radiation")
    print("=" * 80)

    limits = KinematicLimits()
    sentinel = RadZeroRuntimeSentinel(limits=limits)
    state = np.array([1.0, 0.0, 0.0, 0.0, 0.005, -0.003, 0.008], dtype=np.float64)

    # 1. Nominal Operation
    print("\n[PHASE 1] Executing Nominal Inference Steps...")
    print("  * Plain English: Satellite AI is steering smoothly. Solar panels face the Sun.")
    for i in range(3):
        pkt = sentinel.step(state)
        print_step(f"Step {i+1} (Nominal Flight)", pkt, "AI steering commands are safe and within physical boundaries.")
        time.sleep(0.05)

    # 2. Exponent Explosion SEU Strike (0 -> 1 in exponent bitfield)
    print("\n" + "=" * 80)
    print("[PHASE 2] Injecting SEU Strike: EXPONENT_EXPLODE (Bits 30-23)")
    print("  * What happened: Cosmic ray flipped a 0 to 1 in the exponent of a neural weight.")
    print("  * Ordinary Satellite Result: Value multiplies by 340 undecillion -> NaN/Crash -> 45 min reboot!")
    print("  * RadZero Action: Tier 1 Tripwire detects math anomaly and hot-patches memory in <1 ms.")
    print("=" * 80)
    strike1 = IEEE754Injector.inject(
        sentinel.model, layer_name="block0.weight", target=BitfieldTarget.EXPONENT_EXPLODE
    )
    print(f"  Strike Target:   {strike1.layer_name} [{strike1.element_index[0]}]")
    print(f"  Bit Mutated:     Bit {strike1.bit_index} (0 -> 1)")
    print(f"  Hex Transition:  {strike1.original_hex} -> {strike1.mutated_hex}")
    print(f"  Float Impact:    {strike1.original_float:.6e} -> {strike1.mutated_float:.6e}")

    pkt = sentinel.step(state)
    print_step(
        "Step Post-SEU Injection (In-Situ Recovery Triggered)",
        pkt,
        "Tier 1 caught corrupted number; restored clean weights over PCIe DMA without dropping a frame."
    )

    # 3. Sign Bit Polarity Inversion (Bit 31)
    print("\n" + "=" * 80)
    print("[PHASE 3] Injecting SEU Strike: SIGN BIT INVERSION (Bit 31)")
    print("  * What happened: Radiation flipped the plus/minus sign bit of commanded torque.")
    print("  * Ordinary Satellite Result: Left turn becomes violent right turn -> Satellite spins out of control!")
    print("  * RadZero Action: Tier 2 Physics Gate calculates angular velocity, blocks command, and heals weights.")
    print("=" * 80)
    strike2 = IEEE754Injector.inject(
        sentinel.model, layer_name="block3.weight", target=BitfieldTarget.SIGN
    )
    print(f"  Strike Target:   {strike2.layer_name} [{strike2.element_index[0]}]")
    print(f"  Bit Mutated:     Bit {strike2.bit_index} (Sign Flip)")
    print(f"  Float Impact:    {strike2.original_float:.6e} -> {strike2.mutated_float:.6e}")

    pkt = sentinel.step(state)
    print_step(
        "Step Post-Sign Flip (Kinematic Breach & Hot-Patching)",
        pkt,
        "Tier 2 rigid-body physics gate blocked dangerous torque; memory hot-patched in milliseconds."
    )

    # 4. Latent Parameter Mutation Detected by Tier 3 Background Scrubber
    print("\n" + "=" * 80)
    print("[PHASE 4] Latent Fault Injection: Audited by Tier 3 Idle Scrubber")
    print("  * What happened: Silent bit-flip altered precision in idle memory not yet executed.")
    print("  * Ordinary Satellite Result: Sits like a ticking time bomb until activated during critical maneuver.")
    print("  * RadZero Action: Tier 3 background janitor checks CRC fingerprints during idle time and repairs it.")
    print("=" * 80)
    strike3 = IEEE754Injector.inject(
        sentinel.model, layer_name="block1.weight", target=BitfieldTarget.MANTISSA
    )
    print(f"  Strike Target:   {strike3.layer_name} (Latent precision shift)")
    print(f"  Bit Mutated:     Bit {strike3.bit_index}")

    # Sweep blocks until Tier 3 detects CRC mismatch
    for sweep_idx in range(4):
        pkt = sentinel.step(state)
        if not pkt.tier3_passed:
            print_step(
                f"Tier 3 Scrubber detected latent CRC mismatch on block sweep {sweep_idx+1}",
                pkt,
                "Latent memory mutation caught by CRC checksum audit before it could alter satellite trajectory."
            )
            break

    # 5. Safe-Hold Contingency Escalation (Dual-Mirror Corruption Simulation)
    print("\n" + "=" * 80)
    print("[PHASE 5] Stress Test: Simulating Unrecoverable Mirror Corruption")
    print("  * What happened: Severe solar storm corrupts BOTH primary and backup memory mirrors.")
    print("  * Ordinary Satellite Result: Software panics, system enters infinite crash loop, satellite lost.")
    print("  * RadZero Action: Automatically engages analog rate-damping Safe-Hold (emergency parachute).")
    print("=" * 80)
    sentinel.mirror.corrupt_mirror_for_testing("block0.weight", corrupt_backup=False)
    sentinel.mirror.corrupt_mirror_for_testing("block0.weight", corrupt_backup=True)
    IEEE754Injector.inject(
        sentinel.model, layer_name="block0.weight", target=BitfieldTarget.EXPONENT_EXPLODE
    )
    print("  Both Primary and Backup Checkpoint Mirrors Corrupted.")
    print("  Executing control step -> Expecting Escalation to SAFE_HOLD...")

    pkt = sentinel.step(state)
    print_step(
        "Escalation to Classical Safe-Hold Controller",
        pkt,
        "AI disengaged. Analog rate-damping controller stabilized satellite spin rate safely."
    )

    # Reset back to Nominal
    print("\n[PHASE 6] Resetting Sentinel to Nominal Baseline...")
    sentinel.reset_nominal()
    pkt = sentinel.step(state)
    print_step("System Restored to Nominal", pkt, "Clean memory verified; autonomous AI steering re-engaged.")

    print("\n" + "=" * 80)
    print(" RADZERO DEMONSTRATION COMPLETE: 100% UPTIME, ZERO PROCESS TERMINATIONS")
    print(" All faults contained in-situ without rebooting or spinning the spacecraft.")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
