"""Dynamic, costly knowledge copies and local consequence learning.

K1 establishes immutable content records, independently degradable holder
copies, explicit transfer plans, capacity arbitration, and auditable physical
costs.  K2 adds current-tick local context-action-outcome statistics and local
verification.  K3 may publish a separately versioned sparse policy residual;
the legacy ``inherited-linear-policy-v1`` coefficients retain their meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..backend import backend_from_array
from ..cfg import KnowledgeConfig, SimulationConfig
from ..random_api import RandomContext, Stream, bernoulli, uniform01


OUTCOME_WIDTH = 5
OUTCOME_ENERGY = 0
OUTCOME_INTEGRITY = 1
OUTCOME_MATERIAL = 2
OUTCOME_INFORMATION = 3
OUTCOME_REPRODUCTION_OPPORTUNITY = 4

OUTCOME_STATUS_FAILED = 0
OUTCOME_STATUS_SUCCESS = 1
OUTCOME_STATUS_PARTIAL = 2

ACQUISITION_SEED = 0
ACQUISITION_PRIVATE_EXPERIENCE = 1
ACQUISITION_TRANSFER = 2


def encode_local_context(
    resource: np.ndarray,
    hazard: np.ndarray,
    energy: np.ndarray,
    integrity: np.ndarray,
    grouped: np.ndarray,
    *,
    max_energy: float,
) -> np.ndarray:
    """Encode a small local observation into ``local-context-v1`` keys.

    The bins are deliberately coarse and use only the carrier's current local
    observation.  No future state, global fitness, or population statistic is
    available to this encoder.
    """
    xp = backend_from_array(resource).xp
    resource = xp.asarray(resource, dtype=xp.float32)
    hazard = xp.asarray(hazard, dtype=xp.float32)
    energy = xp.asarray(energy, dtype=xp.float32)
    integrity = xp.asarray(integrity, dtype=xp.float32)
    grouped = xp.asarray(grouped, dtype=bool)
    shape = resource.shape
    if any(value.shape != shape for value in (hazard, energy, integrity, grouped)):
        raise ValueError("local knowledge context inputs must align")
    resource_bin = xp.where(resource < 0.05, 0, xp.where(resource < 0.5, 1, 2))
    hazard_bin = xp.where(hazard < 0.25, 0, xp.where(hazard < 0.6, 1, 2))
    energy_fraction = energy / max(float(max_energy), 1e-12)
    energy_bin = xp.where(energy_fraction < 0.35, 0, xp.where(energy_fraction < 0.7, 1, 2))
    integrity_bin = xp.where(integrity < 0.5, 0, xp.where(integrity < 0.85, 1, 2))
    keys = (
        1
        + resource_bin
        + 3 * hazard_bin
        + 9 * energy_bin
        + 27 * integrity_bin
        + 81 * grouped.astype(xp.int16)
    )
    return keys.astype(xp.uint64, copy=False)


def _readonly(value: np.ndarray, dtype: Any | None = None) -> np.ndarray:
    result = np.asarray(value, dtype=dtype).copy()
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class KnowledgeObservationPlan:
    """Immutable holder-segmented knowledge snapshot published for one tick."""

    tick: int
    holder_subject_ids: np.ndarray
    holder_starts: np.ndarray
    holder_counts: np.ndarray
    copy_ids: np.ndarray
    content_ids: np.ndarray
    context_keys: np.ndarray
    action_ids: np.ndarray
    outcome_vectors: np.ndarray
    confidences: np.ndarray
    sample_counts: np.ndarray
    acquisition_kinds: np.ndarray
    encoded_bytes: np.ndarray

    @classmethod
    def empty(cls, tick: int = 0) -> "KnowledgeObservationPlan":
        return cls(
            tick=int(tick),
            holder_subject_ids=_readonly(np.empty(0), np.uint64),
            holder_starts=_readonly(np.empty(0), np.int32),
            holder_counts=_readonly(np.empty(0), np.int32),
            copy_ids=_readonly(np.empty(0), np.uint64),
            content_ids=_readonly(np.empty(0), np.uint64),
            context_keys=_readonly(np.empty(0), np.uint64),
            action_ids=_readonly(np.empty(0), np.int16),
            outcome_vectors=_readonly(np.empty((0, OUTCOME_WIDTH)), np.float32),
            confidences=_readonly(np.empty(0), np.float32),
            sample_counts=_readonly(np.empty(0), np.uint32),
            acquisition_kinds=_readonly(np.empty(0), np.uint8),
            encoded_bytes=_readonly(np.empty(0), np.uint32),
        )

    @property
    def copy_count(self) -> int:
        return int(self.copy_ids.size)


@dataclass(frozen=True)
class KnowledgeOutcomePlan:
    """Immutable local action consequence records for one completed commit.

    Outcome coordinates are ordered as energy, integrity, material/resource,
    information, and reproduction opportunity.  The plan contains no scalar
    reward and is generated only from the current tick's observation and
    committed physical state.
    """

    tick: int
    carrier_indices: np.ndarray
    entity_ids: np.ndarray
    holder_subject_ids: np.ndarray
    context_keys: np.ndarray
    action_ids: np.ndarray
    statuses: np.ndarray
    failure_reasons: np.ndarray
    outcome_vectors: np.ndarray

    @classmethod
    def empty(cls, tick: int = 0) -> "KnowledgeOutcomePlan":
        return cls(
            tick=int(tick),
            carrier_indices=np.empty(0, dtype=np.int32),
            entity_ids=np.empty(0, dtype=np.uint64),
            holder_subject_ids=np.empty(0, dtype=np.uint64),
            context_keys=np.empty(0, dtype=np.uint64),
            action_ids=np.empty(0, dtype=np.int16),
            statuses=np.empty(0, dtype=np.uint8),
            failure_reasons=np.empty(0, dtype=np.uint8),
            outcome_vectors=np.empty((0, OUTCOME_WIDTH), dtype=np.float32),
        )

    @property
    def size(self) -> int:
        return int(self.entity_ids.size)

    def validate(self, entity_capacity: int) -> None:
        count = self.size
        vectors = (
            self.carrier_indices,
            self.entity_ids,
            self.holder_subject_ids,
            self.context_keys,
            self.action_ids,
            self.statuses,
            self.failure_reasons,
        )
        if any(np.asarray(value).shape != (count,) for value in vectors):
            raise ValueError("knowledge outcome plan vectors must align")
        if np.asarray(self.outcome_vectors).shape != (count, OUTCOME_WIDTH):
            raise ValueError("knowledge outcome vectors must have width five")
        if self.tick < 0:
            raise ValueError("knowledge outcome tick must be non-negative")
        if count and (
            np.any(self.carrier_indices < 0)
            or np.any(self.carrier_indices >= entity_capacity)
            or np.any(self.entity_ids == 0)
            or np.any(self.holder_subject_ids == 0)
            or np.any(self.context_keys == 0)
            or np.any(self.action_ids < 0)
            or np.any(self.statuses > OUTCOME_STATUS_PARTIAL)
            or np.any(~np.isfinite(self.outcome_vectors))
        ):
            raise ValueError("knowledge outcome plan contains invalid values")


@dataclass(frozen=True)
class KnowledgeTransferPlan:
    """Explicit transfer attempts produced before any knowledge state mutation."""

    tick: int
    sender_entity_indices: np.ndarray
    receiver_entity_indices: np.ndarray
    sender_subject_ids: np.ndarray
    receiver_subject_ids: np.ndarray
    source_subject_ids: np.ndarray
    source_copy_ids: np.ndarray
    content_ids: np.ndarray
    encoded_bytes: np.ndarray
    delivered: np.ndarray
    corrupted: np.ndarray
    source_outcome_vectors: np.ndarray = field(
        default_factory=lambda: np.empty((0, OUTCOME_WIDTH), dtype=np.float32)
    )
    source_confidences: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.float32)
    )
    source_sample_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    attention_rejected: int = 0

    @classmethod
    def empty(
        cls, tick: int, attention_rejected: int = 0
    ) -> "KnowledgeTransferPlan":
        return cls(
            tick=int(tick),
            sender_entity_indices=np.empty(0, dtype=np.int32),
            receiver_entity_indices=np.empty(0, dtype=np.int32),
            sender_subject_ids=np.empty(0, dtype=np.uint64),
            receiver_subject_ids=np.empty(0, dtype=np.uint64),
            source_subject_ids=np.empty(0, dtype=np.uint64),
            source_copy_ids=np.empty(0, dtype=np.uint64),
            content_ids=np.empty(0, dtype=np.uint64),
            source_outcome_vectors=np.empty((0, OUTCOME_WIDTH), dtype=np.float32),
            source_confidences=np.empty(0, dtype=np.float32),
            source_sample_counts=np.empty(0, dtype=np.uint32),
            encoded_bytes=np.empty(0, dtype=np.uint32),
            delivered=np.empty(0, dtype=bool),
            corrupted=np.empty(0, dtype=bool),
            attention_rejected=int(attention_rejected),
        )

    @property
    def size(self) -> int:
        return int(self.source_copy_ids.size)

    def validate(self, entity_capacity: int) -> None:
        count = self.size
        vectors = (
            self.sender_entity_indices,
            self.receiver_entity_indices,
            self.sender_subject_ids,
            self.receiver_subject_ids,
            self.source_subject_ids,
            self.source_copy_ids,
            self.content_ids,
            self.encoded_bytes,
            self.delivered,
            self.corrupted,
        )
        if any(np.asarray(value).shape != (count,) for value in vectors):
            raise ValueError("knowledge transfer plan vectors must align")
        legacy_source_state = (
            np.asarray(self.source_outcome_vectors).size == 0
            and np.asarray(self.source_confidences).size == 0
            and np.asarray(self.source_sample_counts).size == 0
        )
        if not legacy_source_state and (
            np.asarray(self.source_outcome_vectors).shape != (count, OUTCOME_WIDTH)
            or np.asarray(self.source_confidences).shape != (count,)
            or np.asarray(self.source_sample_counts).shape != (count,)
        ):
            raise ValueError("knowledge transfer source-state vectors must align")
        if self.tick < 0 or self.attention_rejected < 0:
            raise ValueError("knowledge transfer tick/attention count is invalid")
        if count and (
            np.any(self.sender_entity_indices < 0)
            or np.any(self.sender_entity_indices >= entity_capacity)
            or np.any(self.receiver_entity_indices < 0)
            or np.any(self.receiver_entity_indices >= entity_capacity)
            or np.any(self.sender_subject_ids == 0)
            or np.any(self.receiver_subject_ids == 0)
            or np.any(self.source_copy_ids == 0)
            or np.any(self.content_ids == 0)
            or np.any(self.encoded_bytes == 0)
            or np.any(self.corrupted & ~self.delivered)
            or (
                not legacy_source_state
                and (
                    np.any(~np.isfinite(self.source_outcome_vectors))
                    or np.any(~np.isfinite(self.source_confidences))
                    or np.any(
                        (self.source_confidences < 0.0)
                        | (self.source_confidences > 1.0)
                    )
                )
            )
        ):
            raise ValueError("knowledge transfer plan contains invalid values")


@dataclass(frozen=True)
class KnowledgeTransferCommitAudit:
    """Successful transfer rows published for observational diagnostics only."""

    tick: int
    sender_entity_indices: np.ndarray
    receiver_entity_indices: np.ndarray
    committed_content_ids: np.ndarray
    committed_root_ids: np.ndarray
    committed_bytes: np.ndarray

    @classmethod
    def empty(cls, tick: int = 0) -> "KnowledgeTransferCommitAudit":
        return cls(
            tick=int(tick),
            sender_entity_indices=np.empty(0, dtype=np.int32),
            receiver_entity_indices=np.empty(0, dtype=np.int32),
            committed_content_ids=np.empty(0, dtype=np.uint64),
            committed_root_ids=np.empty(0, dtype=np.uint64),
            committed_bytes=np.empty(0, dtype=np.uint32),
        )

    @property
    def size(self) -> int:
        return int(self.committed_content_ids.size)


@dataclass
class KnowledgeStepStats:
    maintenance_energy: float = 0.0
    sender_energy: float = 0.0
    receiver_energy: float = 0.0
    transfer_attempts: int = 0
    transfer_delivered: int = 0
    transfer_lost: int = 0
    transfer_corrupted: int = 0
    transfer_committed: int = 0
    transfer_committed_bytes: int = 0
    transfer_same_lineage_committed: int = 0
    transfer_cross_lineage_committed: int = 0
    transfer_unknown_lineage_committed: int = 0
    transfer_same_group_committed: int = 0
    transfer_cross_group_committed: int = 0
    transfer_unknown_group_committed: int = 0
    transfer_duplicate_rejected: int = 0
    transfer_capacity_rejected: int = 0
    transfer_energy_rejected: int = 0
    attention_rejected: int = 0
    forgotten: int = 0
    evicted_capacity: int = 0
    evicted_maintenance: int = 0
    removed_dead_holder: int = 0
    learning_energy: float = 0.0
    outcome_records: int = 0
    outcome_success: int = 0
    outcome_failed: int = 0
    outcome_partial: int = 0
    outcome_updates: int = 0
    private_experiences_created: int = 0
    private_experience_updates: int = 0
    transferred_copies_verified: int = 0
    outcome_unmatched: int = 0
    learning_energy_rejected: int = 0
    learning_capacity_rejected: int = 0
    learning_match_limit_skipped: int = 0
    confidence_decayed: int = 0
    policy_influenced_entities: int = 0
    policy_influenced_actions: int = 0
    policy_support_copies: int = 0
    policy_private_support_copies: int = 0
    policy_transfer_support_copies: int = 0
    policy_unverified_transfer_support_copies: int = 0
    policy_changed_actions: int = 0
    policy_residual_abs_sum: float = 0.0
    policy_latent_dimensions: int = 0
    policy_latent_max_width: int = 0
    policy_quantized_residual_abs_sum: int = 0
    policy_linear_shadow_changed_actions: int = 0
    policy_router_saturation_units: int = 0
    policy_router_clipped_outputs: int = 0
    policy_router_hidden_abs_sum: int = 0
    policy_router_hidden_active_units: int = 0
    routing_requested_energy: float = 0.0
    routing_committed_energy: float = 0.0
    routing_rejected_energy: float = 0.0
    routing_requested_entities: int = 0
    routing_committed_entities: int = 0
    routing_rejected_entities: int = 0
    routing_accepted_actions: int = 0
    routing_rejected_actions: int = 0
    routing_latent_dimensions: int = 0
    routing_mac_count: int = 0
    routing_active_hidden_units: int = 0
    routing_saturation_count: int = 0
    routing_clipped_output_count: int = 0
    routing_cost_induced_action_changes: int = 0
    selection_candidate_copies: int = 0
    selection_selected_copies: int = 0
    selection_requested_top_k_sum: int = 0
    selection_zero_capacity_entities: int = 0
    selection_tie_count: int = 0
    selection_committed_energy: float = 0.0
    working_memory_requested_energy: float = 0.0
    working_memory_committed_energy: float = 0.0
    working_memory_rejected_energy: float = 0.0
    working_memory_requested_entities: int = 0
    working_memory_committed_entities: int = 0
    working_memory_rejected_entities: int = 0
    working_memory_saturation_units: int = 0
    working_memory_active_dimensions: int = 0
    working_memory_induced_action_changes: int = 0

    @property
    def total_energy_cost(self) -> float:
        return (
            self.maintenance_energy
            + self.sender_energy
            + self.receiver_energy
            + self.learning_energy
            + self.routing_committed_energy
            + self.working_memory_committed_energy
        )


__all__ = [
    "KnowledgeObservationPlan", "KnowledgeOutcomePlan", "KnowledgeTransferPlan",
    "KnowledgeTransferCommitAudit", "KnowledgeStepStats", "encode_local_context",
    "OUTCOME_WIDTH", "OUTCOME_ENERGY", "OUTCOME_INTEGRITY", "OUTCOME_MATERIAL",
    "OUTCOME_INFORMATION", "OUTCOME_REPRODUCTION_OPPORTUNITY",
    "OUTCOME_STATUS_FAILED", "OUTCOME_STATUS_SUCCESS", "OUTCOME_STATUS_PARTIAL",
    "ACQUISITION_SEED", "ACQUISITION_PRIVATE_EXPERIENCE", "ACQUISITION_TRANSFER",
]
