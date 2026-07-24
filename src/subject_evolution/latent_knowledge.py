"""Variable-length latent knowledge and an evolvable quantized router.

This module implements the first high-extensibility latent-knowledge schema.
Knowledge contents own variable-length int16 latent payloads selected from a
small set of length levels.  Per-carrier inherited router weights map those payloads and current local carrier
state to the existing public action-logit residual boundary.  L1 uses a linear
router; L2 retains that router as a shadow prefix and adds a quantized two-layer
MLP with an exact integer hard-tanh activation.

The publish boundary is deliberately quantized.  Per-copy routing can run in
NumPy or CuPy using exact integer arithmetic; the final holder/action
aggregation is performed in the stable CPU reference order.  This preserves a
clear CPU/GPU parity contract without requiring latent dimensions to carry
hand-authored natural-language meanings.
"""

from __future__ import annotations

from dataclasses import dataclass
import copy
from typing import Any, Iterable

import numpy as np

from .backend import backend_from_array, to_numpy
from .config import KnowledgeConfig, SimulationConfig
from .knowledge import (
    ACQUISITION_PRIVATE_EXPERIENCE,
    ACQUISITION_TRANSFER,
    KnowledgeObservationPlan,
    OUTCOME_WIDTH,
)


LATENT_SCHEMA = "variable-latent-knowledge-v1"
LATENT_ROUTER_SCHEMA = "quantized-linear-latent-router-v1"
LATENT_MLP_ROUTER_SCHEMA = "quantized-mlp-latent-router-v1"
LATENT_POLICY_RESIDUAL_SCHEMA = "quantized-variable-latent-residual-v1"
LATENT_MLP_POLICY_RESIDUAL_SCHEMA = "quantized-variable-latent-mlp-residual-v1"
LATENT_STATE_WIDTH = 4
LATENT_ROUTER_METADATA_WIDTH = 3


def _mix_scalar(value: int) -> int:
    """SplitMix64 finalizer for deterministic scalar metadata generation."""
    mask = (1 << 64) - 1
    value = (int(value) + 0x9E3779B97F4A7C15) & mask
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & mask
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & mask
    return value ^ (value >> 31)


def _signed_hash(*values: int) -> int:
    key = 0xD1B54A32D192ED03
    for index, value in enumerate(values):
        key ^= _mix_scalar(int(value) + index * 0x9E3779B97F4A7C15)
        key = _mix_scalar(key)
    return 1 if (key & 1) else -1


def _round_divide_signed_numpy(numerator: np.ndarray, denominator: int | np.ndarray) -> np.ndarray:
    """Round signed integers to nearest, ties away from zero."""
    num = np.asarray(numerator, dtype=np.int64)
    den = np.asarray(denominator, dtype=np.int64)
    if np.any(den <= 0):
        raise ValueError("integer quantization denominator must be positive")
    magnitude = (np.abs(num) + den // 2) // den
    return np.where(num < 0, -magnitude, magnitude).astype(np.int64, copy=False)


def _round_divide_signed_backend(numerator: Any, denominator: int | Any, xp: Any) -> Any:
    """Backend-neutral signed integer rounding with exact CPU/GPU semantics."""
    num = xp.asarray(numerator, dtype=xp.int64)
    den = xp.asarray(denominator, dtype=xp.int64)
    magnitude = (xp.abs(num) + den // xp.int64(2)) // den
    return xp.where(num < 0, -magnitude, magnitude).astype(xp.int64, copy=False)


def _projection_matrix(width: int, hidden_width: int) -> np.ndarray:
    result = np.empty((int(width), int(hidden_width)), dtype=np.int8)
    for dimension in range(int(width)):
        for hidden in range(int(hidden_width)):
            result[dimension, hidden] = np.int8(
                _signed_hash(0x4C4154454E54, width, dimension, hidden)
            )
    return result


def _outcome_projection(hidden_width: int) -> np.ndarray:
    result = np.empty((OUTCOME_WIDTH, int(hidden_width)), dtype=np.int8)
    for outcome in range(OUTCOME_WIDTH):
        for hidden in range(int(hidden_width)):
            result[outcome, hidden] = np.int8(
                _signed_hash(0x4F5554434F4D45, outcome, hidden)
            )
    return result


class VariableLatentContentStore:
    """Append-only variable-length latent payload arena keyed by content ID.

    The existing knowledge catalog remains the authoritative semantic directory.
    This store is a separately versioned representation layer and can therefore
    be disabled without changing any K1--K4 state or archived experiment.
    """

    def __init__(self, config: KnowledgeConfig, run_seed: int) -> None:
        self.schema = LATENT_SCHEMA
        self.run_seed = int(run_seed)
        self.length_levels = tuple(int(value) for value in config.latent_length_levels)
        self.quantization_scale = int(config.latent_value_quantization_scale)
        self.hidden_width = int(config.latent_router_hidden_width)
        self.base_encoded_bytes = int(config.latent_base_encoded_bytes)
        self.bytes_per_value = int(config.latent_bytes_per_value)
        self.length_mutation_probability = float(
            config.latent_length_mutation_probability
        )
        self._size = 0
        self._capacity = 64
        self.length = np.zeros(self._capacity, dtype=np.uint16)
        self.offset = np.zeros(self._capacity, dtype=np.uint64)
        self._value_size = 0
        self._value_capacity = 256
        self.values = np.zeros(self._value_capacity, dtype=np.int16)

    @property
    def size(self) -> int:
        return self._size

    @property
    def total_dimensions(self) -> int:
        return int(self._value_size)

    def clone(self) -> "VariableLatentContentStore":
        return copy.deepcopy(self)

    def _ensure_content_capacity(self, required: int) -> None:
        if required <= self._capacity:
            return
        new_capacity = self._capacity
        while new_capacity < required:
            new_capacity *= 2
        for name in ("length", "offset"):
            old = getattr(self, name)
            expanded = np.zeros(new_capacity, dtype=old.dtype)
            expanded[: self._size] = old[: self._size]
            setattr(self, name, expanded)
        self._capacity = new_capacity

    def _ensure_value_capacity(self, required: int) -> None:
        if required <= self._value_capacity:
            return
        new_capacity = self._value_capacity
        while new_capacity < required:
            new_capacity *= 2
        expanded = np.zeros(new_capacity, dtype=np.int16)
        expanded[: self._value_size] = self.values[: self._value_size]
        self.values = expanded
        self._value_capacity = new_capacity

    def _root_length(
        self,
        *,
        content_id: int,
        context_key: int,
        action_id: int,
        source_subject_id: int,
    ) -> int:
        key = _mix_scalar(
            self.run_seed
            ^ (int(content_id) * 0x9E3779B97F4A7C15)
            ^ (int(context_key) * 0xBF58476D1CE4E5B9)
            ^ ((int(action_id) + 17) * 0x94D049BB133111EB)
            ^ int(source_subject_id)
        )
        return int(self.length_levels[key % len(self.length_levels)])

    def preview_length(
        self,
        *,
        content_id: int,
        parent_content_id: int,
        context_key: int,
        action_id: int,
        source_subject_id: int,
    ) -> int:
        if parent_content_id > 0 and parent_content_id <= self._size:
            parent_length = int(self.length[parent_content_id - 1])
            if len(self.length_levels) <= 1 or self.length_mutation_probability <= 0.0:
                return parent_length
            key = _mix_scalar(
                self.run_seed
                ^ (int(content_id) * 0xD1342543DE82EF95)
                ^ (int(parent_content_id) * 0xA24BAED4963EE407)
            )
            unit = ((key >> 11) & ((1 << 53) - 1)) / float(1 << 53)
            if unit >= self.length_mutation_probability:
                return parent_length
            index = self.length_levels.index(parent_length)
            if index == 0:
                index = 1
            elif index == len(self.length_levels) - 1:
                index -= 1
            else:
                index += 1 if (key & 1) else -1
            return int(self.length_levels[index])
        return self._root_length(
            content_id=content_id,
            context_key=context_key,
            action_id=action_id,
            source_subject_id=source_subject_id,
        )

    def encoded_bytes_for_length(self, length: int) -> int:
        return int(self.base_encoded_bytes + int(length) * self.bytes_per_value)

    def encoded_bytes_for_next(
        self,
        *,
        parent_content_id: int,
        context_key: int,
        action_id: int,
        source_subject_id: int,
    ) -> int:
        length = self.preview_length(
            content_id=self._size + 1,
            parent_content_id=parent_content_id,
            context_key=context_key,
            action_id=action_id,
            source_subject_id=source_subject_id,
        )
        return self.encoded_bytes_for_length(length)

    def _root_values(
        self,
        *,
        content_id: int,
        length: int,
        context_key: int,
        action_id: int,
        source_subject_id: int,
        outcome_vector: np.ndarray,
    ) -> np.ndarray:
        scales = max(self.quantization_scale, 1)
        outcome = np.clip(np.asarray(outcome_vector, dtype=np.float64), -2.0, 2.0)
        result = np.empty(length, dtype=np.int16)
        for dimension in range(length):
            random_key = _mix_scalar(
                self.run_seed
                ^ (content_id * 0xD1342543DE82EF95)
                ^ (dimension * 0xA24BAED4963EE407)
                ^ int(context_key)
                ^ (int(source_subject_id) << 1)
            )
            random_component = ((random_key >> 16) & 0xFFFF) / 65535.0 - 0.5
            outcome_component = 0.0
            for coordinate in range(OUTCOME_WIDTH):
                outcome_component += (
                    float(outcome[coordinate])
                    * _signed_hash(0x4F555443, dimension, coordinate)
                )
            outcome_component /= float(OUTCOME_WIDTH)
            action_component = 0.125 * _signed_hash(0x41435449, dimension, action_id)
            context_component = 0.125 * _signed_hash(0x434F4E54, dimension, context_key)
            value = (
                0.45 * random_component
                + 0.30 * outcome_component
                + action_component
                + context_component
            )
            result[dimension] = np.int16(
                np.clip(np.rint(value * scales), -32767, 32767)
            )
        return result

    def _variant_values(
        self,
        *,
        content_id: int,
        parent_content_id: int,
        target_length: int,
    ) -> np.ndarray:
        parent = self.vector(parent_content_id)
        result = np.zeros(int(target_length), dtype=np.int16)
        shared = min(parent.size, result.size)
        result[:shared] = parent[:shared]
        # Length expansion creates deterministic new coordinates rather than
        # free zero capacity.  Contraction preserves the canonical prefix.
        for dimension in range(shared, result.size):
            key = _mix_scalar(
                self.run_seed
                ^ (content_id * 0xD1342543DE82EF95)
                ^ (parent_content_id * 0xA24BAED4963EE407)
                ^ dimension
            )
            centered = int((key >> 16) & 0xFFFF) - 32768
            result[dimension] = np.int16(
                np.clip(centered // 16, -32767, 32767)
            )
        if result.size == 0:
            return result
        key = _mix_scalar(self.run_seed ^ content_id ^ (parent_content_id << 17))
        mutation_count = 1 + int((key >> 8) % min(3, result.size))
        for mutation in range(mutation_count):
            coordinate = int(_mix_scalar(key + mutation) % result.size)
            signed = _signed_hash(content_id, parent_content_id, mutation)
            delta = signed * max(self.quantization_scale // 16, 1)
            result[coordinate] = np.int16(
                np.clip(int(result[coordinate]) + delta, -32767, 32767)
            )
        return result

    def ensure_catalog(self, catalog: Any) -> None:
        """Append latent records for all newly created catalog contents."""
        while self._size < int(catalog.size):
            row = self._size
            content_id = int(catalog.content_id[row])
            parent_content_id = int(catalog.parent_content_id[row])
            length = self.preview_length(
                content_id=content_id,
                parent_content_id=parent_content_id,
                context_key=int(catalog.context_key[row]),
                action_id=int(catalog.action_id[row]),
                source_subject_id=int(catalog.source_subject_id[row]),
            )
            if parent_content_id > 0:
                vector = self._variant_values(
                    content_id=content_id,
                    parent_content_id=parent_content_id,
                    target_length=length,
                )
            else:
                vector = self._root_values(
                    content_id=content_id,
                    length=length,
                    context_key=int(catalog.context_key[row]),
                    action_id=int(catalog.action_id[row]),
                    source_subject_id=int(catalog.source_subject_id[row]),
                    outcome_vector=catalog.outcome_vector[row],
                )
            if vector.size != length:
                raise ValueError("latent content vector length does not match its level")
            self._ensure_content_capacity(self._size + 1)
            self._ensure_value_capacity(self._value_size + length)
            self.offset[row] = np.uint64(self._value_size)
            self.length[row] = np.uint16(length)
            self.values[self._value_size : self._value_size + length] = vector
            self._value_size += length
            self._size += 1
            # Dynamic payload bytes are authoritative for future copies.  This
            # update does not alter K1--K4 schemas because the latent store is
            # only created for the separately gated latent schema.
            catalog.encoded_bytes[row] = np.uint32(self.encoded_bytes_for_length(length))

    def vector(self, content_id: int) -> np.ndarray:
        row = int(content_id) - 1
        if row < 0 or row >= self._size:
            raise KeyError(f"latent content {content_id} has not been published")
        start = int(self.offset[row])
        length = int(self.length[row])
        return self.values[start : start + length]

    def arrays(self) -> dict[str, np.ndarray]:
        return {
            "length": self.length[: self._size].copy(),
            "offset": self.offset[: self._size].copy(),
            "values": self.values[: self._value_size].copy(),
        }

    def summary(self) -> dict[str, int | float | str]:
        if self._size == 0:
            mean_length = 0.0
            max_length = 0
        else:
            mean_length = float(self.length[: self._size].mean())
            max_length = int(self.length[: self._size].max())
        return {
            "latent_schema": self.schema,
            "latent_content_count": self._size,
            "latent_total_dimensions": self._value_size,
            "latent_mean_dimensions": mean_length,
            "latent_max_dimensions": max_length,
            "latent_length_mutation_probability": self.length_mutation_probability,
        }


@dataclass(frozen=True)
class LatentBucket:
    width: int
    batch_rows: np.ndarray
    values: np.ndarray


@dataclass(frozen=True)
class LatentRouterBatch:
    """Matched copy batch with variable payloads grouped into width buckets."""

    tick: int
    active_count: int
    copy_active_rows: np.ndarray
    copy_ids: np.ndarray
    content_ids: np.ndarray
    entity_ids: np.ndarray
    holder_subject_ids: np.ndarray
    context_keys: np.ndarray
    acquisition_kinds: np.ndarray
    unverified_transfer: np.ndarray
    reliability_q: np.ndarray
    outcome_vectors: np.ndarray
    outcome_q: np.ndarray
    latent_lengths: np.ndarray
    buckets: tuple[LatentBucket, ...]

    @classmethod
    def empty(cls, tick: int, active_count: int = 0) -> "LatentRouterBatch":
        return cls(
            tick=int(tick),
            active_count=int(active_count),
            copy_active_rows=np.empty(0, dtype=np.int32),
            copy_ids=np.empty(0, dtype=np.uint64),
            content_ids=np.empty(0, dtype=np.uint64),
            entity_ids=np.empty(0, dtype=np.uint64),
            holder_subject_ids=np.empty(0, dtype=np.uint64),
            context_keys=np.empty(0, dtype=np.uint64),
            acquisition_kinds=np.empty(0, dtype=np.uint8),
            unverified_transfer=np.empty(0, dtype=bool),
            reliability_q=np.empty(0, dtype=np.int32),
            outcome_vectors=np.empty((0, OUTCOME_WIDTH), dtype=np.float32),
            outcome_q=np.empty((0, OUTCOME_WIDTH), dtype=np.int32),
            latent_lengths=np.empty(0, dtype=np.uint16),
            buckets=(),
        )

    @property
    def size(self) -> int:
        return int(self.copy_ids.size)

    @property
    def semantic_transfer_nbytes(self) -> int:
        return int(
            self.copy_active_rows.nbytes
            + self.reliability_q.nbytes
            + self.outcome_vectors.nbytes
            + self.outcome_q.nbytes
            + sum(bucket.batch_rows.nbytes + bucket.values.nbytes for bucket in self.buckets)
        )

    def validate(self, length_levels: Iterable[int]) -> None:
        count = self.size
        vectors = (
            self.copy_active_rows,
            self.copy_ids,
            self.content_ids,
            self.entity_ids,
            self.holder_subject_ids,
            self.context_keys,
            self.acquisition_kinds,
            self.unverified_transfer,
            self.reliability_q,
            self.latent_lengths,
        )
        if any(np.asarray(value).shape != (count,) for value in vectors):
            raise ValueError("latent router batch vectors must align")
        if self.outcome_vectors.shape != (count, OUTCOME_WIDTH):
            raise ValueError("latent router outcomes must have width five")
        if self.outcome_q.shape != (count, OUTCOME_WIDTH) or self.outcome_q.dtype != np.int32:
            raise ValueError("latent router quantized outcomes must be int32 width-five vectors")
        if count and (
            np.any(self.copy_active_rows < 0)
            or np.any(self.copy_active_rows >= self.active_count)
            or np.any(self.copy_ids == 0)
            or np.any(self.entity_ids == 0)
            or np.any(self.holder_subject_ids == 0)
            or np.any(self.context_keys == 0)
            or np.any(self.reliability_q <= 0)
        ):
            raise ValueError("latent router batch contains invalid values")
        allowed = set(int(value) for value in length_levels)
        covered: list[np.ndarray] = []
        for bucket in self.buckets:
            if bucket.width not in allowed:
                raise ValueError("latent bucket width is not configured")
            if bucket.batch_rows.ndim != 1 or bucket.values.shape != (
                bucket.batch_rows.size,
                bucket.width,
            ):
                raise ValueError("latent bucket matrix is malformed")
            if bucket.batch_rows.size:
                if np.any(bucket.batch_rows < 0) or np.any(bucket.batch_rows >= count):
                    raise ValueError("latent bucket row is out of range")
                covered.append(bucket.batch_rows)
        if count:
            merged = np.concatenate(covered) if covered else np.empty(0, dtype=np.int32)
            if not np.array_equal(np.sort(merged), np.arange(count, dtype=np.int32)):
                raise ValueError("latent buckets must cover each matched copy once")


def _copy_reliability(
    observation: KnowledgeObservationPlan,
    rows: np.ndarray,
    config: KnowledgeConfig,
) -> tuple[np.ndarray, np.ndarray]:
    samples = observation.sample_counts[rows].astype(np.float64)
    confidence = observation.confidences[rows].astype(np.float64)
    acquisition = observation.acquisition_kinds[rows]
    saturation = max(float(config.policy_sample_saturation), 1e-12)
    locally_verified = samples >= float(config.policy_min_local_samples)
    local_evidence = samples / (samples + saturation)
    unverified_transfer = (acquisition == ACQUISITION_TRANSFER) & ~locally_verified
    evidence = np.where(
        locally_verified,
        local_evidence,
        np.where(
            unverified_transfer,
            float(config.policy_unverified_transfer_weight),
            0.0,
        ),
    )
    reliability = confidence * evidence
    scale = int(config.latent_value_quantization_scale)
    return (
        np.clip(np.rint(reliability * scale), 0, scale).astype(np.int32),
        unverified_transfer.astype(bool, copy=False),
    )


def build_latent_router_batch(
    observation: KnowledgeObservationPlan,
    store: VariableLatentContentStore,
    *,
    tick: int,
    entity_ids: np.ndarray,
    holder_subject_ids: np.ndarray,
    context_keys: np.ndarray,
    config: KnowledgeConfig,
) -> LatentRouterBatch:
    """Match holder copies and materialize variable-length width buckets."""
    ids = np.asarray(entity_ids, dtype=np.uint64)
    holders = np.asarray(holder_subject_ids, dtype=np.uint64)
    contexts = np.asarray(context_keys, dtype=np.uint64)
    active_count = ids.size
    if holders.shape != (active_count,) or contexts.shape != (active_count,):
        raise ValueError("latent router holder and context arrays must align")
    if active_count == 0 or observation.copy_count == 0:
        return LatentRouterBatch.empty(tick, active_count)

    copy_holders = np.repeat(
        observation.holder_subject_ids,
        observation.holder_counts.astype(np.int64, copy=False),
    )
    holder_order = np.argsort(holders, kind="stable")
    sorted_holders = holders[holder_order]
    positions = np.searchsorted(sorted_holders, copy_holders)
    in_range = positions < sorted_holders.size
    safe = np.minimum(positions, max(sorted_holders.size - 1, 0))
    matched = in_range & (sorted_holders[safe] == copy_holders)
    if not np.any(matched):
        return LatentRouterBatch.empty(tick, active_count)
    observation_rows = np.flatnonzero(matched)
    active_rows = holder_order[positions[observation_rows]].astype(np.int32, copy=False)
    valid = (
        (observation.context_keys[observation_rows] == contexts[active_rows])
        & (observation.confidences[observation_rows] >= float(config.policy_min_confidence))
    )
    observation_rows = observation_rows[valid]
    active_rows = active_rows[valid]
    if observation_rows.size == 0:
        return LatentRouterBatch.empty(tick, active_count)
    reliability_q, unverified_transfer = _copy_reliability(observation, observation_rows, config)
    keep = reliability_q > 0
    observation_rows = observation_rows[keep]
    active_rows = active_rows[keep]
    reliability_q = reliability_q[keep]
    unverified_transfer = unverified_transfer[keep]
    if observation_rows.size == 0:
        return LatentRouterBatch.empty(tick, active_count)

    content_ids = observation.content_ids[observation_rows].astype(np.uint64, copy=False)
    lengths = store.length[content_ids.astype(np.int64) - 1].astype(np.uint16, copy=True)
    buckets: list[LatentBucket] = []
    for width in store.length_levels:
        batch_rows = np.flatnonzero(lengths == width).astype(np.int32, copy=False)
        if batch_rows.size == 0:
            continue
        matrix = np.empty((batch_rows.size, width), dtype=np.int16)
        for target, batch_row in enumerate(batch_rows):
            matrix[target] = store.vector(int(content_ids[batch_row]))
        buckets.append(LatentBucket(int(width), batch_rows.copy(), matrix))

    outcome_vectors = observation.outcome_vectors[observation_rows].astype(np.float32, copy=True)
    scales = np.asarray(config.policy_outcome_scales, dtype=np.float32)
    normalized = np.clip(
        outcome_vectors / scales[None, :],
        -float(config.policy_outcome_clip),
        float(config.policy_outcome_clip),
    )
    q = int(config.latent_value_quantization_scale)
    outcome_q = np.rint(normalized * q).astype(np.int32)
    batch = LatentRouterBatch(
        tick=int(tick),
        active_count=active_count,
        copy_active_rows=active_rows.copy(),
        copy_ids=observation.copy_ids[observation_rows].copy(),
        content_ids=content_ids.copy(),
        entity_ids=ids[active_rows].copy(),
        holder_subject_ids=holders[active_rows].copy(),
        context_keys=contexts[active_rows].copy(),
        acquisition_kinds=observation.acquisition_kinds[observation_rows].copy(),
        unverified_transfer=unverified_transfer.copy(),
        reliability_q=reliability_q,
        outcome_vectors=outcome_vectors,
        outcome_q=outcome_q,
        latent_lengths=lengths,
        buckets=tuple(buckets),
    )
    batch.validate(store.length_levels)
    return batch


def latent_router_state_features(
    *,
    energy: Any,
    integrity: Any,
    fertility: Any,
    local_resource: Any,
    max_energy: float,
    resource_capacity: float,
) -> Any:
    """Return the four public local state coordinates consumed by the router."""
    xp = backend_from_array(energy).xp
    e = xp.clip(xp.asarray(energy, dtype=xp.float32) / max(float(max_energy), 1e-12), 0.0, 1.5)
    health = xp.clip(xp.asarray(integrity, dtype=xp.float32), 0.0, 1.0)
    fert = xp.clip(xp.asarray(fertility, dtype=xp.float32), 0.0, 2.0)
    scarcity = 1.0 - xp.clip(
        xp.asarray(local_resource, dtype=xp.float32) / max(float(resource_capacity), 1e-12),
        0.0,
        1.0,
    )
    return xp.stack((e, health, fert, scarcity), axis=1).astype(xp.float32, copy=False)


def _linear_router_gene_layout(
    config: KnowledgeConfig, action_count: int
) -> tuple[int, int, int, int]:
    hidden = int(config.latent_router_hidden_width)
    latent_count = action_count * hidden
    state_count = action_count * LATENT_STATE_WIDTH
    bias_count = action_count
    return hidden, latent_count, state_count, bias_count


def linear_latent_router_gene_count(config: KnowledgeConfig, action_count: int) -> int:
    _, latent_count, state_count, bias_count = _linear_router_gene_layout(
        config, action_count
    )
    return latent_count + state_count + bias_count


def _mlp_router_gene_layout(
    config: KnowledgeConfig, action_count: int
) -> tuple[int, int, int, int, int, int]:
    projection_width = int(config.latent_router_hidden_width)
    hidden_width = int(config.latent_router_mlp_hidden_width)
    input_width = projection_width + LATENT_STATE_WIDTH + LATENT_ROUTER_METADATA_WIDTH
    first_weight_count = hidden_width * input_width
    first_bias_count = hidden_width
    second_weight_count = action_count * hidden_width
    second_bias_count = action_count
    return (
        input_width,
        hidden_width,
        first_weight_count,
        first_bias_count,
        second_weight_count,
        second_bias_count,
    )


def mlp_latent_router_gene_count(config: KnowledgeConfig, action_count: int) -> int:
    (
        _,
        _,
        first_weight_count,
        first_bias_count,
        second_weight_count,
        second_bias_count,
    ) = _mlp_router_gene_layout(config, action_count)
    return (
        first_weight_count
        + first_bias_count
        + second_weight_count
        + second_bias_count
    )


def latent_router_gene_count(config: KnowledgeConfig, action_count: int) -> int:
    """Return inherited router genes for the configured latent schema.

    The nonlinear L2 schema deliberately retains the complete L1 linear router
    prefix.  That prefix provides an auditable matched-capacity shadow policy
    and keeps L1 parameters available for later evolutionary transitions.
    """
    linear = linear_latent_router_gene_count(config, action_count)
    if config.latent_router_schema == LATENT_ROUTER_SCHEMA:
        return linear
    if config.latent_router_schema == LATENT_MLP_ROUTER_SCHEMA:
        return linear + mlp_latent_router_gene_count(config, action_count)
    raise ValueError("unknown latent router schema")


def latent_mlp_gene_start(
    router_gene_start: int, config: KnowledgeConfig, action_count: int
) -> int:
    return int(router_gene_start) + linear_latent_router_gene_count(
        config, action_count
    )


def _quantize_gene_block(raw: Any, *, scale: int, xp: Any) -> Any:
    return xp.rint(xp.clip(raw, -1.0, 1.0) * int(scale)).astype(
        xp.int16, copy=False
    )


def _quantized_linear_router_parameters(
    genotype: Any,
    *,
    start: int,
    config: KnowledgeConfig,
    action_count: int,
) -> tuple[Any, Any, Any]:
    xp = backend_from_array(genotype).xp
    hidden, latent_count, state_count, bias_count = _linear_router_gene_layout(
        config, action_count
    )
    required = start + latent_count + state_count + bias_count
    if genotype.ndim != 2 or genotype.shape[1] < required:
        raise ValueError("genotype does not contain the configured linear latent router genes")
    scale = int(config.latent_router_weight_quantization_scale)
    cursor = int(start)
    latent_raw = genotype[:, cursor : cursor + latent_count]
    cursor += latent_count
    state_raw = genotype[:, cursor : cursor + state_count]
    cursor += state_count
    bias_raw = genotype[:, cursor : cursor + bias_count]
    latent_weights = _quantize_gene_block(latent_raw, scale=scale, xp=xp).reshape(
        genotype.shape[0], action_count, hidden
    )
    state_weights = _quantize_gene_block(state_raw, scale=scale, xp=xp).reshape(
        genotype.shape[0], action_count, LATENT_STATE_WIDTH
    )
    bias = _quantize_gene_block(bias_raw, scale=scale, xp=xp).reshape(
        genotype.shape[0], action_count
    )
    return latent_weights, state_weights, bias


def _quantized_mlp_router_parameters(
    genotype: Any,
    *,
    start: int,
    config: KnowledgeConfig,
    action_count: int,
) -> tuple[Any, Any, Any, Any]:
    xp = backend_from_array(genotype).xp
    (
        input_width,
        hidden_width,
        first_weight_count,
        first_bias_count,
        second_weight_count,
        second_bias_count,
    ) = _mlp_router_gene_layout(config, action_count)
    required = (
        int(start)
        + first_weight_count
        + first_bias_count
        + second_weight_count
        + second_bias_count
    )
    if genotype.ndim != 2 or genotype.shape[1] < required:
        raise ValueError("genotype does not contain the configured MLP latent router genes")
    scale = int(config.latent_router_weight_quantization_scale)
    cursor = int(start)
    first_weight_raw = genotype[:, cursor : cursor + first_weight_count]
    cursor += first_weight_count
    first_bias_raw = genotype[:, cursor : cursor + first_bias_count]
    cursor += first_bias_count
    second_weight_raw = genotype[:, cursor : cursor + second_weight_count]
    cursor += second_weight_count
    second_bias_raw = genotype[:, cursor : cursor + second_bias_count]
    first_weights = _quantize_gene_block(
        first_weight_raw, scale=scale, xp=xp
    ).reshape(genotype.shape[0], hidden_width, input_width)
    first_bias = _quantize_gene_block(
        first_bias_raw, scale=scale, xp=xp
    ).reshape(genotype.shape[0], hidden_width)
    second_weights = _quantize_gene_block(
        second_weight_raw, scale=scale, xp=xp
    ).reshape(genotype.shape[0], action_count, hidden_width)
    second_bias = _quantize_gene_block(
        second_bias_raw, scale=scale, xp=xp
    ).reshape(genotype.shape[0], action_count)
    return first_weights, first_bias, second_weights, second_bias


def _build_common_router_inputs(
    batch: LatentRouterBatch,
    *,
    state_features: Any,
    config: KnowledgeConfig,
    xp: Any,
) -> tuple[Any, Any, Any]:
    """Build exact quantized latent projection, public state, and metadata."""
    q = int(config.latent_value_quantization_scale)
    projection_width = int(config.latent_router_hidden_width)
    copy_count = batch.size
    hidden_q = xp.zeros((copy_count, projection_width), dtype=xp.int64)
    for bucket in batch.buckets:
        rows = xp.asarray(bucket.batch_rows, dtype=xp.int32)
        values = xp.asarray(bucket.values, dtype=xp.int64)
        projection = xp.asarray(
            _projection_matrix(bucket.width, projection_width), dtype=xp.int64
        )
        # Fixed-width integer GEMM.  Since all terms are int16/int8 and the
        # configured widths are bounded, CPU and GPU compute the same exact sum.
        projected = values @ projection
        projected = _round_divide_signed_backend(
            projected, max(bucket.width, 1), xp
        )
        hidden_q[rows] = projected

    outcome_q = xp.asarray(batch.outcome_q, dtype=xp.int64)
    outcome_projection = xp.asarray(
        _outcome_projection(projection_width), dtype=xp.int64
    )
    injected = outcome_q @ outcome_projection
    injected = _round_divide_signed_backend(injected, OUTCOME_WIDTH, xp)
    injection_q = int(np.rint(float(config.latent_outcome_injection) * q))
    hidden_q += _round_divide_signed_backend(injected * injection_q, q, xp)
    hidden_q = xp.clip(hidden_q, -32767, 32767).astype(xp.int32)

    state_host = np.asarray(to_numpy(state_features), dtype=np.float32)
    if state_host.shape != (batch.active_count, LATENT_STATE_WIDTH):
        raise ValueError("latent router state features have an invalid shape")
    state_q = xp.asarray(
        np.rint(np.clip(state_host, -2.0, 2.0) * q).astype(np.int32),
        dtype=xp.int32,
    )
    reliability_q = xp.asarray(batch.reliability_q, dtype=xp.int32)
    acquisition_transfer_q = xp.asarray(
        (batch.acquisition_kinds == ACQUISITION_TRANSFER).astype(np.int32) * q,
        dtype=xp.int32,
    )
    unverified_q = xp.asarray(
        batch.unverified_transfer.astype(np.int32) * q,
        dtype=xp.int32,
    )
    metadata_q = xp.stack(
        (reliability_q, acquisition_transfer_q, unverified_q), axis=1
    ).astype(xp.int32, copy=False)
    return hidden_q, state_q, metadata_q


def _route_linear_copy_q(
    *,
    hidden_q: Any,
    state_q: Any,
    active_rows: Any,
    genotype: Any,
    router_gene_start: int,
    config: KnowledgeConfig,
    action_count: int,
    xp: Any,
) -> Any:
    q = int(config.latent_value_quantization_scale)
    weight_q = int(config.latent_router_weight_quantization_scale)
    latent_weights, state_weights, bias = _quantized_linear_router_parameters(
        genotype,
        start=int(router_gene_start),
        config=config,
        action_count=action_count,
    )
    gathered_latent = latent_weights[active_rows].astype(xp.int64)
    gathered_state_weights = state_weights[active_rows].astype(xp.int64)
    gathered_bias = bias[active_rows].astype(xp.int64)
    gathered_state = state_q[active_rows].astype(xp.int64)
    accumulator = gathered_bias * xp.int64(q)
    for hidden in range(int(config.latent_router_hidden_width)):
        accumulator += (
            hidden_q[:, hidden, None].astype(xp.int64)
            * gathered_latent[:, :, hidden]
        )
    for state_index in range(LATENT_STATE_WIDTH):
        accumulator += (
            gathered_state[:, state_index, None]
            * gathered_state_weights[:, :, state_index]
        )
    return _round_divide_signed_backend(accumulator, weight_q, xp)


def _route_mlp_copy_q(
    *,
    hidden_q: Any,
    state_q: Any,
    metadata_q: Any,
    active_rows: Any,
    genotype: Any,
    router_gene_start: int,
    config: KnowledgeConfig,
    action_count: int,
    xp: Any,
) -> tuple[Any, dict[str, Any]]:
    """Execute a two-layer inherited MLP using exact integer hard-tanh."""
    q = int(config.latent_value_quantization_scale)
    weight_q = int(config.latent_router_weight_quantization_scale)
    mlp_start = latent_mlp_gene_start(router_gene_start, config, action_count)
    first_weights, first_bias, second_weights, second_bias = (
        _quantized_mlp_router_parameters(
            genotype,
            start=mlp_start,
            config=config,
            action_count=action_count,
        )
    )
    gathered_state = state_q[active_rows].astype(xp.int32)
    input_q = xp.concatenate(
        (hidden_q.astype(xp.int32), gathered_state, metadata_q), axis=1
    )
    gathered_first_weights = first_weights[active_rows].astype(xp.int64)
    gathered_first_bias = first_bias[active_rows].astype(xp.int64)
    first_accumulator = gathered_first_bias * xp.int64(q)
    for input_index in range(input_q.shape[1]):
        first_accumulator += (
            input_q[:, input_index, None].astype(xp.int64)
            * gathered_first_weights[:, :, input_index]
        )
    pre_activation_q = _round_divide_signed_backend(
        first_accumulator, weight_q, xp
    )
    activation_clip_q = max(
        1, int(np.rint(float(config.latent_router_activation_clip) * q))
    )
    saturation = xp.abs(pre_activation_q) > activation_clip_q
    activated_q = xp.clip(
        pre_activation_q, -activation_clip_q, activation_clip_q
    ).astype(xp.int32)

    gathered_second_weights = second_weights[active_rows].astype(xp.int64)
    gathered_second_bias = second_bias[active_rows].astype(xp.int64)
    second_accumulator = gathered_second_bias * xp.int64(q)
    for hidden_index in range(int(config.latent_router_mlp_hidden_width)):
        second_accumulator += (
            activated_q[:, hidden_index, None].astype(xp.int64)
            * gathered_second_weights[:, :, hidden_index]
        )
    copy_route_q = _round_divide_signed_backend(
        second_accumulator, weight_q, xp
    )
    max_q = int(np.rint(float(config.latent_max_abs_logit_residual) * q))
    output_clip_mask = xp.abs(copy_route_q) > max_q
    return copy_route_q, {
        "copy_mlp_pre_activation_q": pre_activation_q,
        "copy_mlp_hidden_q": activated_q,
        "copy_mlp_saturation_count": saturation.sum(axis=1).astype(xp.int32),
        "copy_mlp_hidden_abs_sum": xp.abs(activated_q).sum(axis=1).astype(xp.int64),
        "copy_mlp_hidden_active_count": (activated_q != 0).sum(axis=1).astype(xp.int32),
        "copy_mlp_output_clip_mask": output_clip_mask,
    }


def _aggregate_copy_routes(
    copy_route_q: Any,
    *,
    batch: LatentRouterBatch,
    active_rows: Any,
    use_strength: Any,
    config: KnowledgeConfig,
    action_count: int,
    xp: Any,
) -> Any:
    q = int(config.latent_value_quantization_scale)
    reliability_q = xp.asarray(batch.reliability_q, dtype=xp.int64)
    numerator = xp.zeros((batch.active_count, action_count), dtype=xp.int64)
    denominator = xp.zeros(batch.active_count, dtype=xp.int64)
    xp.add.at(numerator, active_rows, copy_route_q * reliability_q[:, None])
    xp.add.at(denominator, active_rows, reliability_q)
    safe_denominator = xp.maximum(denominator, xp.int64(1))
    mean_route_q = _round_divide_signed_backend(
        numerator, safe_denominator[:, None], xp
    )
    use_host = np.asarray(to_numpy(use_strength), dtype=np.float32)
    use_q = xp.asarray(
        np.rint(np.clip(use_host, 0.0, 1.0) * q).astype(np.int64),
        dtype=xp.int64,
    )
    published_q = _round_divide_signed_backend(
        mean_route_q * use_q[:, None], q, xp
    )
    max_q = int(np.rint(float(config.latent_max_abs_logit_residual) * q))
    return xp.clip(published_q, -max_q, max_q).astype(xp.int32)


def route_latent_router_batch(
    batch: LatentRouterBatch,
    *,
    genotype: Any,
    router_gene_start: int,
    use_strength: Any,
    state_features: Any,
    config: KnowledgeConfig,
    action_count: int,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Route matched latent copies and publish exact integer residuals.

    L1 uses the inherited quantized linear router.  L2 retains that complete
    router as a shadow baseline, then evaluates a separately inherited two-layer
    MLP with an integer hard-tanh activation.  Both paths use the same common
    latent projection and exact publication boundary.
    """
    if batch.size == 0:
        projection_width = int(config.latent_router_hidden_width)
        mlp_width = int(config.latent_router_mlp_hidden_width)
        return np.zeros((batch.active_count, action_count), dtype=np.int32), {
            "copy_route_q": np.empty((0, action_count), dtype=np.int32),
            "copy_hidden_q": np.empty((0, projection_width), dtype=np.int32),
            "linear_shadow_published_q": np.zeros(
                (batch.active_count, action_count), dtype=np.int32
            ),
            "copy_mlp_pre_activation_q": np.empty((0, mlp_width), dtype=np.int32),
            "copy_mlp_hidden_q": np.empty((0, mlp_width), dtype=np.int32),
            "copy_mlp_saturation_count": np.empty(0, dtype=np.int32),
            "copy_mlp_hidden_abs_sum": np.empty(0, dtype=np.int64),
            "copy_mlp_hidden_active_count": np.empty(0, dtype=np.int32),
            "copy_mlp_output_clip_mask": np.empty((0, action_count), dtype=bool),
        }
    xp = backend_from_array(genotype).xp
    active_rows = xp.asarray(batch.copy_active_rows, dtype=xp.int32)
    hidden_q, state_q, metadata_q = _build_common_router_inputs(
        batch, state_features=state_features, config=config, xp=xp
    )
    linear_copy_q = _route_linear_copy_q(
        hidden_q=hidden_q,
        state_q=state_q,
        active_rows=active_rows,
        genotype=genotype,
        router_gene_start=router_gene_start,
        config=config,
        action_count=action_count,
        xp=xp,
    )
    linear_published_q = _aggregate_copy_routes(
        linear_copy_q,
        batch=batch,
        active_rows=active_rows,
        use_strength=use_strength,
        config=config,
        action_count=action_count,
        xp=xp,
    )

    if config.latent_router_schema == LATENT_ROUTER_SCHEMA:
        published_q = linear_published_q
        diagnostics: dict[str, Any] = {
            "copy_route_q": linear_copy_q,
            "copy_hidden_q": hidden_q,
            "linear_shadow_published_q": xp.zeros_like(linear_published_q),
            "copy_mlp_pre_activation_q": xp.empty((batch.size, 0), dtype=xp.int32),
            "copy_mlp_hidden_q": xp.empty((batch.size, 0), dtype=xp.int32),
            "copy_mlp_saturation_count": xp.zeros(batch.size, dtype=xp.int32),
            "copy_mlp_hidden_abs_sum": xp.zeros(batch.size, dtype=xp.int64),
            "copy_mlp_hidden_active_count": xp.zeros(batch.size, dtype=xp.int32),
            "copy_mlp_output_clip_mask": xp.zeros(
                (batch.size, action_count), dtype=bool
            ),
        }
    elif config.latent_router_schema == LATENT_MLP_ROUTER_SCHEMA:
        mlp_copy_q, mlp_diagnostics = _route_mlp_copy_q(
            hidden_q=hidden_q,
            state_q=state_q,
            metadata_q=metadata_q,
            active_rows=active_rows,
            genotype=genotype,
            router_gene_start=router_gene_start,
            config=config,
            action_count=action_count,
            xp=xp,
        )
        published_q = _aggregate_copy_routes(
            mlp_copy_q,
            batch=batch,
            active_rows=active_rows,
            use_strength=use_strength,
            config=config,
            action_count=action_count,
            xp=xp,
        )
        diagnostics = {
            "copy_route_q": mlp_copy_q,
            "copy_hidden_q": hidden_q,
            "linear_shadow_published_q": linear_published_q,
            **mlp_diagnostics,
        }
    else:
        raise ValueError("unknown latent router schema")

    return to_numpy(published_q).astype(np.int32, copy=False), {
        name: to_numpy(value)
        for name, value in diagnostics.items()
    }


__all__ = [
    "LATENT_MLP_POLICY_RESIDUAL_SCHEMA",
    "LATENT_MLP_ROUTER_SCHEMA",
    "LATENT_POLICY_RESIDUAL_SCHEMA",
    "LATENT_ROUTER_METADATA_WIDTH",
    "LATENT_ROUTER_SCHEMA",
    "LATENT_SCHEMA",
    "LATENT_STATE_WIDTH",
    "LatentBucket",
    "LatentRouterBatch",
    "VariableLatentContentStore",
    "build_latent_router_batch",
    "latent_mlp_gene_start",
    "latent_router_gene_count",
    "latent_router_state_features",
    "linear_latent_router_gene_count",
    "mlp_latent_router_gene_count",
    "route_latent_router_batch",
]
