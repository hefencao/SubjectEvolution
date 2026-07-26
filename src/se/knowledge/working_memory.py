"""Quantized working memory for stateful latent-knowledge routing.

The memory is an explicitly versioned, optional world mechanism. It is not an
external controller: each coordinate is stored in entity state, updated from
public observations and committed local outcomes, and driven by inherited
parameters. Updates use exact integer arithmetic and are checkpointable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..backend import to_numpy
from ..cfg import KnowledgeConfig
from se.knowledge import OUTCOME_WIDTH

WORKING_MEMORY_SCHEMA = "quantized-working-memory-v1"
WORKING_MEMORY_INPUT_WIDTH = 4


def _signed_projection(rows: int, cols: int, salt: int) -> np.ndarray:
    out = np.empty((int(rows), int(cols)), dtype=np.int8)
    mask = (1 << 64) - 1
    for row in range(int(rows)):
        for col in range(int(cols)):
            value = (
                int(salt)
                ^ ((row + 1) * 0x9E3779B97F4A7C15)
                ^ ((col + 1) * 0xBF58476D1CE4E5B9)
            ) & mask
            value ^= value >> 30
            value = (value * 0xBF58476D1CE4E5B9) & mask
            value ^= value >> 27
            value = (value * 0x94D049BB133111EB) & mask
            value ^= value >> 31
            out[row, col] = np.int8(1 if value & 1 else -1)
    return out


def working_memory_gene_count(config: KnowledgeConfig) -> int:
    """Per-dimension decay, prediction gain, observation gain, and bias."""
    return int(config.working_memory_width) * 4 if config.working_memory_enabled else 0


@dataclass(frozen=True)
class WorkingMemoryUpdateResult:
    tick: int
    active_rows: np.ndarray
    entity_ids: np.ndarray
    previous_q: np.ndarray
    proposed_q: np.ndarray
    committed_q: np.ndarray
    observation_q: np.ndarray
    observation_delta_q: np.ndarray
    prediction_error_q: np.ndarray
    saturation_count: np.ndarray
    active_dimension_count: np.ndarray
    requested_energy: np.ndarray
    committed_energy: np.ndarray
    accepted: np.ndarray

    @classmethod
    def empty(cls, tick: int, width: int) -> "WorkingMemoryUpdateResult":
        return cls(
            tick=int(tick),
            active_rows=np.empty(0, dtype=np.int32),
            entity_ids=np.empty(0, dtype=np.uint64),
            previous_q=np.empty((0, int(width)), dtype=np.int16),
            proposed_q=np.empty((0, int(width)), dtype=np.int16),
            committed_q=np.empty((0, int(width)), dtype=np.int16),
            observation_q=np.empty((0, WORKING_MEMORY_INPUT_WIDTH), dtype=np.int16),
            observation_delta_q=np.empty((0, WORKING_MEMORY_INPUT_WIDTH), dtype=np.int16),
            prediction_error_q=np.empty((0, OUTCOME_WIDTH), dtype=np.int16),
            saturation_count=np.empty(0, dtype=np.uint16),
            active_dimension_count=np.empty(0, dtype=np.uint16),
            requested_energy=np.empty(0, dtype=np.float64),
            committed_energy=np.empty(0, dtype=np.float64),
            accepted=np.empty(0, dtype=bool),
        )

    @property
    def requested_total(self) -> float:
        return float(self.requested_energy.sum(dtype=np.float64))

    @property
    def committed_total(self) -> float:
        return float(self.committed_energy.sum(dtype=np.float64))

    @property
    def rejected_total(self) -> float:
        return float(self.requested_total - self.committed_total)


def memory_float_view(memory_q: np.ndarray, config: KnowledgeConfig) -> np.ndarray:
    scale = max(int(config.working_memory_quantization_scale), 1)
    return (np.asarray(memory_q, dtype=np.float64) / float(scale)).astype(np.float32)


def quantize_memory_observation(state_features: Any, config: KnowledgeConfig) -> np.ndarray:
    state = np.asarray(to_numpy(state_features), dtype=np.float32)
    if state.ndim != 2 or state.shape[1] != WORKING_MEMORY_INPUT_WIDTH:
        raise ValueError("working-memory observation must have four public coordinates")
    scale = int(config.working_memory_quantization_scale)
    return np.clip(
        np.rint(np.clip(state, -2.0, 2.0) * scale), -32767, 32767
    ).astype(np.int16)


def expected_outcomes_for_actions(
    plan: Any, *, active_count: int, actions: np.ndarray
) -> np.ndarray:
    """Extract the selected action's expected five-dimensional outcome."""
    result = np.zeros((int(active_count), OUTCOME_WIDTH), dtype=np.float32)
    if plan is None or int(getattr(plan, "size", 0)) == 0:
        return result
    selected = np.asarray(actions, dtype=np.int16)
    rows = np.asarray(plan.active_rows, dtype=np.int32)
    plan_actions = np.asarray(plan.action_ids, dtype=np.int16)
    match = plan_actions == selected[rows]
    if np.any(match):
        result[rows[match]] = np.asarray(plan.weighted_outcome_vectors[match], dtype=np.float32)
    return result


def _memory_parameters(
    genotype: np.ndarray, *, gene_start: int, config: KnowledgeConfig
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    width = int(config.working_memory_width)
    required = int(gene_start) + width * 4
    genes = np.asarray(to_numpy(genotype), dtype=np.float32)
    if genes.ndim != 2 or genes.shape[1] < required:
        raise ValueError("genotype does not contain working-memory genes")
    raw = np.clip(genes[:, gene_start:required], -1.0, 1.0)
    scale = int(config.working_memory_quantization_scale)
    decay = np.rint((raw[:, 0:width] + 1.0) * 0.5 * scale).astype(np.int32)
    prediction_gain = np.rint(raw[:, width : 2 * width] * scale).astype(np.int32)
    observation_gain = np.rint(raw[:, 2 * width : 3 * width] * scale).astype(np.int32)
    bias = np.rint(raw[:, 3 * width : 4 * width] * scale).astype(np.int32)
    return decay, prediction_gain, observation_gain, bias


def build_working_memory_update(
    *,
    tick: int,
    active_rows: np.ndarray,
    entity_ids: np.ndarray,
    previous_q: np.ndarray,
    previous_observation_q: np.ndarray,
    current_state_features: Any,
    actual_outcomes: np.ndarray,
    expected_outcomes: np.ndarray,
    genotype: np.ndarray,
    gene_start: int,
    available_energy: np.ndarray,
    config: KnowledgeConfig,
) -> WorkingMemoryUpdateResult:
    width = int(config.working_memory_width)
    rows = np.asarray(active_rows, dtype=np.int32)
    if not config.working_memory_enabled or rows.size == 0:
        return WorkingMemoryUpdateResult.empty(tick, width)
    ids = np.asarray(entity_ids, dtype=np.uint64)
    prev = np.asarray(previous_q, dtype=np.int16)
    prev_obs = np.asarray(previous_observation_q, dtype=np.int16)
    actual = np.asarray(actual_outcomes, dtype=np.float32)
    expected = np.asarray(expected_outcomes, dtype=np.float32)
    energy = np.asarray(available_energy, dtype=np.float64)
    if prev.shape != (rows.size, width):
        raise ValueError("working-memory state shape does not match active rows")
    if prev_obs.shape != (rows.size, WORKING_MEMORY_INPUT_WIDTH):
        raise ValueError("working-memory previous observation shape is invalid")
    if actual.shape != (rows.size, OUTCOME_WIDTH) or expected.shape != actual.shape:
        raise ValueError("working-memory outcomes must be five-dimensional")
    if ids.shape != (rows.size,) or energy.shape != (rows.size,):
        raise ValueError("working-memory entity metadata must align")

    scale = int(config.working_memory_quantization_scale)
    current_obs = quantize_memory_observation(current_state_features, config)
    obs_delta = np.clip(
        current_obs.astype(np.int32) - prev_obs.astype(np.int32), -32767, 32767
    ).astype(np.int16)
    outcome_scales = np.asarray(config.policy_outcome_scales, dtype=np.float64)
    normalized_error = np.clip(
        (actual.astype(np.float64) - expected.astype(np.float64)) / outcome_scales[None, :],
        -float(config.policy_outcome_clip),
        float(config.policy_outcome_clip),
    )
    prediction_error_q = np.clip(
        np.rint(normalized_error * scale), -32767, 32767
    ).astype(np.int16)

    prediction_projection = _signed_projection(OUTCOME_WIDTH, width, 0x574D50524544).astype(np.int64)
    observation_projection = _signed_projection(
        WORKING_MEMORY_INPUT_WIDTH, width, 0x574D4F4253
    ).astype(np.int64)
    prediction_signal = prediction_error_q.astype(np.int64) @ prediction_projection
    prediction_signal = np.rint(prediction_signal / float(OUTCOME_WIDTH)).astype(np.int64)
    observation_signal = obs_delta.astype(np.int64) @ observation_projection
    observation_signal = np.rint(
        observation_signal / float(WORKING_MEMORY_INPUT_WIDTH)
    ).astype(np.int64)

    decay_q, prediction_gain_q, observation_gain_q, bias_q = _memory_parameters(
        genotype, gene_start=gene_start, config=config
    )
    accumulator = prev.astype(np.int64) * decay_q.astype(np.int64)
    accumulator += prediction_signal * prediction_gain_q.astype(np.int64)
    accumulator += observation_signal * observation_gain_q.astype(np.int64)
    accumulator += bias_q.astype(np.int64) * np.int64(scale)
    magnitude = (np.abs(accumulator) + scale // 2) // scale
    proposed_i64 = np.where(accumulator < 0, -magnitude, magnitude)
    clip_q = max(1, int(round(float(config.working_memory_activation_clip) * scale)))
    saturation_mask = np.abs(proposed_i64) > clip_q
    proposed = np.clip(proposed_i64, -clip_q, clip_q).astype(np.int16)
    saturation_count = saturation_mask.sum(axis=1).astype(np.uint16)
    active_dimensions = (proposed != 0).sum(axis=1).astype(np.uint16)

    requested = (
        float(config.working_memory_base_energy_cost)
        + width * float(config.working_memory_energy_per_dimension)
        + saturation_count.astype(np.float64)
        * float(config.working_memory_energy_per_saturation)
    )
    accepted = energy + 1e-12 >= requested
    committed_energy = np.where(accepted, requested, 0.0)
    committed_q = np.where(accepted[:, None], proposed, prev).astype(np.int16)
    return WorkingMemoryUpdateResult(
        tick=int(tick),
        active_rows=rows.copy(),
        entity_ids=ids.copy(),
        previous_q=prev.copy(),
        proposed_q=proposed,
        committed_q=committed_q,
        observation_q=current_obs,
        observation_delta_q=obs_delta,
        prediction_error_q=prediction_error_q,
        saturation_count=saturation_count,
        active_dimension_count=active_dimensions,
        requested_energy=requested.astype(np.float64),
        committed_energy=committed_energy.astype(np.float64),
        accepted=accepted.astype(bool),
    )


__all__ = [
    "WORKING_MEMORY_SCHEMA",
    "WorkingMemoryUpdateResult",
    "build_working_memory_update",
    "expected_outcomes_for_actions",
    "memory_float_view",
    "quantize_memory_observation",
    "working_memory_gene_count",
]
