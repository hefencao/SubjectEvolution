"""Disabled null object and host-authoritative Subject VM runtime."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .activation import SubjectVMActivationResult, execute_activation
from .config import SUBJECT_VM_STAGE2_SCHEMA, SubjectVMConfig
from .lifecycle import inherit_birth_rows, release_dead_rows
from .storage import SubjectVMRegionUsage, SubjectVMStorage

RUNTIME_SCHEMA_V1 = "se-subject-vm-runtime-stage1-v1"
RUNTIME_SCHEMA = "se-subject-vm-runtime-v2"


@dataclass(frozen=True)
class SubjectVMDeviceContract:
    schema: str
    host_authoritative: bool
    device_allocation: bool
    device_sync: bool
    consumes_random_numbers: bool
    affects_action_or_cost: bool
    supported_execution_backends: tuple[str, ...]


STAGE1_DEVICE_CONTRACT = SubjectVMDeviceContract(
    schema="subject-vm-stage1-host-inert-device-contract-v1",
    host_authoritative=True,
    device_allocation=False,
    device_sync=False,
    consumes_random_numbers=False,
    affects_action_or_cost=False,
    supported_execution_backends=("cpu", "cpu-fallback-no-gpu", "gpu-strict-reference", "gpu-hybrid-accelerated"),
)

STAGE2_DEVICE_CONTRACT = SubjectVMDeviceContract(
    schema="subject-vm-stage2-cpu-reference-device-contract-v1",
    host_authoritative=True,
    device_allocation=False,
    device_sync=False,
    consumes_random_numbers=False,
    affects_action_or_cost=True,
    supported_execution_backends=("cpu",),
)


@dataclass
class SubjectVMActivationAccounting:
    activation_calls: int = 0
    structural_node_units: int = 0
    structural_edge_units: int = 0
    node_execution_units: int = 0
    edge_transmission_units: int = 0
    cross_region_transmission_units: int = 0
    output_contribution_units: int = 0
    last_activation_tick: int = -1

    def record(self, result: SubjectVMActivationResult) -> None:
        usage = result.usage
        self.activation_calls += 1
        self.structural_node_units += usage.structural_nodes
        self.structural_edge_units += usage.structural_edges
        self.node_execution_units += usage.executed_nodes
        self.edge_transmission_units += usage.transmitted_edges
        self.cross_region_transmission_units += usage.cross_region_transmissions
        self.output_contribution_units += usage.output_contributions
        self.last_activation_tick = usage.tick


class SubjectVMRuntime:
    """Tiny no-op wrapper when disabled; fixed storage owner when enabled."""

    def __init__(
        self,
        cfg: SubjectVMConfig,
        entity_capacity: int,
        storage: SubjectVMStorage | None = None,
        *,
        restore_mode: str = "initialized",
        activation_accounting: SubjectVMActivationAccounting | None = None,
    ) -> None:
        self.cfg = cfg
        self.entity_capacity = int(entity_capacity)
        self.storage = storage
        self.restore_mode = str(restore_mode)
        self.activation_accounting = (
            activation_accounting or SubjectVMActivationAccounting()
        )
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
        mode = "initialized-stage2-empty" if cfg.activation_enabled else "initialized-empty"
        return cls(cfg, entity_capacity, storage, restore_mode=mode)

    @property
    def enabled(self) -> bool:
        return self.storage is not None

    @property
    def activation_enabled(self) -> bool:
        return self.cfg.schema == SUBJECT_VM_STAGE2_SCHEMA

    @property
    def device_contract(self) -> SubjectVMDeviceContract:
        return STAGE2_DEVICE_CONTRACT if self.activation_enabled else STAGE1_DEVICE_CONTRACT

    def require_execution_backend(
        self, backend: str, *, requested_backend: str | None = None
    ) -> None:
        resolved = str(backend)
        if self.activation_enabled:
            allowed = resolved == "cpu" or (
                resolved == "cpu-fallback-no-gpu" and requested_backend == "auto"
            )
        else:
            allowed = resolved in self.device_contract.supported_execution_backends
        if not allowed:
            raise RuntimeError(
                f"{self.device_contract.schema} does not support backend {backend!r}"
            )

    def has_expressed_graph(self, rows: np.ndarray) -> bool:
        return bool(
            self.activation_enabled
            and self.storage is not None
            and self.storage.has_expressed_graph(rows)
        )

    def activate(
        self,
        *,
        rows: np.ndarray,
        input_values: np.ndarray,
        tick: int,
        output_width: int,
    ) -> SubjectVMActivationResult:
        if not self.activation_enabled or self.storage is None:
            raise RuntimeError("subject_vm activation is not enabled")
        result = execute_activation(
            self.storage,
            rows=rows,
            input_values=input_values,
            tick=tick,
            output_width=output_width,
        )
        self.activation_accounting.record(result)
        return result

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
            "activation_accounting": asdict(self.activation_accounting),
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
            result = cls.initialize(
                cfg,
                entity_capacity=entity_capacity,
                active_rows=rows,
                entity_ids=entity_ids,
                subject_ids=subject_ids,
            )
            result.restore_mode = "compatibility-empty-rebuild"
            return result
        schema = payload.get("schema")
        if schema not in {RUNTIME_SCHEMA, RUNTIME_SCHEMA_V1}:
            raise ValueError("unsupported subject_vm runtime checkpoint schema")
        if schema == RUNTIME_SCHEMA_V1 and cfg.activation_enabled:
            raise ValueError("Stage-2 subject_vm cannot restore Stage-1 runtime state")
        expected_contract = (
            STAGE1_DEVICE_CONTRACT.schema
            if schema == RUNTIME_SCHEMA_V1
            else (STAGE2_DEVICE_CONTRACT.schema if cfg.activation_enabled else STAGE1_DEVICE_CONTRACT.schema)
        )
        if payload.get("device_contract") != expected_contract:
            raise ValueError("subject_vm device contract mismatch")
        storage = SubjectVMStorage.from_snapshot(
            cfg, entity_capacity, payload["storage"]
        )
        storage.validate_owners(alive, entity_ids, subject_ids)
        accounting_raw = payload.get("activation_accounting", {})
        accounting = SubjectVMActivationAccounting(
            **{
                key: int(accounting_raw.get(key, default))
                for key, default in asdict(SubjectVMActivationAccounting()).items()
            }
        )
        return cls(
            cfg,
            entity_capacity,
            storage,
            restore_mode=str(payload.get("restore_mode", "checkpoint-restored")),
            activation_accounting=accounting,
        )

    def region_usage(self) -> tuple[SubjectVMRegionUsage, ...]:
        return () if self.storage is None else self.storage.region_usage()

    def diagnostics(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "activation_enabled": self.activation_enabled,
            "restore_mode": self.restore_mode,
            "device_contract": self.device_contract.schema,
            "activation_accounting": asdict(self.activation_accounting),
            "regions": [asdict(value) for value in self.region_usage()],
        }

    def clone(self) -> "SubjectVMRuntime":
        return type(self)(
            self.cfg,
            self.entity_capacity,
            None if self.storage is None else self.storage.clone(),
            restore_mode=self.restore_mode,
            activation_accounting=SubjectVMActivationAccounting(
                **asdict(self.activation_accounting)
            ),
        )


__all__ = [
    "RUNTIME_SCHEMA",
    "RUNTIME_SCHEMA_V1",
    "STAGE1_DEVICE_CONTRACT",
    "STAGE2_DEVICE_CONTRACT",
    "SubjectVMActivationAccounting",
    "SubjectVMDeviceContract",
    "SubjectVMRuntime",
]
