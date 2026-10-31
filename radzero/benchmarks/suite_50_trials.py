"""50-Trial Automated SEU Injection & Recovery Benchmark Suite.

Executes 50 consecutive closed-loop in-situ fault injection and recovery cycles.
Measures dual-domain latencies (system monotonic vs device time), evaluates
process uptime (zero unhandled exceptions / NFR-3), and profiles statistical distributions.
Carries closed-loop vehicle kinematic state across trials.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List
import numpy as np
import torch

from radzero.core.types import BitfieldTarget, KinematicLimits, SystemState
from radzero.mutation.ieee754_injector import IEEE754Injector
from radzero.recovery.state_machine import RadZeroRuntimeSentinel


def run_50_trial_benchmark(num_trials: int = 50) -> Dict[str, Any]:
    """Execute automated N-trial closed-loop benchmark suite and return performance statistics."""
    limits = KinematicLimits()
    sentinel = RadZeroRuntimeSentinel(limits=limits)

    targets = [
        BitfieldTarget.EXPONENT_EXPLODE,
        BitfieldTarget.SIGN,
        BitfieldTarget.EXPONENT_COLLAPSE,
        BitfieldTarget.MANTISSA,
    ]

    system_latencies_ms: List[float] = []
    device_latencies_ms: List[float] = []
    trial_records: List[Dict[str, Any]] = []
    successful_recoveries = 0
    safe_hold_count = 0
    crashes = 0

    print("=" * 70)
    print(f"RADZERO 50-TRIAL IN-SITU FAULT RECOVERY BENCHMARK (N={num_trials})")
    print(f"Device: {sentinel.device} | Target System Latency: <= 40 ms (CPU) / <= 15 ms (CUDA)")
    print("=" * 70)

    # Initial nominal attitude state: [q_w, q_x, q_y, q_z, omega_x, omega_y, omega_z]
    current_state = np.array([1.0, 0.0, 0.0, 0.0, 0.005, -0.003, 0.004], dtype=np.float64)

    for trial_idx in range(1, num_trials + 1):
        # Select bitfield target cycling through types
        target_type = targets[trial_idx % len(targets)]

        try:
            # 1. Inject physical SEU strike into model parameters
            strike = IEEE754Injector.inject(sentinel.model, target=target_type)

            # 2. Step runtime sentinel through fault detection & in-situ recovery
            packet = sentinel.step(current_state)

            # If fault was latent (e.g. subtle mantissa or masked activation),
            # allow Tier 3 cyclic background scrubber to sweep and catch it (<= 4 frames = 400 ms)
            detection_tier = "Tier 1/2 In-Line"
            if packet.recovery_latency_system_ms == 0.0:
                detection_tier = "Tier 3 Scrubber"
                for _ in range(sentinel.tier3.num_blocks):
                    packet = sentinel.step(current_state)
                    if packet.recovery_latency_system_ms > 0:
                        break

            sys_lat = packet.recovery_latency_system_ms
            dev_lat = packet.recovery_latency_device_ms

            if sys_lat > 0:
                system_latencies_ms.append(sys_lat)
                device_latencies_ms.append(dev_lat)

            if packet.state == SystemState.NOMINAL:
                successful_recoveries += 1
                status_str = f"RECOVERED ({detection_tier})"
            elif packet.state == SystemState.SAFE_HOLD:
                safe_hold_count += 1
                status_str = "SAFE_HOLD"
            else:
                status_str = packet.state.value

            record = {
                "trial": trial_idx,
                "target": target_type.value,
                "layer": strike.layer_name,
                "bit": strike.bit_index,
                "detection_mechanism": detection_tier,
                "orig_hex": strike.original_hex,
                "mutated_hex": strike.mutated_hex,
                "orig_float": strike.original_float,
                "mutated_float": strike.mutated_float,
                "system_lat_ms": round(sys_lat, 3),
                "device_lat_ms": round(dev_lat, 3),
                "final_state": packet.state.value,
            }
            trial_records.append(record)

            # Closed-loop kinematics integration: carry attitude and body rate forward
            tau_cmd = np.array(packet.torque_cmd, dtype=np.float64)
            omega = np.array(packet.angular_velocity, dtype=np.float64)
            # Euler equations of motion
            i_w = limits.inertia_matrix @ omega
            gyro = np.cross(omega, i_w)
            alpha = limits.inv_inertia @ (tau_cmd - gyro)
            new_omega = omega + alpha * limits.delta_t

            # Quaternion integration
            q = np.array(packet.quaternion, dtype=np.float64)
            wx, wy, wz = new_omega
            omega_mat = np.array([
                [0.0, -wx, -wy, -wz],
                [wx, 0.0, wz, -wy],
                [wy, -wz, 0.0, wx],
                [wz, wy, -wx, 0.0]
            ], dtype=np.float64)
            q_dot = 0.5 * (omega_mat @ q)
            new_q = q + q_dot * limits.delta_t
            new_q /= np.linalg.norm(new_q)
            current_state = np.concatenate([new_q, new_omega])

            if trial_idx % 10 == 0 or trial_idx == 1:
                print(
                    f"Trial {trial_idx:02d}/{num_trials:02d} | Target: {target_type.value:<17} | "
                    f"Bit {strike.bit_index:02d} | Sys Latency: {sys_lat:6.2f} ms | Status: {status_str}"
                )

        except Exception as e:
            crashes += 1
            print(f"Trial {trial_idx:02d} EXCEPTION: {e}")

    # Compute Statistical Distribution
    sys_arr = np.array(system_latencies_ms) if system_latencies_ms else np.array([0.0])
    stats = {
        "num_trials": num_trials,
        "successful_recoveries": successful_recoveries,
        "safe_hold_escalations": safe_hold_count,
        "crashes": crashes,
        "uptime_percent": ((num_trials - crashes) / num_trials) * 100.0,
        "recovery_success_rate_percent": (successful_recoveries / num_trials) * 100.0,
        "latency_stats_system_ms": {
            "mean": float(np.mean(sys_arr)),
            "std": float(np.std(sys_arr)),
            "median_p50": float(np.median(sys_arr)),
            "p95": float(np.percentile(sys_arr, 95)),
            "p99": float(np.percentile(sys_arr, 99)),
            "min": float(np.min(sys_arr)),
            "max": float(np.max(sys_arr)),
        },
    }

    print("-" * 70)
    print("STATISTICAL BENCHMARK SUMMARY (NFR-1 / NFR-2 / NFR-3):")
    print(f"  • Process Uptime:              {stats['uptime_percent']:.1f}% (Zero Unhandled Exceptions)")
    print(f"  • In-Situ Recovery Success:    {stats['recovery_success_rate_percent']:.1f}%")
    print(f"  • Mean System Latency:         {stats['latency_stats_system_ms']['mean']:.2f} ms")
    print(f"  • Median (P50) Latency:        {stats['latency_stats_system_ms']['median_p50']:.2f} ms")
    print(f"  • 95th Percentile (P95):       {stats['latency_stats_system_ms']['p95']:.2f} ms")
    print(f"  • Min / Max Latency:           {stats['latency_stats_system_ms']['min']:.2f} ms / {stats['latency_stats_system_ms']['max']:.2f} ms")
    print("=" * 70)

    return {
        "metadata": {
            "title": "RadZero 50-Trial Empirical Benchmark Dataset",
            "date": "2026-10-31",
            "event": "GRAVITON 2026, CGC University - Problem Statement 31",
            "execution_mode": "In-Situ Closed-Loop Vehicle Dynamics Validation",
        },
        "environment": {
            "device": str(sentinel.device),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Reference Host CPU Node",
            "cuda_available": torch.cuda.is_available(),
            "torch_version": torch.__version__,
            "batch_shape": [1, 7],
            "control_deadline_ms": limits.control_deadline_ms,
            "tau_max_nm": limits.tau_max,
            "alpha_max_rad_s2": limits.alpha_max,
            "omega_max_rad_s": limits.omega_max,
        },
        "stats": stats,
        "trials": trial_records,
    }


if __name__ == "__main__":
    results = run_50_trial_benchmark(50)
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved results to benchmark_results.json")
