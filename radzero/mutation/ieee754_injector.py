"""IEEE-754 FP32 In-Memory Bit-Mutation Harness.

Simulates physical Single-Event Upsets (SEUs) induced by ionizing radiation:
  - Sign Bit (Bit 31): Reverses torque polarity.
  - Exponent Bits (Bits 30-23): Induces dynamic range explosion (0 -> 1) or collapse (1 -> 0).
  - Mantissa Bits (Bits 22-0): Simulates subtle in-bounds precision shifts.
Directly manipulates raw IEEE-754 bitfields in-place in tensor memory.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import List, Optional, Tuple
import torch
import torch.nn as nn

from radzero.core.types import BitfieldTarget


@dataclass
class SEUStrikeRecord:
    """Audit log of an injected SEU physical strike."""
    layer_name: str
    param_type: str                   # 'weight' or 'bias'
    element_index: Tuple[int, ...]
    bitfield_target: BitfieldTarget
    bit_index: int
    original_float: float
    mutated_float: float
    original_hex: str
    mutated_hex: str


class IEEE754Injector:
    """In-memory bitfield mutation engine targeting raw IEEE-754 FP32 representations."""

    @staticmethod
    def _get_target_param(
        model: nn.Module,
        layer_name: Optional[str] = None,
        target: Optional[BitfieldTarget] = None,
    ) -> Tuple[str, torch.nn.Parameter]:
        """Locate parameter for SEU injection."""
        candidates = []
        for name, param in model.named_parameters():
            if layer_name is None or layer_name in name:
                # If target requires non-zero bits (EXPONENT_COLLAPSE or SIGN), prefer non-zero parameters
                if target in (BitfieldTarget.EXPONENT_COLLAPSE, BitfieldTarget.SIGN):
                    if (param.data.abs() > 1e-9).any():
                        candidates.append((name, param))
                else:
                    candidates.append((name, param))

        if not candidates:
            # Fallback to weight tensors
            weights = [(name, param) for name, param in model.named_parameters() if "weight" in name]
            if weights:
                return random.choice(weights)
            first_name, first_param = next(model.named_parameters())
            return first_name, first_param

        return random.choice(candidates)

    @classmethod
    def inject(
        cls,
        model: nn.Module,
        layer_name: Optional[str] = None,
        target: BitfieldTarget = BitfieldTarget.EXPONENT_EXPLODE,
        element_idx: Optional[Tuple[int, ...]] = None,
    ) -> SEUStrikeRecord:
        """Inject an in-place SEU bit-mutation into a model parameter tensor.

        Args:
            model: PyTorch model holding parameters.
            layer_name: Optional layer name substring to target.
            target: SEU bitfield target (SIGN, EXPONENT_EXPLODE, EXPONENT_COLLAPSE, MANTISSA).
            element_idx: Optional specific element coordinate within tensor.

        Returns:
            SEUStrikeRecord detailing the mutated bitfield and numerical change.
        """
        param_name, param = cls._get_target_param(model, layer_name, target=target)
        data = param.data

        # Reshape to 1D view for uniform indexing
        flat_data = data.view(-1)
        num_elements = flat_data.numel()

        if element_idx is not None:
            # If flat index or multi-dim index provided
            if isinstance(element_idx, int):
                flat_idx = element_idx % num_elements
                coord = (flat_idx,)
            else:
                import numpy as np
                flat_idx = int(np.ravel_multi_index(element_idx, tuple(param.shape))) % num_elements
                coord = tuple(int(x) for x in element_idx)
        else:
            # When selecting target randomly, ensure non-zero values for SIGN and EXPONENT_COLLAPSE
            # to prevent silent no-ops (+0.0 -> -0.0 or 0 -> 0)
            if target in (BitfieldTarget.SIGN, BitfieldTarget.EXPONENT_COLLAPSE):
                nonzero_indices = (flat_data.abs() > 1e-9).nonzero(as_tuple=True)[0]
                if len(nonzero_indices) > 0:
                    flat_idx = int(nonzero_indices[random.randint(0, len(nonzero_indices) - 1)].item())
                else:
                    flat_idx = random.randint(0, num_elements - 1)
            else:
                flat_idx = random.randint(0, num_elements - 1)
            import numpy as np
            coord = tuple(int(x) for x in np.unravel_index(flat_idx, tuple(param.shape)))

        # View raw memory as 32-bit signed integer (bitwise operations on IEEE-754)
        int_view = flat_data.view(torch.int32)
        # Convert signed int32 to unsigned 32-bit integer for clean bitwise operations
        orig_signed = int(int_view[flat_idx].item())
        orig_uint = orig_signed & 0xFFFFFFFF
        orig_float = float(flat_data[flat_idx].item())

        mutated_uint = orig_uint
        bit_index = 0

        if target == BitfieldTarget.SIGN:
            # Bit 31: Flip sign bit (mask 0x80000000)
            bit_index = 31
            mutated_uint ^= (1 << 31)
            # If original value was zero, set small exponent to guarantee non-zero polarity change
            if orig_float == 0.0:
                mutated_uint |= (120 << 23)

        elif target == BitfieldTarget.EXPONENT_EXPLODE:
            # Bits 30-23: Exponent explosion (0 -> 1)
            # Find a 0 bit in the upper exponent bits (bits 28-30) or force bit 30 to 1
            exponent_bits = [30, 29, 28, 27]
            zero_exp_bits = [b for b in exponent_bits if not (orig_uint & (1 << b))]
            bit_index = random.choice(zero_exp_bits) if zero_exp_bits else 30
            mutated_uint |= (1 << bit_index)

        elif target == BitfieldTarget.EXPONENT_COLLAPSE:
            # Bits 30-23: Exponent collapse (1 -> 0)
            # Force high exponent bits to 0 to drop value into subnormal/zero regime
            exponent_bits = [30, 29, 28, 27, 26, 25, 24, 23]
            one_exp_bits = [b for b in exponent_bits if (orig_uint & (1 << b))]
            if one_exp_bits:
                bit_index = random.choice(one_exp_bits)
                mutated_uint &= ~(1 << bit_index)
            else:
                bit_index = 30
                mutated_uint ^= (1 << bit_index)

        elif target == BitfieldTarget.MANTISSA:
            # Bits 15-0: Subtle in-bounds precision shift (restricting to bits 0-15)
            bit_index = random.randint(0, 15)
            mutated_uint ^= (1 << bit_index)

        # Convert back from unsigned 32-bit to signed 32-bit int for PyTorch tensor assignment
        mutated_uint &= 0xFFFFFFFF
        if mutated_uint >= (1 << 31):
            mutated_signed = mutated_uint - (1 << 32)
        else:
            mutated_signed = mutated_uint

        # In-place write back to tensor memory
        int_view[flat_idx] = mutated_signed
        mutated_float = float(flat_data[flat_idx].item())

        return SEUStrikeRecord(
            layer_name=param_name,
            param_type="weight" if "weight" in param_name else "bias",
            element_index=coord,
            bitfield_target=target,
            bit_index=bit_index,
            original_float=orig_float,
            mutated_float=mutated_float,
            original_hex=f"0x{orig_uint:08X}",
            mutated_hex=f"0x{mutated_uint:08X}",
        )
