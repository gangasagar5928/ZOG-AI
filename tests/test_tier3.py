"""Tests for Tier 3: Asynchronous Parameter Scrubber."""

import pytest
import torch

from radzero.core.adcs_model import DeterministicADCSModel
from radzero.core.types import BreachType
from radzero.invariants.tier3_scrubber import Tier3Scrubber


def test_tier3_audit_nominal_match():
    """Verify clean model passes cyclic CRC-32 verification."""
    model = DeterministicADCSModel()
    scrubber = Tier3Scrubber(model)

    # Audit all 4 blocks sequentially
    for _ in range(4):
        passed, breach, block_name, elapsed_ms = scrubber.audit_next_block()
        assert passed, f"Nominal block '{block_name}' should pass CRC-32"
        assert breach is None
        assert elapsed_ms < 15.0, f"Audit elapsed {elapsed_ms} ms exceeded 15 ms budget"


def test_tier3_catches_corrupted_parameter_block():
    """Verify CRC mismatch when a parameter in a block is mutated."""
    model = DeterministicADCSModel()
    scrubber = Tier3Scrubber(model)

    # Mutate a parameter in block1 (fc2)
    model.block1.weight.data[0, 0] += 0.001

    # Perform full audit
    all_passed, breaches, corrupted_blocks = scrubber.audit_all_blocks()
    assert not all_passed, "Scrubber must detect corrupted block"
    assert "block1_fc2" in corrupted_blocks
    assert any(b.breach_type == BreachType.TIER3_CRC_MISMATCH for b in breaches)


def test_tier3_cyclic_sweep_coverage():
    """Verify 4 sequential audits cover all 4 distinct blocks."""
    model = DeterministicADCSModel()
    scrubber = Tier3Scrubber(model)

    audited_blocks = []
    for _ in range(4):
        _, _, block_name, _ = scrubber.audit_next_block()
        audited_blocks.append(block_name)

    expected = ["block0_fc1", "block1_fc2", "block2_fc3", "block3_fc4"]
    assert audited_blocks == expected, f"Expected sweep {expected}, got {audited_blocks}"
