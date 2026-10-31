"""Tests for Deterministic ADCS Control Model."""

import numpy as np
import pytest
import torch

from radzero.core.adcs_model import DeterministicADCSModel, enforce_deterministic_runtime


def test_deterministic_reproducibility():
    """Verify that model forward pass is strictly deterministic."""
    enforce_deterministic_runtime()
    model1 = DeterministicADCSModel(seed=42)
    model2 = DeterministicADCSModel(seed=42)

    x = torch.tensor([1.0, 0.0, 0.0, 0.0, 0.01, -0.01, 0.02], dtype=torch.float32)

    with torch.no_grad():
        out1 = model1(x)
        out2 = model2(x)

    assert torch.allclose(out1, out2, atol=1e-7), "Model outputs must be strictly deterministic"


def test_evaluation_mode_and_frozen_weights():
    """Verify weights have requires_grad=False and model is in eval mode."""
    model = DeterministicADCSModel()
    assert not model.training, "Model must execute strictly in evaluation mode"
    for name, param in model.named_parameters():
        assert not param.requires_grad, f"Parameter {name} must be frozen"


def test_input_output_dimensions():
    """Verify 7-element state input maps to 3 commanded torques."""
    model = DeterministicADCSModel()
    
    # Single sample
    x_single = torch.randn(7)
    with torch.no_grad():
        out_single = model(x_single)
    assert out_single.shape == (3,)

    # Batch sample
    x_batch = torch.randn(10, 7)
    with torch.no_grad():
        out_batch = model(x_batch)
    assert out_batch.shape == (10, 3)


def test_nominal_torque_bounds():
    """Verify uncorrupted initial weights produce torques within nominal limits."""
    model = DeterministicADCSModel(max_torque=0.05)
    # 50 random nominal states
    for _ in range(50):
        q = np.random.randn(4)
        q /= np.linalg.norm(q)
        w = np.random.uniform(-0.02, 0.02, size=3)
        state = torch.tensor(np.concatenate([q, w]), dtype=torch.float32)
        with torch.no_grad():
            tau = model(state)
        assert torch.all(tau.abs() <= 0.05), f"Nominal torque breached max_torque: {tau}"


def test_four_block_partitioning():
    """Verify model parameters are cleanly partitioned into 4 distinct blocks for Tier 3."""
    model = DeterministicADCSModel()
    blocks = model.get_parameter_blocks()
    assert len(blocks) == 4, f"Expected 4 blocks for 400 ms cycle, got {len(blocks)}"
    block_names = [b[0] for b in blocks]
    assert block_names == ["block0_fc1", "block1_fc2", "block2_fc3", "block3_fc4"]
