"""
RadZero PyTorch ADCS Model Architecture & Loader for Accelerator Node.
Harmonized with radzero.core.adcs_model.DeterministicADCSModel targeted for the RTX 3050 Mobile accelerator.
Maps 7-element attitude state vectors [q_w, q_x, q_y, q_z, omega_x, omega_y, omega_z] to 3-axis commanded torques.
"""

import os
from typing import Optional, Tuple, Dict, Any

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    class nn:
        class Module:
            pass

try:
    from radzero.core.adcs_model import DeterministicADCSModel
    HAS_ADCS_MODEL = True
except ImportError:
    HAS_ADCS_MODEL = False


if HAS_TORCH:
    if HAS_ADCS_MODEL:
        Member1PerceptionModel = DeterministicADCSModel
    else:
        class DeterministicADCSModelFallback(nn.Module):
            def __init__(self, max_torque: float = 0.05, seed: int = 42):
                super().__init__()
                torch.manual_seed(seed)
                self.max_torque = max_torque
                self.block0 = nn.Linear(7, 64)
                self.act0 = nn.Tanh()
                self.block1 = nn.Linear(64, 64)
                self.act1 = nn.Tanh()
                self.block2 = nn.Linear(64, 32)
                self.act2 = nn.Tanh()
                self.block3 = nn.Linear(32, 3)
                self.eval()
                for p in self.parameters():
                    p.requires_grad = False

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                h0 = self.act0(self.block0(x))
                h1 = self.act1(self.block1(h0))
                h2 = self.act2(self.block2(h1))
                return self.block3(h2)

        Member1PerceptionModel = DeterministicADCSModelFallback

else:
    class MockTensor:
        """Lightweight pure-python tensor representation for zero-dependency test environments."""
        def __init__(self, shape, dtype="float32", data=None):
            self.shape = shape
            self.dtype = dtype
            numel = 1
            for d in shape:
                numel *= d
            self.numel_val = numel
            self.byte_data = bytearray(numel * 4)

        def numel(self):
            return self.numel_val

        def element_size(self):
            return 4

        def clone(self):
            return MockTensor(self.shape, self.dtype, self.byte_data)

        def copy_(self, src):
            if hasattr(src, "byte_data"):
                self.byte_data[:] = src.byte_data[:]
            elif isinstance(src, (bytes, bytearray)):
                self.byte_data[:] = src[:]

        def is_pinned(self):
            return False

        def to(self, device):
            return self

    class Member1PerceptionModel:
        """Simulation model fallback when torch is not present in local test harness."""
        def __init__(self, max_torque: float = 0.05):
            self.max_torque = max_torque
            self._parameters = {
                "block0.weight": MockTensor((64, 7)),
                "block0.bias": MockTensor((64,)),
                "block1.weight": MockTensor((64, 64)),
                "block1.bias": MockTensor((64,)),
                "block2.weight": MockTensor((32, 64)),
                "block2.bias": MockTensor((32,)),
                "block3.weight": MockTensor((3, 32)),
                "block3.bias": MockTensor((3,))
            }

        def named_parameters(self):
            for k, v in self._parameters.items():
                yield k, v

        def forward(self, x):
            return "simulated_torque"

        def __call__(self, x):
            return self.forward(x)

        def to(self, device):
            return self

        def eval(self):
            return self


def create_or_load_member1_model(model_path: Optional[str] = None) -> Any:
    """Instantiates harmonized DeterministicADCSModel architecture or loads weights from disk."""
    if HAS_TORCH:
        if HAS_ADCS_MODEL:
            model = DeterministicADCSModel(max_torque=0.05)
        else:
            model = Member1PerceptionModel()
    else:
        model = Member1PerceptionModel()

    if HAS_TORCH and model_path and os.path.exists(model_path):
        state_dict = torch.load(model_path, map_location="cpu")
        model.load_state_dict(state_dict)
    return model
