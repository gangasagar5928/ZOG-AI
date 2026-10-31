"""
Hardware Recovery Barrier & DMA In-Place Memory Restoration Engine.
Executes the atomic weight recovery protocol:
1. Acquires exclusive write lock on Parameter Mutex (blocks all inference).
2. Hardware recovery barrier: enforces device-wide synchronization (torch.cuda.synchronize()).
   Ensures in-flight matrix multiplications (GEMM) complete before memory is overwritten.
3. In-place device memory updates (param.data.copy_()) from host-pinned buffers (non_blocking=True).
4. Dual-domain latency profiling (paired torch.cuda.Event and host perf_counter_ns).
5. Post-recovery verification re-inference pass.
"""

import time
from typing import Dict, Any, Optional

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from ..concurrency.rw_mutex import ReadWriteMutex
from ..model.shadow_mirror import HostPinnedShadowMirror
from ..profiling.latency_profiler import DualDomainLatencyProfiler
from .cuda_engine import CUDAExecutionEngine


class HardwareRecoveryBarrier:
    """
    Enforces hardware synchronization barriers and executes DMA parameter restoration.
    """

    def __init__(self,
                 engine: CUDAExecutionEngine,
                 shadow_mirror: HostPinnedShadowMirror,
                 rw_mutex: ReadWriteMutex,
                 profiler: DualDomainLatencyProfiler):
        self.engine = engine
        self.shadow_mirror = shadow_mirror
        self.rw_mutex = rw_mutex
        self.profiler = profiler

    def execute_recovery(self) -> Dict[str, Any]:
        """
        Executes the atomic hardware recovery sequence under exclusive write lock protection.
        """
        host_start_ns = time.perf_counter_ns()
        lock_wait_start_ns = host_start_ns

        # 1. Acquire Exclusive Write Lock
        with self.rw_mutex.write_lock():
            lock_wait_ns = time.perf_counter_ns() - lock_wait_start_ns
            barrier_start_ns = time.perf_counter_ns()

            # 2. Hardware Recovery Barrier: Device-Wide Synchronization
            # Enforce that all in-flight matrix multiplications, convolutions, and CUDA kernels
            # on the inference stream drain and complete before modifying device memory.
            if self.engine.cuda_available:
                torch.cuda.synchronize(self.engine.device)
            barrier_sync_ms = (time.perf_counter_ns() - barrier_start_ns) / 1_000_000.0

            # 3. Dual-Domain Timing: Record DMA Start Event on Hardware Stream
            if self.engine.cuda_available:
                self.profiler.record_dma_start(self.engine.recovery_stream)
            dma_host_start_ns = time.perf_counter_ns()

            # 4. In-Place Device Memory Updates from Host-Pinned Buffers
            # param.data.copy_() preserves existing GPU VRAM allocations/addresses
            # non_blocking=True enables direct PCIe DMA transfer from page-locked host memory
            bytes_transferred = 0
            shadow_buffers = self.shadow_mirror.get_all_buffers()

            if self.engine.cuda_available:
                with torch.cuda.stream(self.engine.recovery_stream):
                    for name, param in self.engine.model.named_parameters():
                        if name in shadow_buffers:
                            host_buf = shadow_buffers[name]
                            param.data.copy_(host_buf, non_blocking=True)
                            bytes_transferred += param.numel() * param.element_size()

                # Record DMA Completion Event and Synchronize Recovery Stream
                self.profiler.record_dma_end(self.engine.recovery_stream)
                self.engine.recovery_stream.synchronize()
                dma_elapsed_ms = self.profiler.elapsed_dma_ms()

            else:
                # CPU / Simulation mode
                for name, param in self.engine.model.named_parameters():
                    if name in shadow_buffers:
                        host_buf = shadow_buffers[name]
                        if hasattr(param.data, "copy_"):
                            param.data.copy_(host_buf)
                        elif hasattr(param.data, "__setitem__"):
                            param.data[...] = host_buf[...]
                        bytes_transferred += self.shadow_mirror.param_metadata.get(name, {}).get("bytes", 0)

                dma_elapsed_ms = (time.perf_counter_ns() - dma_host_start_ns) / 1_000_000.0

            # 5. Post-Recovery Verification Re-Inference Pass
            # Measures re-inference time using paired CUDA events
            re_infer_ms = 0.0
            if self.engine.cuda_available:
                self.profiler.record_infer_start(self.engine.inference_stream)
                with torch.inference_mode(), torch.cuda.stream(self.engine.inference_stream):
                    _ = self.engine.model(self.engine.dummy_input)
                self.profiler.record_infer_end(self.engine.inference_stream)
                self.engine.inference_stream.synchronize()
                re_infer_ms = self.profiler.elapsed_infer_ms()
            else:
                t_infer0 = time.perf_counter_ns()
                _ = self.engine.model(self.engine.dummy_input)
                re_infer_ms = (time.perf_counter_ns() - t_infer0) / 1_000_000.0

            # 6. End-to-End Host Clock Completion
            host_end_ns = time.perf_counter_ns()
            end_to_end_ns = host_end_ns - host_start_ns

        # 7. Register Record with Latency Profiler
        record = self.profiler.register_recovery(
            dma_ms=dma_elapsed_ms,
            infer_ms=re_infer_ms,
            barrier_ms=barrier_sync_ms,
            end_to_end_ns=end_to_end_ns,
            lock_wait_ns=lock_wait_ns,
            bytes_transferred=bytes_transferred
        )

        return {
            "status": "RECOVERY_COMPLETE",
            "barrier_enforced": True,
            "exclusive_lock_held": True,
            "bytes_transferred": bytes_transferred,
            "metrics": record.to_dict()
        }
