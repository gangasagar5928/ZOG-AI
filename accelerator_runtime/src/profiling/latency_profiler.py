"""
Dual-Domain Latency Profiler.
Instruments device-side execution using paired torch.cuda.Event(enable_timing=True)
and host-side monotonic clocks (time.perf_counter_ns) to measure end-to-end recovery latency.

Dual domains:
1. Device-Domain (CUDA Events): Hardware timers executed on GPU clock cycles.
   - Measures raw PCIe DMA transfer duration (host-pinned buffer -> device VRAM).
   - Measures post-recovery verification re-inference duration on the GPU.
2. Host-Domain (Monotonic Clocks): CPU host-side timeline (time.perf_counter_ns).
   - Measures lock contention, hardware barrier synchronization latency, and end-to-end wall-clock latency.
"""

import time
from typing import Dict, Any, Optional, List
from collections import deque

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class LatencyRecord:
    def __init__(self,
                 operation: str,
                 device_dma_ms: float,
                 device_infer_ms: float,
                 barrier_sync_ms: float,
                 host_end_to_end_ms: float,
                 lock_wait_ms: float,
                 bytes_transferred: int = 0):
        self.operation = operation
        self.device_dma_ms = device_dma_ms
        self.device_infer_ms = device_infer_ms
        self.barrier_sync_ms = barrier_sync_ms
        self.host_end_to_end_ms = host_end_to_end_ms
        self.lock_wait_ms = lock_wait_ms
        self.bytes_transferred = bytes_transferred
        self.timestamp = time.time()

        # Compute throughput in Gigabytes per second (GB/s)
        if device_dma_ms > 0 and bytes_transferred > 0:
            dma_sec = device_dma_ms / 1000.0
            self.throughput_gbps = (bytes_transferred / (1024 ** 3)) / dma_sec
        else:
            self.throughput_gbps = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "device_dma_ms": round(self.device_dma_ms, 4),
            "device_infer_ms": round(self.device_infer_ms, 4),
            "barrier_sync_ms": round(self.barrier_sync_ms, 4),
            "host_end_to_end_ms": round(self.host_end_to_end_ms, 4),
            "lock_wait_ms": round(self.lock_wait_ms, 4),
            "bytes_transferred": self.bytes_transferred,
            "throughput_gbps": round(self.throughput_gbps, 3),
            "timestamp": self.timestamp
        }


class DualDomainLatencyProfiler:
    """
    Instruments GPU recovery and inference operations across both host and device clocks.
    """

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.recovery_records: deque = deque(maxlen=history_size)
        self.inference_records: deque = deque(maxlen=history_size)

        # Pre-allocated CUDA Events for zero-overhead profiling
        self._cuda_available = HAS_TORCH and torch.cuda.is_available()

        if self._cuda_available:
            self.dma_start = torch.cuda.Event(enable_timing=True)
            self.dma_end = torch.cuda.Event(enable_timing=True)
            self.infer_start = torch.cuda.Event(enable_timing=True)
            self.infer_end = torch.cuda.Event(enable_timing=True)
            self.barrier_start = torch.cuda.Event(enable_timing=True)
            self.barrier_end = torch.cuda.Event(enable_timing=True)
        else:
            self.dma_start = None
            self.dma_end = None
            self.infer_start = None
            self.infer_end = None
            self.barrier_start = None
            self.barrier_end = None

        # Cumulative statistics
        self.total_recoveries: int = 0
        self.total_inferences: int = 0
        self.last_recovery_record: Optional[LatencyRecord] = None
        self.last_inference_ms: float = 0.0

    # ---------------- Device-Domain Event Recording ----------------

    def record_dma_start(self, stream=None):
        """Records the launch of PCIe DMA memory transfers on the recovery stream."""
        if self._cuda_available:
            if stream:
                self.dma_start.record(stream)
            else:
                self.dma_start.record()

    def record_dma_end(self, stream=None):
        """Records completion of DMA transfers."""
        if self._cuda_available:
            if stream:
                self.dma_end.record(stream)
            else:
                self.dma_end.record()

    def record_infer_start(self, stream=None):
        """Records start of re-inference kernel execution."""
        if self._cuda_available:
            if stream:
                self.infer_start.record(stream)
            else:
                self.infer_start.record()

    def record_infer_end(self, stream=None):
        """Records end of re-inference kernel execution."""
        if self._cuda_available:
            if stream:
                self.infer_end.record(stream)
            else:
                self.infer_end.record()

    def elapsed_dma_ms(self) -> float:
        """Calculates elapsed GPU hardware time for DMA transfer."""
        if self._cuda_available:
            self.dma_end.synchronize()
            return float(self.dma_start.elapsed_time(self.dma_end))
        return 0.0

    def elapsed_infer_ms(self) -> float:
        """Calculates elapsed GPU hardware time for inference pass."""
        if self._cuda_available:
            self.infer_end.synchronize()
            return float(self.infer_start.elapsed_time(self.infer_end))
        return 0.0

    # ---------------- Record Registration ----------------

    def register_recovery(self,
                          dma_ms: float,
                          infer_ms: float,
                          barrier_ms: float,
                          end_to_end_ns: int,
                          lock_wait_ns: int,
                          bytes_transferred: int) -> LatencyRecord:
        """
        Combines device-side CUDA Event measurements with host monotonic clocks.
        """
        end_to_end_ms = end_to_end_ns / 1_000_000.0
        lock_wait_ms = lock_wait_ns / 1_000_000.0

        record = LatencyRecord(
            operation="RECOVERY_DMA_RESTORE",
            device_dma_ms=dma_ms,
            device_infer_ms=infer_ms,
            barrier_sync_ms=barrier_ms,
            host_end_to_end_ms=end_to_end_ms,
            lock_wait_ms=lock_wait_ms,
            bytes_transferred=bytes_transferred
        )

        self.recovery_records.append(record)
        self.last_recovery_record = record
        self.total_recoveries += 1
        return record

    def register_inference(self, infer_ms: float):
        """Records nominal inference latency."""
        self.inference_records.append(infer_ms)
        self.last_inference_ms = infer_ms
        self.total_inferences += 1

    # ---------------- Aggregation & Telemetry ----------------

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Provides statistical distributions for recovery timings."""
        if not self.recovery_records:
            return {
                "total_recoveries": self.total_recoveries,
                "latest": None,
                "avg_dma_ms": 0.0,
                "avg_end_to_end_ms": 0.0,
                "avg_throughput_gbps": 0.0
            }

        dma_times = [r.device_dma_ms for r in self.recovery_records]
        e2e_times = [r.host_end_to_end_ms for r in self.recovery_records]
        throughputs = [r.throughput_gbps for r in self.recovery_records]

        return {
            "total_recoveries": self.total_recoveries,
            "latest": self.last_recovery_record.to_dict() if self.last_recovery_record else None,
            "avg_dma_ms": round(sum(dma_times) / len(dma_times), 4),
            "avg_end_to_end_ms": round(sum(e2e_times) / len(e2e_times), 4),
            "min_dma_ms": round(min(dma_times), 4),
            "max_dma_ms": round(max(dma_times), 4),
            "avg_throughput_gbps": round(sum(throughputs) / len(throughputs), 3)
        }

    def get_inference_stats(self) -> Dict[str, Any]:
        """Provides statistical distribution for nominal inference."""
        if not self.inference_records:
            return {
                "total_inferences": self.total_inferences,
                "last_ms": 0.0,
                "avg_ms": 0.0,
                "estimated_fps": 0.0
            }

        avg_ms = sum(self.inference_records) / len(self.inference_records)
        fps = (1000.0 / avg_ms) if avg_ms > 0 else 0.0

        return {
            "total_inferences": self.total_inferences,
            "last_ms": round(self.last_inference_ms, 3),
            "avg_ms": round(avg_ms, 3),
            "estimated_fps": round(fps, 1)
        }
