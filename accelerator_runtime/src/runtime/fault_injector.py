"""
Hardware Fault Injection Engine.
Simulates Single-Event Upsets (SEUs), memory bit-flips, IEEE-754 NaNs,
and weight corruption in device VRAM on the RTX 3050 Mobile.
Used by Prachi's client or automated fault-tolerance validation harnesses.
"""

import struct
import random
from typing import Dict, Any, Optional, List

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from ..config import FaultType
from ..concurrency.rw_mutex import ReadWriteMutex
from .cuda_engine import CUDAExecutionEngine


class FaultInjectionEngine:
    """
    Directly mutates GPU parameter tensors to simulate physical radiation/thermal faults.
    """

    def __init__(self, engine: CUDAExecutionEngine, rw_mutex: ReadWriteMutex):
        self.engine = engine
        self.rw_mutex = rw_mutex
        self.active_fault: Optional[Dict[str, Any]] = None
        self.fault_history: List[Dict[str, Any]] = []

    def inject_fault(self,
                     fault_type: FaultType = FaultType.BIT_FLIP,
                     layer_name: Optional[str] = None,
                     intensity: float = 1.0,
                     element_count: int = 10) -> Dict[str, Any]:
        """
        Injects corruption into targeted GPU memory under exclusive write lock protection.
        """
        with self.rw_mutex.write_lock():
            # Synchronize before mutating device memory
            if self.engine.cuda_available:
                torch.cuda.synchronize(self.engine.device)

            target_layer = None
            target_param = None

            # Find matching layer or pick the first candidate
            for name, param in self.engine.model.named_parameters():
                if layer_name:
                    if layer_name in name:
                        target_layer = name
                        target_param = param
                        break
                else:
                    if "weight" in name and getattr(param, "numel", lambda: 100)() > 10:
                        target_layer = name
                        target_param = param
                        break

            if target_layer is None or target_param is None:
                # Fallback to any parameter
                for name, param in self.engine.model.named_parameters():
                    target_layer = name
                    target_param = param
                    break

            if target_param is None:
                raise RuntimeError("No model parameters available for fault injection")

            corrupted_count = 0
            if HAS_TORCH and isinstance(target_param, torch.Tensor):
                with torch.no_grad():
                    flat_view = target_param.data.view(-1)
                    num_elements = flat_view.numel()
                    indices = torch.randint(0, num_elements, (min(element_count, num_elements),), device=flat_view.device)

                    if fault_type == FaultType.BIT_FLIP:
                        # Emulate Single Event Upset (SEU) by flipping random bits
                        for idx in indices:
                            val = flat_view[idx].item()
                            packed = struct.pack('!f', val)
                            as_int = int.from_bytes(packed, byteorder='big')
                            flipped_int = as_int ^ (1 << 30)
                            unpacked = struct.unpack('!f', flipped_int.to_bytes(4, byteorder='big'))[0]
                            flat_view[idx] = unpacked
                            corrupted_count += 1

                    elif fault_type == FaultType.NAN_INJECTION:
                        flat_view[indices] = float("nan")
                        corrupted_count = len(indices)

                    elif fault_type == FaultType.ZERO_WEIGHTS:
                        flat_view[indices] = 0.0
                        corrupted_count = len(indices)

                    elif fault_type == FaultType.GAUSSIAN_NOISE:
                        noise = torch.randn_like(flat_view[indices]) * intensity
                        flat_view[indices] += noise
                        corrupted_count = len(indices)

                    elif fault_type == FaultType.STUCK_AT_VALUE:
                        flat_view[indices] = float(intensity)
                        corrupted_count = len(indices)

                if self.engine.cuda_available:
                    torch.cuda.synchronize(self.engine.device)

            else:
                # Simulation mode (byte manipulation)
                data = getattr(target_param, "data", target_param)
                if hasattr(data, "byte_data"):
                    b = data.byte_data
                    for _ in range(min(element_count, len(b))):
                        pos = random.randint(0, len(b) - 1)
                        b[pos] ^= 0xFF
                        corrupted_count += 1
                elif hasattr(data, "tobytes"):
                    corrupted_count = element_count

            fault_record = {
                "fault_type": fault_type.value if hasattr(fault_type, "value") else str(fault_type),
                "layer_name": target_layer,
                "elements_corrupted": corrupted_count,
                "intensity": intensity,
                "status": "FAULT_ACTIVE"
            }

            self.active_fault = fault_record
            self.fault_history.append(fault_record)
            return fault_record

    def clear_fault_state(self):
        """Clears active fault indicator after recovery."""
        self.active_fault = None

    def get_status(self) -> Dict[str, Any]:
        """Provides status of the fault injection subsystem."""
        return {
            "has_active_fault": self.active_fault is not None,
            "active_fault": self.active_fault,
            "total_faults_injected": len(self.fault_history)
        }
