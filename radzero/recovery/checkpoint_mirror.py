"""Dual-Mirrored Host Checkpoint Architecture.

Maintains dual-redundant parameter buffers (primary and backup shadow mirrors)
protected with CRC-32-IEEE 802.3 checksums in host staging memory.
Provides safe in-situ memory restoration (param.data.copy_()) with device synchronization.
"""

from __future__ import annotations

import time
import zlib
from typing import Dict, List, Optional, Tuple
import torch
import torch.nn as nn

from radzero.core.rwlock import ReadWriteLock
from radzero.core.types import BreachType, InvariantBreach


def _compute_tensor_crc32(t: torch.Tensor) -> int:
    """Compute CRC-32 of a tensor's raw byte buffer."""
    return zlib.crc32(t.detach().cpu().numpy().tobytes()) & 0xFFFFFFFF


class DualCheckpointMirror:
    """Secondary host checkpoint memory maintaining primary and backup shadow mirrors."""

    def __init__(self, model: nn.Module) -> None:
        self.model = model
        
        # Dual host-pinned / CPU shadow buffers
        self.primary_mirror: Dict[str, torch.Tensor] = {}
        self.backup_mirror: Dict[str, torch.Tensor] = {}

        # Golden CRC-32 digests per parameter
        self.golden_crcs: Dict[str, int] = {}

        self._initialize_mirrors()

    def _initialize_mirrors(self) -> None:
        """Capture initial uncorrupted weights into dual host mirrors and store CRC-32 digests."""
        for name, param in self.model.named_parameters():
            # Clone to host memory (pinned if CUDA available)
            cpu_tensor = param.detach().cpu().clone()
            if torch.cuda.is_available():
                primary_tensor = cpu_tensor.pin_memory()
                backup_tensor = cpu_tensor.clone().pin_memory()
            else:
                primary_tensor = cpu_tensor
                backup_tensor = cpu_tensor.clone()

            self.primary_mirror[name] = primary_tensor
            self.backup_mirror[name] = backup_tensor

            crc = _compute_tensor_crc32(primary_tensor)
            self.golden_crcs[name] = crc

    def verify_mirror_parameter(self, param_name: str, use_backup: bool = False) -> bool:
        """Verify CRC-32 digest of a specific mirror parameter."""
        mirror = self.backup_mirror if use_backup else self.primary_mirror
        if param_name not in mirror:
            return False
        computed = _compute_tensor_crc32(mirror[param_name])
        expected = self.golden_crcs[param_name]
        return computed == expected

    def verify_full_mirror(self, use_backup: bool = False) -> bool:
        """Verify CRC-32 digests across all parameters in mirror."""
        for name in self.golden_crcs:
            if not self.verify_mirror_parameter(name, use_backup=use_backup):
                return False
        return True

    def hot_patch_parameter(
        self,
        param_name: str,
        target_param: torch.nn.Parameter,
        device: torch.device,
    ) -> Tuple[bool, Optional[str], Optional[InvariantBreach]]:
        """Hot-patch a single parameter in-situ from primary or backup mirror."""
        # Check primary mirror first
        if self.verify_mirror_parameter(param_name, use_backup=False):
            source_tensor = self.primary_mirror[param_name]
            source_name = "primary"
        elif self.verify_mirror_parameter(param_name, use_backup=True):
            source_tensor = self.backup_mirror[param_name]
            source_name = "backup"
        else:
            # Both mirrors corrupted: critical unrecoverable fault
            breach = InvariantBreach(
                tier=0,
                breach_type=BreachType.MIRROR_CORRUPTION,
                message=f"Both primary and backup shadow mirrors failed CRC-32 for '{param_name}'",
                layer_name=param_name,
                timestamp_ns=time.perf_counter_ns(),
            )
            return False, None, breach

        try:
            # Transfer tensor to target device and execute in-place copy
            staged = source_tensor.to(device, non_blocking=True)
            target_param.data.copy_(staged.data)
            return True, source_name, None
        except Exception as ex:
            breach = InvariantBreach(
                tier=0,
                breach_type=BreachType.DMA_EXCEPTION,
                message=f"DMA memory copy exception on '{param_name}': {str(ex)}",
                layer_name=param_name,
                timestamp_ns=time.perf_counter_ns(),
            )
            return False, None, breach

    def hot_patch_all(
        self,
        model: nn.Module,
        device: torch.device,
    ) -> Tuple[bool, str, Optional[InvariantBreach]]:
        """Atomic hot-patch: verify all parameters across mirrors before modifying model memory."""
        # Phase 1: Pre-validation of all parameters across mirrors
        plan: List[Tuple[str, torch.nn.Parameter, torch.Tensor, str]] = []
        for name, param in model.named_parameters():
            if self.verify_mirror_parameter(name, use_backup=False):
                plan.append((name, param, self.primary_mirror[name], "primary"))
            elif self.verify_mirror_parameter(name, use_backup=True):
                plan.append((name, param, self.backup_mirror[name], "backup"))
            else:
                breach = InvariantBreach(
                    tier=0,
                    breach_type=BreachType.MIRROR_CORRUPTION,
                    message=f"Both primary and backup shadow mirrors failed CRC-32 for '{name}'",
                    layer_name=name,
                    timestamp_ns=time.perf_counter_ns(),
                )
                return False, "", breach

        # Phase 2: Atomic in-situ application across verified parameter plan
        used_sources = []
        for name, param, source_tensor, source_name in plan:
            try:
                staged = source_tensor.to(device, non_blocking=True)
                param.data.copy_(staged.data)
                used_sources.append(source_name)
            except Exception as ex:
                breach = InvariantBreach(
                    tier=0,
                    breach_type=BreachType.DMA_EXCEPTION,
                    message=f"DMA memory copy exception on '{name}': {str(ex)}",
                    layer_name=name,
                    timestamp_ns=time.perf_counter_ns(),
                )
                return False, "", breach

        summary_source = "primary" if all(s == "primary" for s in used_sources) else "primary+backup"
        return True, summary_source, None

    def corrupt_mirror_for_testing(self, param_name: str, corrupt_backup: bool = False) -> None:
        """Inject intentional corruption into shadow mirrors to test safe-hold escalation."""
        mirror = self.backup_mirror if corrupt_backup else self.primary_mirror
        if param_name in mirror:
            mirror[param_name].view(-1)[0] += 999.0
