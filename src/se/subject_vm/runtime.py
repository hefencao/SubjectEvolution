"""Disabled null object and host-authoritative Subject VM runtime."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .binding import SubjectVMTargetCandidateBatch
from .activation import SubjectVMActivationResult, execute_activation
from .config import SubjectVMConfig
from .eligibility import SubjectVMLocalEligibilityUsage
from .lifecycle import inherit_birth_rows, release_dead_rows
from .storage import SubjectVMRegionUsage, SubjectVMStorage
from .trace import (
    SubjectVMObjectiveEventBatch,
    SubjectVMThoughtTokenBatch,
    SubjectVMTraceAccounting,
    SubjectVMTraceStorage,
)

RUNTIME_SCHEMA_V1 = "se-subject-vm-runtime-stage1-v1"
RUNTIME_SCHEMA_V2 = "se-subject-vm-runtime-v2"
RUNTIME_SCHEMA_V3 = "se-subject-vm-runtime-v3"
RUNTIME_SCHEMA_V4 = "se-subject-vm-runtime-v4"
RUNTIME_SCHEMA_V5 = "se-subject-vm-runtime-v5"
RUNTIME_SCHEMA_V6 = "se-subject-vm-runtime-v6"
RUNTIME_SCHEMA = "se-subject-vm-runtime-v7"


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
    supported_execution_backends=(
        "cpu",
        "cpu-fallback-no-gpu",
        "gpu-strict-reference",
        "gpu-hybrid-accelerated",
    ),
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

STAGE3_DEVICE_CONTRACT = SubjectVMDeviceContract(
    schema="subject-vm-stage3-token-trace-cpu-reference-contract-v1",
    host_authoritative=True,
    device_allocation=False,
    device_sync=False,
    consumes_random_numbers=False,
    affects_action_or_cost=True,
    supported_execution_backends=("cpu",),
)

STAGE3B_DEVICE_CONTRACT = SubjectVMDeviceContract(
    schema="subject-vm-stage3b-local-eligibility-cpu-reference-contract-v1",
    host_authoritative=True,
    device_allocation=False,
    device_sync=False,
    consumes_random_numbers=False,
    affects_action_or_cost=True,
    supported_execution_backends=("cpu",),
)

STAGE3B2_DEVICE_CONTRACT = SubjectVMDeviceContract(
    schema="subject-vm-stage3b2-delayed-association-cpu-reference-contract-v1",
    host_authoritative=True,
    device_allocation=False,
    device_sync=False,
    consumes_random_numbers=False,
    affects_action_or_cost=True,
    supported_execution_backends=("cpu",),
)

STAGE3B3_DEVICE_CONTRACT = SubjectVMDeviceContract(
    schema="subject-vm-stage3b3-modulation-proposal-cpu-reference-contract-v1",
    host_authoritative=True,
    device_allocation=False,
    device_sync=False,
    consumes_random_numbers=False,
    affects_action_or_cost=True,
    supported_execution_backends=("cpu",),
)

STAGE3C1_DEVICE_CONTRACT = SubjectVMDeviceContract(
    schema="subject-vm-stage3c1-target-binding-cpu-reference-contract-v1",
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
    token_contribution_units: int = 0
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
        self.token_contribution_units += usage.token_contributions
        self.last_activation_tick = usage.tick


@dataclass
class SubjectVMEligibilityAccounting:
    activation_calls: int = 0
    decay_calls: int = 0
    decayed_node_units: int = 0
    decayed_edge_units: int = 0
    expired_node_units: int = 0
    expired_edge_units: int = 0
    node_mark_units: int = 0
    edge_mark_units: int = 0
    last_eligibility_tick: int = -1

    def record(self, usage: SubjectVMLocalEligibilityUsage) -> None:
        self.activation_calls += 1
        self.decay_calls += int(usage.decay_calls)
        self.decayed_node_units += int(usage.decayed_nodes)
        self.decayed_edge_units += int(usage.decayed_edges)
        self.expired_node_units += int(usage.expired_nodes)
        self.expired_edge_units += int(usage.expired_edges)
        self.node_mark_units += int(usage.node_marks)
        self.edge_mark_units += int(usage.edge_marks)
        self.last_eligibility_tick = int(usage.tick)


class SubjectVMRuntime:
    """No-op when disabled; graph, token-ring and lifecycle owner when enabled."""

    def __init__(
        self,
        cfg: SubjectVMConfig,
        entity_capacity: int,
        storage: SubjectVMStorage | None = None,
        *,
        trace_storage: SubjectVMTraceStorage | None = None,
        restore_mode: str = "initialized",
        activation_accounting: SubjectVMActivationAccounting | None = None,
        trace_accounting: SubjectVMTraceAccounting | None = None,
        eligibility_accounting: SubjectVMEligibilityAccounting | None = None,
    ) -> None:
        self.cfg = cfg
        self.entity_capacity = int(entity_capacity)
        self.storage = storage
        self.trace_storage = trace_storage
        self.restore_mode = str(restore_mode)
        self.activation_accounting = (
            activation_accounting or SubjectVMActivationAccounting()
        )
        self.trace_accounting = trace_accounting or SubjectVMTraceAccounting()
        self.eligibility_accounting = (
            eligibility_accounting or SubjectVMEligibilityAccounting()
        )
        self._pending_thought_tokens: SubjectVMThoughtTokenBatch | None = None
        self._pending_target_candidates: SubjectVMTargetCandidateBatch | None = None
        if cfg.enabled != (storage is not None):
            raise ValueError("subject_vm runtime enabled/storage state disagrees")
        if cfg.trace_enabled != (trace_storage is not None):
            raise ValueError("subject_vm runtime trace configuration/storage disagrees")

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
        trace_storage = (
            SubjectVMTraceStorage(cfg, entity_capacity) if cfg.trace_enabled else None
        )
        if trace_storage is not None:
            trace_storage.initialize_rows(rows)
        mode = (
            "initialized-stage3c1-empty"
            if cfg.target_binding_enabled
            else "initialized-stage3b3-empty"
            if cfg.modulation_enabled
            else "initialized-stage3b2-empty"
            if cfg.association_enabled
            else "initialized-stage3b-empty"
            if cfg.eligibility_enabled
            else "initialized-stage3-empty"
            if cfg.trace_enabled
            else ("initialized-stage2-empty" if cfg.activation_enabled else "initialized-empty")
        )
        return cls(
            cfg,
            entity_capacity,
            storage,
            trace_storage=trace_storage,
            restore_mode=mode,
        )

    @property
    def enabled(self) -> bool:
        return self.storage is not None

    @property
    def activation_enabled(self) -> bool:
        return self.cfg.activation_enabled

    @property
    def trace_enabled(self) -> bool:
        return self.cfg.trace_enabled

    @property
    def eligibility_enabled(self) -> bool:
        return self.cfg.eligibility_enabled

    @property
    def association_enabled(self) -> bool:
        return self.cfg.association_enabled

    @property
    def modulation_enabled(self) -> bool:
        return self.cfg.modulation_enabled

    @property
    def has_pending_thought_tokens(self) -> bool:
        return self._pending_thought_tokens is not None

    @property
    def target_binding_enabled(self) -> bool:
        return self.cfg.target_binding_enabled

    @property
    def device_contract(self) -> SubjectVMDeviceContract:
        if self.target_binding_enabled:
            return STAGE3C1_DEVICE_CONTRACT
        if self.modulation_enabled:
            return STAGE3B3_DEVICE_CONTRACT
        if self.association_enabled:
            return STAGE3B2_DEVICE_CONTRACT
        if self.eligibility_enabled:
            return STAGE3B_DEVICE_CONTRACT
        if self.trace_enabled:
            return STAGE3_DEVICE_CONTRACT
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
        if self._pending_thought_tokens is not None or self._pending_target_candidates is not None:
            raise RuntimeError("subject_vm prior activation metadata was not committed")
        result = execute_activation(
            self.storage,
            rows=rows,
            input_values=input_values,
            tick=tick,
            output_width=output_width,
        )
        self.activation_accounting.record(result)
        if result.eligibility_usage is not None:
            self.eligibility_accounting.record(result.eligibility_usage)
        self._pending_thought_tokens = (
            result.thought_tokens
            if result.thought_tokens is not None
            and bool(np.any(result.thought_tokens.emitted))
            else None
        )
        self._pending_target_candidates = (
            result.target_candidates if self._pending_thought_tokens is not None else None
        )
        return result

    def commit_objective_events(self, batch: SubjectVMObjectiveEventBatch) -> None:
        if not self.trace_enabled or self.trace_storage is None or self.storage is None:
            raise RuntimeError("subject_vm token/event trace is not enabled")
        if self._pending_thought_tokens is None:
            raise RuntimeError("subject_vm objective event has no pending thought token")
        self.trace_storage.append(
            batch,
            self._pending_thought_tokens,
            owner_entity_ids=self.storage.owner_entity_id,
            owner_subject_ids=self.storage.owner_subject_id,
            accounting=self.trace_accounting,
            target_candidates=self._pending_target_candidates,
        )
        self._pending_thought_tokens = None
        self._pending_target_candidates = None

    def discard_pending_thought_tokens(self) -> None:
        self._pending_thought_tokens = None
        self._pending_target_candidates = None

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
        else:
            inherit_birth_rows(
                self.storage,
                parent_rows=parent_rows,
                child_rows=child_rows,
                child_entity_ids=entity_ids[child_rows],
                child_subject_ids=subject_ids[child_rows],
            )
        if self.trace_storage is not None:
            self.trace_storage.initialize_rows(np.asarray(child_rows, dtype=np.int32))

    def release_deaths(
        self,
        rows: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> None:
        normalized = np.asarray(rows, dtype=np.int32)
        if self.storage is None or normalized.size == 0:
            return
        if self.trace_storage is not None:
            self.trace_storage.clear_rows(normalized)
        release_dead_rows(
            self.storage,
            rows=normalized,
            expected_entity_ids=entity_ids[normalized],
            expected_subject_ids=subject_ids[normalized],
        )

    def compact_rows(
        self, source_rows: np.ndarray, destination_rows: np.ndarray
    ) -> None:
        if self.storage is None:
            return
        self.storage.move_rows(source_rows, destination_rows)
        if self.trace_storage is not None:
            self.trace_storage.move_rows(source_rows, destination_rows)

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
        if self._pending_thought_tokens is not None or self._pending_target_candidates is not None:
            raise RuntimeError("subject_vm cannot checkpoint a partial activation phase")
        payload: dict[str, Any] = {
            "schema": RUNTIME_SCHEMA,
            "restore_mode": self.restore_mode,
            "device_contract": self.device_contract.schema,
            "activation_accounting": asdict(self.activation_accounting),
            "storage": self.storage.snapshot_state(),
        }
        if self.trace_enabled:
            assert self.trace_storage is not None
            payload["trace_accounting"] = asdict(self.trace_accounting)
            payload["trace_storage"] = self.trace_storage.snapshot_state()
        if self.eligibility_enabled:
            payload["eligibility_accounting"] = asdict(
                self.eligibility_accounting
            )
        return payload

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
        if schema not in {
            RUNTIME_SCHEMA,
            RUNTIME_SCHEMA_V6,
            RUNTIME_SCHEMA_V5,
            RUNTIME_SCHEMA_V4,
            RUNTIME_SCHEMA_V3,
            RUNTIME_SCHEMA_V2,
            RUNTIME_SCHEMA_V1,
        }:
            raise ValueError("unsupported subject_vm runtime checkpoint schema")
        if schema == RUNTIME_SCHEMA_V1 and cfg.activation_enabled:
            raise ValueError("active subject_vm cannot restore Stage-1 runtime state")
        compatibility_empty_trace = cfg.trace_enabled and schema == RUNTIME_SCHEMA_V2
        compatibility_empty_eligibility = cfg.eligibility_enabled and schema in {
            RUNTIME_SCHEMA_V2,
            RUNTIME_SCHEMA_V3,
        }
        compatibility_empty_association = (
            cfg.association_enabled and schema == RUNTIME_SCHEMA_V4
        )
        compatibility_empty_modulation = (
            cfg.modulation_enabled and schema == RUNTIME_SCHEMA_V5
        )
        compatibility_empty_binding = (
            cfg.target_binding_enabled and schema == RUNTIME_SCHEMA_V6
        )
        if schema == RUNTIME_SCHEMA_V1:
            expected_contract = STAGE1_DEVICE_CONTRACT.schema
        elif schema == RUNTIME_SCHEMA_V2:
            expected_contract = STAGE2_DEVICE_CONTRACT.schema
        elif schema == RUNTIME_SCHEMA_V3:
            expected_contract = STAGE3_DEVICE_CONTRACT.schema
        elif schema == RUNTIME_SCHEMA_V4:
            expected_contract = STAGE3B_DEVICE_CONTRACT.schema
        elif schema == RUNTIME_SCHEMA_V5:
            expected_contract = STAGE3B2_DEVICE_CONTRACT.schema
        elif schema == RUNTIME_SCHEMA_V6:
            expected_contract = STAGE3B3_DEVICE_CONTRACT.schema
        else:
            expected_contract = (
                STAGE3C1_DEVICE_CONTRACT.schema
                if cfg.target_binding_enabled
                else STAGE3B3_DEVICE_CONTRACT.schema
                if cfg.modulation_enabled
                else STAGE3B2_DEVICE_CONTRACT.schema
                if cfg.association_enabled
                else STAGE3B_DEVICE_CONTRACT.schema
                if cfg.eligibility_enabled
                else (
                    STAGE3_DEVICE_CONTRACT.schema
                    if cfg.trace_enabled
                    else (
                        STAGE2_DEVICE_CONTRACT.schema
                        if cfg.activation_enabled
                        else STAGE1_DEVICE_CONTRACT.schema
                    )
                )
            )
        if payload.get("device_contract") != expected_contract:
            raise ValueError("subject_vm device contract mismatch")
        storage = SubjectVMStorage.from_snapshot(
            cfg, entity_capacity, payload["storage"]
        )
        storage.validate_owners(alive, entity_ids, subject_ids)
        accounting_raw = payload.get("activation_accounting", {})
        activation_accounting = SubjectVMActivationAccounting(
            **{
                key: int(accounting_raw.get(key, default))
                for key, default in asdict(SubjectVMActivationAccounting()).items()
            }
        )
        trace_storage = None
        trace_accounting = SubjectVMTraceAccounting()
        eligibility_accounting = SubjectVMEligibilityAccounting()
        restore_mode = str(payload.get("restore_mode", "checkpoint-restored"))
        if cfg.trace_enabled:
            if compatibility_empty_trace:
                trace_storage = SubjectVMTraceStorage(cfg, entity_capacity)
                trace_storage.initialize_rows(rows)
                restore_mode = "compatibility-empty-token-trace-rebuild"
            else:
                trace_storage = SubjectVMTraceStorage.from_snapshot(
                    cfg, entity_capacity, payload["trace_storage"]
                )
                trace_raw = payload.get("trace_accounting", {})
                trace_accounting = SubjectVMTraceAccounting(
                    **{
                        key: int(trace_raw.get(key, default))
                        for key, default in asdict(SubjectVMTraceAccounting()).items()
                    }
                )
        if cfg.eligibility_enabled:
            if compatibility_empty_eligibility:
                restore_mode = (
                    "compatibility-empty-token-trace-and-local-eligibility-rebuild"
                    if compatibility_empty_trace
                    else "compatibility-empty-local-eligibility-rebuild"
                )
            else:
                eligibility_raw = payload.get("eligibility_accounting", {})
                eligibility_accounting = SubjectVMEligibilityAccounting(
                    **{
                        key: int(eligibility_raw.get(key, default))
                        for key, default in asdict(
                            SubjectVMEligibilityAccounting()
                        ).items()
                    }
                )
        if compatibility_empty_association:
            restore_mode = "compatibility-empty-delayed-association-rebuild"
        if compatibility_empty_modulation:
            restore_mode = "compatibility-empty-modulation-proposal-rebuild"
        if compatibility_empty_binding:
            restore_mode = "compatibility-empty-target-binding-rebuild"
        return cls(
            cfg,
            entity_capacity,
            storage,
            trace_storage=trace_storage,
            restore_mode=restore_mode,
            activation_accounting=activation_accounting,
            trace_accounting=trace_accounting,
            eligibility_accounting=eligibility_accounting,
        )

    def region_usage(self) -> tuple[SubjectVMRegionUsage, ...]:
        return () if self.storage is None else self.storage.region_usage()

    def diagnostics(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "activation_enabled": self.activation_enabled,
            "trace_enabled": self.trace_enabled,
            "eligibility_enabled": self.eligibility_enabled,
            "association_enabled": self.association_enabled,
            "modulation_enabled": self.modulation_enabled,
            "target_binding_enabled": self.target_binding_enabled,
            "restore_mode": self.restore_mode,
            "device_contract": self.device_contract.schema,
            "activation_accounting": asdict(self.activation_accounting),
            "trace_accounting": asdict(self.trace_accounting),
            "eligibility_accounting": asdict(self.eligibility_accounting),
            "trace_storage": (
                None if self.trace_storage is None else self.trace_storage.diagnostics()
            ),
            "regions": [asdict(value) for value in self.region_usage()],
        }

    def clone(self) -> "SubjectVMRuntime":
        if self._pending_thought_tokens is not None or self._pending_target_candidates is not None:
            raise RuntimeError("subject_vm cannot clone a partial activation phase")
        return type(self)(
            self.cfg,
            self.entity_capacity,
            None if self.storage is None else self.storage.clone(),
            trace_storage=(
                None if self.trace_storage is None else self.trace_storage.clone()
            ),
            restore_mode=self.restore_mode,
            activation_accounting=SubjectVMActivationAccounting(
                **asdict(self.activation_accounting)
            ),
            trace_accounting=SubjectVMTraceAccounting(**asdict(self.trace_accounting)),
            eligibility_accounting=SubjectVMEligibilityAccounting(
                **asdict(self.eligibility_accounting)
            ),
        )


__all__ = [
    "RUNTIME_SCHEMA",
    "RUNTIME_SCHEMA_V1",
    "RUNTIME_SCHEMA_V2",
    "RUNTIME_SCHEMA_V3",
    "RUNTIME_SCHEMA_V4",
    "RUNTIME_SCHEMA_V5",
    "RUNTIME_SCHEMA_V6",
    "STAGE1_DEVICE_CONTRACT",
    "STAGE2_DEVICE_CONTRACT",
    "STAGE3_DEVICE_CONTRACT",
    "STAGE3B_DEVICE_CONTRACT",
    "STAGE3B2_DEVICE_CONTRACT",
    "STAGE3B3_DEVICE_CONTRACT",
    "STAGE3C1_DEVICE_CONTRACT",
    "SubjectVMActivationAccounting",
    "SubjectVMDeviceContract",
    "SubjectVMEligibilityAccounting",
    "SubjectVMRuntime",
]
