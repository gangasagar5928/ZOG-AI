"""Tests for IEEE-754 FP32 In-Memory Bit-Mutation Harness."""

import pytest
import torch

from radzero.core.adcs_model import DeterministicADCSModel
from radzero.core.types import BitfieldTarget
from radzero.mutation.ieee754_injector import IEEE754Injector


def test_sign_bit_mutation_flips_polarity():
    """Verify sign bit (bit 31) inversion reverses numerical sign."""
    model = DeterministicADCSModel()
    
    # Target weight and find non-zero element
    param = model.block0.weight
    orig_val = float(param.data[0, 0].item())
    if orig_val == 0.0:
        param.data[0, 0] = 0.5
        orig_val = 0.5

    strike = IEEE754Injector.inject(
        model,
        layer_name="block0.weight",
        target=BitfieldTarget.SIGN,
        element_idx=(0, 0),
    )

    assert strike.bit_index == 31
    mutated_val = float(param.data[0, 0].item())
    assert mutated_val == -orig_val, f"Expected {-orig_val}, got {mutated_val}"


def test_exponent_explosion_scales_magnitude():
    """Verify exponent bit (0 -> 1) triggers dramatic numerical surge."""
    model = DeterministicADCSModel()
    param = model.block0.weight
    orig_val = float(param.data[0, 0].item())

    strike = IEEE754Injector.inject(
        model,
        layer_name="block0.weight",
        target=BitfieldTarget.EXPONENT_EXPLODE,
        element_idx=(0, 0),
    )

    mutated_val = float(param.data[0, 0].item())
    assert 23 <= strike.bit_index <= 30
    assert abs(mutated_val) > abs(orig_val) or not torch.isfinite(torch.tensor(mutated_val))


def test_exponent_collapse_drops_magnitude():
    """Verify exponent collapse (1 -> 0) forces weight towards subnormal/zero regime."""
    model = DeterministicADCSModel()
    param = model.block0.weight
    # Ensure starting with known non-zero float
    param.data[0, 0] = 1.0

    strike = IEEE754Injector.inject(
        model,
        layer_name="block0.weight",
        target=BitfieldTarget.EXPONENT_COLLAPSE,
        element_idx=(0, 0),
    )

    mutated_val = float(param.data[0, 0].item())
    assert abs(mutated_val) < 1.0, f"Expected collapsed magnitude < 1.0, got {mutated_val}"


def test_mantissa_mutation_subtle_shift():
    """Verify mantissa mutation causes slight precision alteration without NaN/Inf."""
    model = DeterministicADCSModel()
    param = model.block0.weight
    param.data[0, 0] = 0.75

    strike = IEEE754Injector.inject(
        model,
        layer_name="block0.weight",
        target=BitfieldTarget.MANTISSA,
        element_idx=(0, 0),
    )

    assert 0 <= strike.bit_index <= 22
    mutated_val = float(param.data[0, 0].item())
    assert torch.isfinite(torch.tensor(mutated_val))
    assert mutated_val != 0.75


def test_multidimensional_element_idx_mapping():
    """Verify 2D element_idx maps via row-major index, not product."""
    model = DeterministicADCSModel()
    param = model.block0.weight  # Shape (64, 7)
    param.data[3, 5] = 1.0

    strike = IEEE754Injector.inject(
        model,
        layer_name="block0.weight",
        target=BitfieldTarget.EXPONENT_COLLAPSE,
        element_idx=(3, 5),
    )

    # In shape (64, 7), (3, 5) row-major is 3 * 7 + 5 = 26
    assert strike.element_index == (3, 5)
    assert param.data[3, 5].item() != 1.0, "Element at (3, 5) must be mutated"
