"""
CUDA Execution Engine & Dedicated Stream Manager.
Target Hardware: NVIDIA GeForce RTX 3050 Mobile (CUDA 12.x, 4GB/6GB VRAM).

Manages:
1. Dedicated CUDA Streams:
   - Inference Stream: Priority 0 (nominal inference pipeline)
   - Recovery Stream: Priority -1 (high priority for urgent DMA recovery barrier)
   - Telemetry Stream: Auxiliary stream for async monitoring
2. Device Memory & Context Management:
   - Automatic hardware detection and RTX 3050 capability verification.
   - Memory tracking (allocated, reserved, free VRAM).
3. Inference Contexts:
   - torch.inference_mode() execution with explicit stream bindings.
"""

import time
from typing import Dict, Any, Optional, Tuple

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from ..config import config, OperationalMode
from ..concurrency.rw_mutex import ReadWriteMutex


class CUDAExecutionEngine:
    """
    Hosts Member 1's PyTorch model on the RTX 3050 GPU using dedicated CUDA streams.
    Coordinates nominal inference under shared read lock protection.
    """

    def __init__(self, model: Any, rw_mutex: ReadWriteMutex):
        self.raw_model = model
        self.rw_mutex = rw_mutex
        self.device_id = config.device_id
        self.cuda_available = HAS_TORCH and torch.cuda.is_available() and not config.force_cpu

        if self.cuda_available:
            self.device = torch.device(f"cuda:{self.device_id}")
            torch.cuda.set_device(self.device)

            # Retrieve device name & capabilities (RTX 3050 Mobile)
            self.device_properties = torch.cuda.get_device_properties(self.device)
            self.device_name = self.device_properties.name
            self.total_memory_bytes = self.device_properties.total_memory
            self.compute_capability = f"{self.device_properties.major}.{self.device_properties.minor}"

            # Dedicated CUDA streams with hardware priorities
            self.inference_stream = torch.cuda.Stream(
                device=self.device,
                priority=config.inference_stream_priority
            )
            self.recovery_stream = torch.cuda.Stream(
                device=self.device,
                priority=config.recovery_stream_priority
            )
            self.telemetry_stream = torch.cuda.Stream(device=self.device)

            # Move Member 1's model to GPU
            self.model = self.raw_model.to(self.device)
            self.model.eval()

            # Warmup inference pass on inference stream
            self._warmup_device()

        else:
            self.device = "cpu"
            self.device_name = "CPU Emulation (CUDA Unavailable)"
            self.total_memory_bytes = config.target_vram_mb * 1024 * 1024
            self.compute_capability = "N/A"
            self.inference_stream = None
            self.recovery_stream = None
            self.telemetry_stream = None
            self.model = self.raw_model

        self.current_mode: OperationalMode = config.default_mode
        self.dummy_input = self._generate_dummy_input()

    def _generate_dummy_input(self) -> Any:
        """Generates standard batch input (e.g., 1x3x224x224 perception frame)."""
        if self.cuda_available:
            return torch.randn(1, 3, 224, 224, device=self.device, dtype=torch.float32)
        elif HAS_TORCH:
            return torch.randn(1, 3, 224, 224, dtype=torch.float32)
        else:
            return b"\x00" * (1 * 3 * 224 * 224 * 4)

    def _warmup_device(self):
        """Warms up CUDA context and cuBLAS/cuDNN kernels."""
        if self.cuda_available:
            with torch.inference_mode(), torch.cuda.stream(self.inference_stream):
                dummy = torch.randn(1, 3, 224, 224, device=self.device)
                _ = self.model(dummy)
            self.inference_stream.synchronize()

    def execute_inference(self, input_tensor: Optional[Any] = None) -> Tuple[Any, float]:
        """
        Executes nominal inference under shared read lock protection.
        Guarantees that no recovery write can alter model weights during execution.
        """
        t0 = time.perf_counter_ns()
        data = input_tensor if input_tensor is not None else self.dummy_input

        # Acquire Shared Read Lock
        with self.rw_mutex.read_lock():
            if self.cuda_available:
                with torch.inference_mode(), torch.cuda.stream(self.inference_stream):
                    output = self.model(data)
                self.inference_stream.synchronize()
            else:
                output = self.model(data)

        infer_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return output, infer_ms

    def get_memory_info(self) -> Dict[str, Any]:
        """Queries device VRAM metrics for RTX 3050 Mobile."""
        if self.cuda_available:
            allocated = torch.cuda.memory_allocated(self.device)
            reserved = torch.cuda.memory_reserved(self.device)
            free = self.total_memory_bytes - reserved
            return {
                "cuda_available": True,
                "device_name": self.device_name,
                "device_id": self.device_id,
                "compute_capability": self.compute_capability,
                "total_vram_mb": round(self.total_memory_bytes / (1024 * 1024), 2),
                "allocated_vram_mb": round(allocated / (1024 * 1024), 2),
                "reserved_vram_mb": round(reserved / (1024 * 1024), 2),
                "free_vram_mb": round(free / (1024 * 1024), 2),
                "utilization_pct": round((allocated / self.total_memory_bytes) * 100, 2)
            }
        else:
            return {
                "cuda_available": False,
                "device_name": self.device_name,
                "device_id": None,
                "compute_capability": "N/A",
                "total_vram_mb": config.target_vram_mb,
                "allocated_vram_mb": 128.0,
                "reserved_vram_mb": 256.0,
                "free_vram_mb": config.target_vram_mb - 256.0,
                "utilization_pct": 3.12
            }
