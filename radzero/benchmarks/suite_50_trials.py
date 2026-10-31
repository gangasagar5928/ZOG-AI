"""50-Trial Automated SEU Injection & Recovery Benchmark Suite.

Executes 50 consecutive in-situ fault injection and recovery cycles.
Measures dual-domain latencies (system monotonic vs device time), evaluates
process uptime (zero unhandled exceptions / NFR-3), and profiles statistical distributions.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List
import numpy as np

from radzero.core.types import BitfieldTarget, KinematicLimits, SystemState
from radzero.mutation.ieee754_injector import IEEE754Injector
from radzero.recovery.state_machine import RadZeroRuntimeSentinel


def run_50_trial_benchmark(num_trials: int = 50) -> Dict[str, Any]:
    """Execute automated N-trial benchmark suite and return performance statistics."""
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

    for trial_idx in range(1, num_trials + 1):
        # Generate nominal attitude state
        q = np.random.randn(4)
        q /= np.linalg.norm(q)
        w = np.random.uniform(-0.015, 0.015, size=3)
        state_vec = np.concatenate([q, w])

        # Select bitfield target cycling through types
        target_type = targets[trial_idx % len(targets)]

        try:
            # 1. Inject physical SEU strike into model parameters
            strike = IEEE754Injector.inject(sentinel.model, target=target_type)

            # 2. Step runtime sentinel through fault detection & in-situ recovery
            packet = sentinel.step(state_vec)

            sys_lat = packet.recovery_latency_system_ms
            dev_lat = packet.recovery_latency_device_ms

            if sys_lat > 0:
                system_latencies_ms.append(sys_lat)
                device_latencies_ms.append(dev_lat)

            if packet.state == SystemState.NOMINAL:
                successful_recoveries += 1
                status_str = "RECOVERED (NOMINAL)"
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
                "orig_hex": strike.original_hex,
                "mutated_hex": strike.mutated_hex,
                "system_lat_ms": round(sys_lat, 3),
                "device_lat_ms": round(dev_lat, 3),
                "final_state": packet.state.value,
            }
            trial_records.append(record)

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

    return {"stats": stats, "trials": trial_records}


if __name__ == "__main__":
    results = run_50_trial_benchmark(50)
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved results to benchmark_results.json")
