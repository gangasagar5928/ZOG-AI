"""
Configuration settings for Aaditya's Accelerator Runtime & Systems Integration Node.
Target Hardware: NVIDIA GeForce RTX 3050 Mobile (CUDA 12.x, 4GB/6GB VRAM).
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OperationalMode(str, Enum):
    NOMINAL = "NOMINAL"
    BENCHMARK = "BENCHMARK"
    FAULT_TEST = "FAULT_TEST"
    DEGRADED = "DEGRADED"
    RECOVERY_ONLY = "RECOVERY_ONLY"
    SAFE_HOLD = "SAFE_HOLD"


class FaultType(str, Enum):
    BIT_FLIP = "bit_flip"
    NAN_INJECTION = "nan"
    ZERO_WEIGHTS = "zero"
    GAUSSIAN_NOISE = "noise"
    STUCK_AT_VALUE = "stuck_at_val"


@dataclass
class RuntimeConfig:
    # Server network binding (Accessible across LAN, e.g. Prachi's workstation)
    host: str = os.getenv("RUNTIME_HOST", "0.0.0.0")
    port: int = int(os.getenv("RUNTIME_PORT", "8000"))

    # CUDA device configuration
    device_id: int = int(os.getenv("CUDA_DEVICE_ID", "0"))
    device_name: str = "NVIDIA GeForce RTX 3050 Mobile"
    target_vram_mb: int = 4096  # 4 GB VRAM standard on RTX 3050 Mobile
    force_cpu: bool = os.getenv("FORCE_CPU", "0") == "1"

    # Concurrency and Streams
    enable_stream_priorities: bool = True
    inference_stream_priority: int = 0
    recovery_stream_priority: int = -1  # Negative priority indicates higher priority in PyTorch CUDA

    # Memory and Shadow Mirroring
    pin_host_memory: bool = True  # Host-pinned memory for zero-copy/DMA transfers
    non_blocking_dma: bool = True  # Asynchronous DMA transfers over PCIe

    # Profiling & Telemetry
    telemetry_broadcast_hz: float = 30.0  # 30 Hz WebSocket broadcast
    telemetry_interval_sec: float = 1.0 / 30.0  # ~0.0333s
    enable_dual_domain_timing: bool = True
    re_inference_validation: bool = True

    # Initial Operational Mode
    default_mode: OperationalMode = OperationalMode.NOMINAL


config = RuntimeConfig()
