"""Tier 3: Asynchronous Parameter Scrubber (Background Memory Auditor).

Soft real-time cyclic audit of 1 tensor block per 100 ms idle window (<= 15 ms execution budget).
Uses CRC-32-IEEE 802.3 digests against host-pinned shadow mirrors.
Nominal 4-block partition results in a complete model sweep period: T_scrub = 400 ms.
Detects latent/sub-threshold faults masked by zero-valued sensor inputs.
"""

from __future__ import annotations

import time
import zlib
from typing import Dict, List, Optional, Tuple
import torch
import torch.nn as nn

from radzero.core.types import BreachType, InvariantBreach


def compute_crc32(data_bytes: bytes) -> int:
    """Compute standard IEEE 802.3 CRC-32 checksum (polynomial 0xEDB88320)."""
    return zlib.crc32(data_bytes) & 0xFFFFFFFF


class Tier3Scrubber:
    """Cyclic memory scrubber auditing one parameter block per idle frame."""

    def __init__(self, model: nn.Module) -> None:
        self.model = model
        self.blocks = model.get_parameter_blocks()
        self.num_blocks = len(self.blocks)
        self.current_block_index: int = 0
        
        # Golden reference CRC-32 hashes: block_name -> crc32 uint
        self.reference_crcs: Dict[str, int] = {}
        self._compute_reference_crcs()

    def _compute_block_crc(self, params: List[torch.nn.Parameter]) -> int:
        """Concatenate raw bytes of all parameters in block and compute CRC-32."""
        crc = 0
        for p in params:
            # Transfer to host contiguous byte representation
            raw_bytes = p.detach().cpu().numpy().tobytes()
            crc = zlib.crc32(raw_bytes, crc)
        return crc & 0xFFFFFFFF

    def _compute_reference_crcs(self) -> None:
        """Establish baseline golden CRC-32 digests for all parameter blocks."""
        for block_name, params in self.blocks:
            self.reference_crcs[block_name] = self._compute_block_crc(params)

    def audit_next_block(self) -> Tuple[bool, Optional[InvariantBreach], str, float]:
        """Audit the next sequential tensor block against golden host mirror.

        Returns:
            Tuple of:
              - passed: bool
              - breach: Optional[InvariantBreach]
              - block_name: str
              - elapsed_ms: float (audit execution time)
        """
        start_ns = time.perf_counter_ns()
        block_name, params = self.blocks[self.current_block_index]
        expected_crc = self.reference_crcs[block_name]

        current_crc = self._compute_block_crc(params)
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6

        # Advance cyclic counter for 400 ms full sweep
        audited_block = block_name
        self.current_block_index = (self.current_block_index + 1) % self.num_blocks

        if current_crc != expected_crc:
            breach = InvariantBreach(
                tier=3,
                breach_type=BreachType.TIER3_CRC_MISMATCH,
                message=(
                    f"Tier 3 CRC-32 mismatch on '{audited_block}': "
                    f"computed=0x{current_crc:08X}, expected=0x{expected_crc:08X}"
                ),
                layer_name=audited_block,
                observed_value=float(current_crc),
                threshold_value=float(expected_crc),
                timestamp_ns=start_ns,
            )
            return False, breach, audited_block, elapsed_ms

        return True, None, audited_block, elapsed_ms

    def audit_all_blocks(self) -> Tuple[bool, List[InvariantBreach], List[str]]:
        """Perform comprehensive full-model audit across all blocks."""
        all_passed = True
        breaches: List[InvariantBreach] = []
        corrupted_blocks: List[str] = []

        for block_name, params in self.blocks:
            expected = self.reference_crcs[block_name]
            computed = self._compute_block_crc(params)
            if computed != expected:
                all_passed = False
                corrupted_blocks.append(block_name)
                breaches.append(
                    InvariantBreach(
                        tier=3,
                        breach_type=BreachType.TIER3_CRC_MISMATCH,
                        message=f"CRC-32 failure in '{block_name}': 0x{computed:08X} != 0x{expected:08X}",
                        layer_name=block_name,
                        observed_value=float(computed),
                        threshold_value=float(expected),
                        timestamp_ns=time.perf_counter_ns(),
                    )
                )

        return all_passed, breaches, corrupted_blocks

    def get_block_crc_hex_list(self) -> List[str]:
        """Return list of formatted hex CRC strings for telemetry."""
        result = []
        for block_name, params in self.blocks:
            crc = self._compute_block_crc(params)
            result.append(f"{block_name}:0x{crc:08X}")
        return result
