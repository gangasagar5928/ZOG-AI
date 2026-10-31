"""Deterministic ADCS Control Model (PyTorch Neural Execution Graph).

Maps 7-element kinematic state input (error quaternion q_e, angular velocity omega)
to 3-axis reaction-wheel commanded torques (tau_cmd).
Strictly deterministic, frozen parameters, evaluation mode.
Partitioned into 4 sequential parameter blocks for Tier 3 idle scrubbing.
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple
import torch
import torch.nn as nn


def enforce_deterministic_runtime() -> None:
    """Enforce deterministic PyTorch execution environment."""
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.use_deterministic_algorithms(True, warn_only=False)
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)


class DeterministicADCSModel(nn.Module):
    """Deterministic Multi-Layer Perceptron for Satellite Attitude Control.

    State Input: [q_w, q_x, q_y, q_z, omega_x, omega_y, omega_z] in R^7
    Control Output: [tau_x, tau_y, tau_z] in R^3
    Partitioned into 4 explicit blocks:
      Block 0: fc1 (7 -> 64)
      Block 1: fc2 (64 -> 64)
      Block 2: fc3 (64 -> 32)
      Block 3: fc4 (32 -> 3)
    """

    def __init__(self, max_torque: float = 0.05, seed: int = 42) -> None:
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

        self._init_weights()
        self.eval()

        # Freeze parameter gradients
        for p in self.parameters():
            p.requires_grad = False

    def _init_weights(self) -> None:
        """Initialize weights deterministically to generate stable, bounded ADCS torques."""
        # Use orthogonal/kaiming deterministic initialization
        for idx, block in enumerate([self.block0, self.block1, self.block2]):
            nn.init.orthogonal_(block.weight, gain=0.8)
            nn.init.zeros_(block.bias)

        # Output layer initialized with small weights so nominal torques stay well within limits
        nn.init.uniform_(self.block3.weight, -0.005, 0.005)
        nn.init.zeros_(self.block3.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward inference pass.
        
        Args:
            x: Input tensor of shape (batch, 7) or (7,)
        Returns:
            Commanded torque tensor of shape (batch, 3) or (3,)
        """
        if x.dim() == 1:
            x = x.unsqueeze(0)
            squeeze_output = True
        else:
            squeeze_output = False

        h0 = self.act0(self.block0(x))
        h1 = self.act1(self.block1(h0))
        h2 = self.act2(self.block2(h1))
        out = self.block3(h2)

        if squeeze_output:
            return out.squeeze(0)
        return out

    def get_parameter_blocks(self) -> List[Tuple[str, List[torch.nn.Parameter]]]:
        """Return parameters grouped into 4 distinct blocks for Tier 3 cyclic scrubbing."""
        return [
            ("block0_fc1", [self.block0.weight, self.block0.bias]),
            ("block1_fc2", [self.block1.weight, self.block1.bias]),
            ("block2_fc3", [self.block2.weight, self.block2.bias]),
            ("block3_fc4", [self.block3.weight, self.block3.bias]),
        ]

    def get_named_parameters_dict(self) -> Dict[str, torch.Tensor]:
        """Return detached clone dictionary of all model parameters."""
        return {name: param.detach().clone() for name, param in self.named_parameters()}
