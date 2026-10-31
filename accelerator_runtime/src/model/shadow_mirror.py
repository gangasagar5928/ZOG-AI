"""
Host-Pinned Memory Shadow Mirror Manager.
Allocates host shadow mirrors in host-pinned memory (pin_memory=True)
to maximize PCIe DMA transfer throughput during recovery.

DMA Benefits:
- Host-pinned pages (page-locked) are guaranteed not to be paged out by the OS kernel.
- Allows the GPU's copy engine (DMA engine) to read directly across the PCIe bus
  via non_blocking=True asynchronous transfers without CPU intermediate bounce-buffering.
"""

import hashlib
from typing import Dict, Tuple, Any, List

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class HostPinnedShadowMirror:
    """
    Manages host-pinned memory allocations mirroring all model weights on the GPU.
    Serves as the golden recovery buffer for PCIe DMA transfers.
    """

    def __init__(self, model: Any, pin_memory: bool = True):
        self.model = model
        self.pin_memory = pin_memory
        self.shadow_buffers: Dict[str, Any] = {}
        self.param_metadata: Dict[str, Dict[str, Any]] = {}
        self.total_param_bytes: int = 0
        self.golden_checksums: Dict[str, str] = {}

        self._allocate_shadow_buffers()

    def _allocate_shadow_buffers(self):
        """
        Allocates host-pinned buffers for every trainable parameter and copies
        the pristine golden weights into host RAM.
        """
        self.total_param_bytes = 0

        for name, param in self.model.named_parameters():
            if HAS_TORCH and isinstance(param, torch.Tensor):
                num_bytes = param.numel() * param.element_size()
                self.total_param_bytes += num_bytes

                # Allocate host-pinned memory
                is_cuda_avail = torch.cuda.is_available() and self.pin_memory
                pinned_buffer = torch.empty(
                    param.shape,
                    dtype=param.dtype,
                    device="cpu",
                    pin_memory=is_cuda_avail
                )
                pinned_buffer.copy_(param.data)

                self.shadow_buffers[name] = pinned_buffer
                is_actually_pinned = pinned_buffer.is_pinned() if is_cuda_avail else False

                self.param_metadata[name] = {
                    "shape": list(param.shape),
                    "dtype": str(param.dtype),
                    "numel": param.numel(),
                    "bytes": num_bytes,
                    "is_pinned": is_actually_pinned
                }
                self.golden_checksums[name] = self._compute_tensor_hash(pinned_buffer)

            else:
                # Lightweight pure-Python / Simulation fallback
                data = getattr(param, "data", param)
                if hasattr(data, "byte_data"):
                    raw_bytes = bytes(data.byte_data)
                    shape = getattr(param, "shape", (len(raw_bytes),))
                    numel = getattr(param, "numel", lambda: len(raw_bytes) // 4)()
                    nbytes = len(raw_bytes)
                elif hasattr(data, "tobytes"):
                    raw_bytes = data.tobytes()
                    shape = list(data.shape)
                    numel = int(data.size)
                    nbytes = len(raw_bytes)
                else:
                    raw_bytes = str(data).encode("utf-8")
                    shape = [len(raw_bytes)]
                    numel = len(raw_bytes)
                    nbytes = len(raw_bytes)

                self.total_param_bytes += nbytes
                self.shadow_buffers[name] = bytearray(raw_bytes)
                self.param_metadata[name] = {
                    "shape": list(shape),
                    "dtype": "float32",
                    "numel": numel,
                    "bytes": nbytes,
                    "is_pinned": False
                }
                self.golden_checksums[name] = hashlib.sha256(raw_bytes).hexdigest()[:16]

    def _compute_tensor_hash(self, tensor: Any) -> str:
        """Computes 16-character SHA-256 digest of tensor memory."""
        if HAS_TORCH and isinstance(tensor, torch.Tensor):
            cpu_tensor = tensor.detach().cpu().contiguous()
            byte_data = cpu_tensor.numpy().tobytes()
        elif hasattr(tensor, "byte_data"):
            byte_data = bytes(tensor.byte_data)
        elif hasattr(tensor, "tobytes"):
            byte_data = tensor.tobytes()
        elif isinstance(tensor, (bytes, bytearray)):
            byte_data = bytes(tensor)
        else:
            byte_data = str(tensor).encode("utf-8")
        return hashlib.sha256(byte_data).hexdigest()[:16]

    def get_shadow_buffer(self, param_name: str) -> Any:
        return self.shadow_buffers[param_name]

    def get_all_buffers(self) -> Dict[str, Any]:
        return self.shadow_buffers

    def verify_integrity(self, current_model: Any) -> Tuple[bool, List[str]]:
        corrupted = []
        for name, param in current_model.named_parameters():
            current_hash = self._compute_tensor_hash(param.data)
            golden_hash = self.golden_checksums.get(name)
            if current_hash != golden_hash:
                corrupted.append(name)
        return (len(corrupted) == 0, corrupted)

    def get_summary(self) -> Dict[str, Any]:
        pinned_count = sum(1 for m in self.param_metadata.values() if m.get("is_pinned", False))
        return {
            "parameter_count": len(self.shadow_buffers),
            "total_bytes": self.total_param_bytes,
            "total_mb": round(self.total_param_bytes / (1024 * 1024), 3),
            "pinned_tensors": pinned_count,
            "all_pinned": pinned_count == len(self.shadow_buffers) and len(self.shadow_buffers) > 0,
            "parameters": self.param_metadata
        }
