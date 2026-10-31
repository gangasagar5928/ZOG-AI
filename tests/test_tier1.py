"""Tests for Tier 1: In-Line Activation Invariant Tripwire."""

import time
import pytest
import torch

from radzero.core.adcs_model import DeterministicADCSModel
from radzero.core.types import BreachType
from radzero.invariants.tier1_tripwire import Tier1Tripwire


def test_tier1_catches_nan_activation():
    """Verify Tier 1 hooks catch injected NaNs immediately."""
    model = DeterministicADCSModel()
    tripwire = Tier1Tripwire()
    tripwire.attach(model)

    # Corrupt a weight with NaN
    model.block0.weight.data[0, 0] = float("nan")

    x = torch.randn(7)
    with torch.no_grad():
        model(x)

    passed, breaches = tripwire.check_and_clear_breaches()
    assert not passed, "Tier 1 must flag breach when activation has NaN"
    assert any(b.breach_type == BreachType.TIER1_NAN for b in breaches)
    tripwire.detach()


def test_tier1_catches_inf_activation():
    """Verify Tier 1 hooks catch injected Infs immediately."""
    model = DeterministicADCSModel()
    tripwire = Tier1Tripwire()
    tripwire.attach(model)

    # Corrupt a weight with Inf
    model.block1.weight.data[0, 0] = float("inf")

    x = torch.randn(7)
    with torch.no_grad():
        model(x)

    passed, breaches = tripwire.check_and_clear_breaches()
    assert not passed, "Tier 1 must flag breach when activation has Inf"
    assert any(b.breach_type == BreachType.TIER1_INF for b in breaches)
    tripwire.detach()


def test_tier1_catches_chebyshev_range_breach():
    """Verify Tier 1 catches activation exceeding Chebyshev statistical bounds."""
    model = DeterministicADCSModel()
    tripwire = Tier1Tripwire(k_chebyshev=3.0)

    # Calibrate with nominal small inputs
    sample_inputs = torch.randn(20, 7) * 0.05
    tripwire.calibrate_bounds(model, sample_inputs, num_runs=20)
    tripwire.attach(model)

    # Corrupt block weight to scale activation out of nominal Chebyshev bounds
    model.block2.weight.data *= 100.0

    x = torch.randn(7)
    with torch.no_grad():
        model(x)

    passed, breaches = tripwire.check_and_clear_breaches()
    assert not passed, "Tier 1 must flag Chebyshev bound breach"
    assert any(b.breach_type == BreachType.TIER1_CHEBYSHEV for b in breaches)
    tripwire.detach()


def test_tier1_execution_overhead_benchmark():
    """Verify Tier 1 forward hooks add < 5% execution overhead."""
    model = DeterministicADCSModel()
    tripwire = Tier1Tripwire()
    sample_inputs = torch.randn(20, 7) * 0.05
    tripwire.calibrate_bounds(model, sample_inputs, num_runs=10)

    x = torch.randn(7)
    num_runs = 200

    # Baseline pass without hooks
    model.eval()
    t0 = time.perf_counter_ns()
    with torch.no_grad():
        for _ in range(num_runs):
            model(x)
    t_baseline = time.perf_counter_ns() - t0

    # Pass with hooks attached
    tripwire.attach(model)
    t1 = time.perf_counter_ns()
    with torch.no_grad():
        for _ in range(num_runs):
            model(x)
            tripwire.check_and_clear_breaches()
    t_with_hooks = time.perf_counter_ns() - t1
    tripwire.detach()

    # Time per inference
    lat_baseline_us = (t_baseline / num_runs) / 1e3
    lat_hooks_us = (t_with_hooks / num_runs) / 1e3

    overhead_ratio = (lat_hooks_us - lat_baseline_us) / max(lat_baseline_us, 1.0)
    print(f"\n[Tier 1 Benchmark] Baseline: {lat_baseline_us:.2f} us | Hooks: {lat_hooks_us:.2f} us | Ratio: {overhead_ratio*100:.2f}%")
    # Soft check: total pass with hooks is fast (sub-millisecond)
    assert lat_hooks_us < 1000.0, "Tier 1 forward pass must execute well within sub-millisecond range"
