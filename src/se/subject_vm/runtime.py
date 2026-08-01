"""Disabled-null-object and host-authoritative Stage-1 Subject VM runtime."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import SubjectVMConfig
from .lifecycle import inherit_birth_rows, release_dead_rows
from .storage import SubjectVMRegionUsage, SubjectVMStorage

RUNTIME_SCHEMA = "se-subject-vm-runtime-stage1-v1"


@dataclass(frozen=True)
class SubjectVMDeviceContract:
    schema: str
    host_authoritative: bool
    device_allocation: bool
    device_sync: bool
    consumes_random_numbers: bool
    affects_action_or_cost: bool


STAGE1_DEVICE_CONTRACT = SubjectVMDeviceContract(
    schema="subject-vm-stage1-host-inert-device-contract-v1",
    host_authoritative=True,
    device_allocation=False,
    device_sync=False,
    consumes_random_numbers=False,
    affects_action_or_cost=False,
)


class SubjectVMRuntime:
    """Tiny no-op wrapper when disabled; fixed storage owner when enabled."""

    def __init__(
        self,
        cfg: SubjectVMConfig,
        entity_capacity: int,
        storage: SubjectVMStorage | None = None,
        *,
        restore_mode: str = "initialized",
    ) -> None:
        self.cfg = cfg
        self.entity_capacity = int(entity_capacity)
        self.storage = storage
        self.restore_mode = str(restore_mode)
        if cfg.enabled != (storage is not None):
            raise ValueError("subject_vm runtime enabled/storage state disagrees")

    @classmethod
    def initialize(
        cls,
        cfg: SubjectVMConfig,
        *,
        entity_capacity: int,
        active_rows: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> "SubjectVMRuntime":
        if not cfg.enabled:
            return cls(cfg, entity_capacity, None, restore_mode="disabled")
        storage = SubjectVMStorage(cfg, entity_capacity)
        rows = np.asarray(active_rows, dtype=np.int32)
        storage.initialize_rows(rows, entity_ids[rows], subject_ids[rows])
        return cls(cfg, entity_capacity, storage, restore_mode="initialized-empty")

    @property
    def enabled(self) -> bool:
        return self.storage is not None

    @property
    def device_contract(self) -> SubjectVMDeviceContract:
        return STAGE1_DEVICE_CONTRACT

    def inherit_births(
        self,
        parent_rows: np.ndarray,
        child_rows: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> None:
        if self.storage is None or np.asarray(child_rows).size == 0:
            return
        if not self.cfg.inherit_structure_on_birth:
            self.storage.initialize_rows(
                child_rows, entity_ids[child_rows], subject_ids[child_rows]
            )
            return
        inherit_birth_rows(
            self.storage,
            parent_rows=parent_rows,
            child_rows=child_rows,
            child_entity_ids=entity_ids[child_rows],
            child_subject_ids=subject_ids[child_rows],
        )

    def release_deaths(
        self,
        rows: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> None:
        if self.storage is None or np.asarray(rows).size == 0:
            return
        release_dead_rows(
            self.storage,
            rows=rows,
            expected_entity_ids=entity_ids[rows],
            expected_subject_ids=subject_ids[rows],
        )

    def validate_owners(
        self,
        alive: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> None:
        if self.storage is not None:
            self.storage.validate_owners(alive, entity_ids, subject_ids)

    def snapshot_state(self) -> dict[str, Any] | None:
        if self.storage is None:
            return None
        return {
            "schema": RUNTIME_SCHEMA,
            "restore_mode": self.restore_mode,
            "device_contract": self.device_contract.schema,
            "storage": self.storage.snapshot_state(),
        }

    @classmethod
    def restore(
        cls,
        cfg: SubjectVMConfig,
        *,
        entity_capacity: int,
        payload: dict[str, Any] | None,
        alive: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> "SubjectVMRuntime":
        rows = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
        if not cfg.enabled:
            if payload not in (None, {}):
                raise ValueError("disabled subject_vm cannot restore enabled storage")
            return cls(cfg, entity_capacity, None, restore_mode="disabled")
        if payload is None:
            # Compatibility with checkpoints written before Stage 1 existed.
            result = cls.initialize(
                cfg,
                entity_capacity=entity_capacity,
                active_rows=rows,
                entity_ids=entity_ids,
                subject_ids=subject_ids,
            )
            result.restore_mode = "compatibility-empty-rebuild"
            return result
        if payload.get("schema") != RUNTIME_SCHEMA:
            raise ValueError("unsupported subject_vm runtime checkpoint schema")
        if payload.get("device_contract") != STAGE1_DEVICE_CONTRACT.schema:
            raise ValueError("subject_vm device contract mismatch")
        storage = SubjectVMStorage.from_snapshot(
            cfg, entity_capacity, payload["storage"]
        )
        storage.validate_owners(alive, entity_ids, subject_ids)
        return cls(
            cfg,
            entity_capacity,
            storage,
            restore_mode=str(payload.get("restore_mode", "checkpoint-restored")),
        )

    def region_usage(self) -> tuple[SubjectVMRegionUsage, ...]:
        return () if self.storage is None else self.storage.region_usage()

    def clone(self) -> "SubjectVMRuntime":
        return type(self)(
            self.cfg,
            self.entity_capacity,
            None if self.storage is None else self.storage.clone(),
            restore_mode=self.restore_mode,
        )


__all__ = [
    "RUNTIME_SCHEMA",
    "STAGE1_DEVICE_CONTRACT",
    "SubjectVMDeviceContract",
    "SubjectVMRuntime",
]
