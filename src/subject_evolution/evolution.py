"""Periodic diagnostics for inherited strategy evolution.

Raw gene variance is not a sufficient diversity measure: softmax policies are
unchanged when the same feature coefficient is added to every action.  This
module therefore reports raw, gauge-canonical strategy, and fixed-probe
behavioural diversity without feeding any diagnostic value back into policy.
"""

from __future__ import annotations

import copy
from enum import IntEnum
import json
from pathlib import Path
from typing import Any

import numpy as np

from .policy import Action, ParametricPolicy
from .random_api import RandomContext, Stream, keys


class BenefitFlowKind(IntEnum):
    """Exhaustive boundary relation for one realized benefit transfer."""

    INTERNAL = 0
    GROUP_TO_GROUP = 1
    GROUP_TO_UNGROUPED = 2
    UNGROUPED_TO_GROUP = 3
    UNBOUNDED = 4


BENEFIT_FLOW_COUNT = len(BenefitFlowKind)


def _categorical_alignment(
    left: np.ndarray,
    right: np.ndarray,
) -> dict[str, float | int]:
    """Return deterministic contingency diagnostics for two labels.

    The result is observational only.  In particular, a high NMI does not
    imply that either label causes the other; it merely reports how strongly
    the two current partitions overlap.
    """

    a = np.asarray(left)
    b = np.asarray(right)
    if a.ndim != 1 or b.ndim != 1 or a.size != b.size:
        raise ValueError("categorical alignment inputs must be aligned vectors")
    if a.size == 0:
        return {
            "sample_size": 0,
            "left_count": 0,
            "right_count": 0,
            "mutual_information": 0.0,
            "normalized_mutual_information": 0.0,
            "left_given_right_purity": 0.0,
            "right_given_left_purity": 0.0,
        }
    _, ai = np.unique(a, return_inverse=True)
    _, bi = np.unique(b, return_inverse=True)
    left_count = int(ai.max()) + 1
    right_count = int(bi.max()) + 1
    joint = np.zeros((left_count, right_count), dtype=np.int64)
    np.add.at(joint, (ai, bi), 1)
    total = float(a.size)
    pxy = joint.astype(np.float64) / total
    px = pxy.sum(axis=1)
    py = pxy.sum(axis=0)
    expected = px[:, None] * py[None, :]
    valid = pxy > 0.0
    mutual_information = float(
        np.sum(pxy[valid] * np.log(pxy[valid] / expected[valid]))
    )
    hx = float(-np.sum(px[px > 0.0] * np.log(px[px > 0.0])))
    hy = float(-np.sum(py[py > 0.0] * np.log(py[py > 0.0])))
    denominator = max((max(hx, 0.0) * max(hy, 0.0)) ** 0.5, 1e-30)
    pair_total = int(a.size * (a.size - 1) // 2)
    left_pairs = int(np.sum(joint.sum(axis=1) * (joint.sum(axis=1) - 1) // 2))
    right_pairs = int(np.sum(joint.sum(axis=0) * (joint.sum(axis=0) - 1) // 2))
    joint_pairs = int(np.sum(joint * (joint - 1) // 2))
    same_left_given_same_right = (
        joint_pairs / right_pairs if right_pairs else 0.0
    )
    same_right_given_same_left = (
        joint_pairs / left_pairs if left_pairs else 0.0
    )
    baseline_same_left = left_pairs / pair_total if pair_total else 0.0
    baseline_same_right = right_pairs / pair_total if pair_total else 0.0
    pair_enrichment = (
        (joint_pairs / pair_total) / (baseline_same_left * baseline_same_right)
        if pair_total and baseline_same_left > 0.0 and baseline_same_right > 0.0
        else 0.0
    )
    return {
        "sample_size": int(a.size),
        "left_count": left_count,
        "right_count": right_count,
        "mutual_information": mutual_information,
        "normalized_mutual_information": float(mutual_information / denominator),
        # Weighted dominant-left share within each right category.
        "left_given_right_purity": float(joint.max(axis=0).sum() / total),
        # Weighted dominant-right share within each left category.
        "right_given_left_purity": float(joint.max(axis=1).sum() / total),
        "pair_total": pair_total,
        "same_left_pair_count": left_pairs,
        "same_right_pair_count": right_pairs,
        "same_both_pair_count": joint_pairs,
        "same_left_given_same_right": float(same_left_given_same_right),
        "same_right_given_same_left": float(same_right_given_same_left),
        "pair_enrichment_over_independence": float(pair_enrichment),
    }


def lineage_group_diagnostics(
    alive: np.ndarray,
    lineage_ids: np.ndarray,
    group_ids: np.ndarray,
) -> dict[str, float | int | str]:
    active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
    if active.size == 0:
        return {
            "lineage_group_alignment_schema": "lineage-group-alignment-v1",
            "grouped_entity_count": 0,
            "grouped_entity_fraction": 0.0,
            "group_count": 0,
            "lineage_group_nmi": 0.0,
            "group_lineage_purity": 0.0,
            "lineage_group_purity": 0.0,
            "lineage_group_alignment_sample_size": 0,
            "same_lineage_given_same_group": 0.0,
            "same_group_given_same_lineage": 0.0,
            "lineage_group_pair_enrichment": 0.0,
        }
    groups = np.asarray(group_ids, dtype=np.uint64)[active]
    lineages = np.asarray(lineage_ids, dtype=np.uint64)[active]
    grouped = groups != 0
    if not np.any(grouped):
        return {
            "lineage_group_alignment_schema": "lineage-group-alignment-v1",
            "grouped_entity_count": 0,
            "grouped_entity_fraction": 0.0,
            "group_count": 0,
            "lineage_group_nmi": 0.0,
            "group_lineage_purity": 0.0,
            "lineage_group_purity": 0.0,
            "lineage_group_alignment_sample_size": 0,
            "same_lineage_given_same_group": 0.0,
            "same_group_given_same_lineage": 0.0,
            "lineage_group_pair_enrichment": 0.0,
        }
    alignment = _categorical_alignment(lineages[grouped], groups[grouped])
    return {
        "lineage_group_alignment_schema": "lineage-group-alignment-v1",
        "grouped_entity_count": int(np.count_nonzero(grouped)),
        "grouped_entity_fraction": float(np.mean(grouped)),
        "group_count": int(alignment["right_count"]),
        "lineage_group_nmi": float(alignment["normalized_mutual_information"]),
        "group_lineage_purity": float(alignment["left_given_right_purity"]),
        "lineage_group_purity": float(alignment["right_given_left_purity"]),
        "lineage_group_alignment_sample_size": int(alignment["sample_size"]),
        "same_lineage_given_same_group": float(
            alignment["same_left_given_same_right"]
        ),
        "same_group_given_same_lineage": float(
            alignment["same_right_given_same_left"]
        ),
        "lineage_group_pair_enrichment": float(
            alignment["pair_enrichment_over_independence"]
        ),
    }


def benefit_flow_totals(
    owner_group_tokens: np.ndarray,
    target_group_tokens: np.ndarray,
    amounts: np.ndarray,
) -> np.ndarray:
    """Return a lossless five-way energy partition for realized transfers."""
    owners = np.asarray(owner_group_tokens, dtype=np.uint64)
    targets = np.asarray(target_group_tokens, dtype=np.uint64)
    values = np.asarray(amounts, dtype=np.float64)
    if any(value.ndim != 1 for value in (owners, targets, values)) or not (
        owners.size == targets.size == values.size
    ):
        raise ValueError("benefit flow arrays must be aligned and one-dimensional")
    if np.any(~np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("benefit flow amounts must be finite and non-negative")

    kinds = np.full(owners.size, BenefitFlowKind.UNBOUNDED, dtype=np.int8)
    owner_grouped = owners != 0
    target_grouped = targets != 0
    kinds[owner_grouped & (owners == targets)] = BenefitFlowKind.INTERNAL
    kinds[owner_grouped & target_grouped & (owners != targets)] = (
        BenefitFlowKind.GROUP_TO_GROUP
    )
    kinds[owner_grouped & ~target_grouped] = BenefitFlowKind.GROUP_TO_UNGROUPED
    kinds[~owner_grouped & target_grouped] = BenefitFlowKind.UNGROUPED_TO_GROUP
    return np.bincount(kinds, weights=values, minlength=BENEFIT_FLOW_COUNT).astype(
        np.float64,
        copy=False,
    )


class LaggedBenefitBoundary:
    """Frozen group membership keyed by physical slot and stable entity ID.

    Slot matching alone is unsafe because lifecycle commits reuse slots.  A
    post-snapshot entity is therefore outside the frozen boundary even when it
    occupies a slot that previously belonged to a grouped entity.
    """

    def __init__(self, capacity: int) -> None:
        self.snapshot_tick = 0
        self.entity_ids = np.zeros(capacity, dtype=np.uint64)
        self.group_tokens = np.zeros(capacity, dtype=np.uint64)
        self.flow_energy_total = np.zeros(BENEFIT_FLOW_COUNT, dtype=np.float64)

    def clone(self) -> "LaggedBenefitBoundary":
        branch = type(self)(self.entity_ids.size)
        branch.snapshot_tick = self.snapshot_tick
        branch.entity_ids = self.entity_ids.copy()
        branch.group_tokens = self.group_tokens.copy()
        branch.flow_energy_total = self.flow_energy_total.copy()
        return branch

    def freeze(
        self,
        *,
        tick: int,
        alive: np.ndarray,
        stable_ids: np.ndarray,
        group_tokens: np.ndarray,
    ) -> None:
        alive_values = np.asarray(alive, dtype=bool)
        ids = np.asarray(stable_ids, dtype=np.uint64)
        groups = np.asarray(group_tokens, dtype=np.uint64)
        if any(value.ndim != 1 for value in (alive_values, ids, groups)) or not (
            alive_values.size == ids.size == groups.size == self.entity_ids.size
        ):
            raise ValueError("lagged boundary arrays must match world capacity")
        self.entity_ids.fill(0)
        self.group_tokens.fill(0)
        self.entity_ids[alive_values] = ids[alive_values]
        self.group_tokens[alive_values] = groups[alive_values]
        self.snapshot_tick = int(tick)

    def record(
        self,
        *,
        owner_indices: np.ndarray,
        target_indices: np.ndarray,
        current_stable_ids: np.ndarray,
        amounts: np.ndarray,
    ) -> np.ndarray:
        owners = np.asarray(owner_indices, dtype=np.int32)
        targets = np.asarray(target_indices, dtype=np.int32)
        current_ids = np.asarray(current_stable_ids, dtype=np.uint64)
        values = np.asarray(amounts, dtype=np.float64)
        if any(value.ndim != 1 for value in (owners, targets, values)) or not (
            owners.size == targets.size == values.size
        ):
            raise ValueError("lagged benefit event arrays must be aligned")
        if current_ids.ndim != 1 or current_ids.size != self.entity_ids.size:
            raise ValueError("current stable IDs must match frozen world capacity")
        if owners.size and (
            np.any(owners < 0)
            or np.any(targets < 0)
            or np.any(owners >= current_ids.size)
            or np.any(targets >= current_ids.size)
        ):
            raise ValueError("lagged benefit event contains an invalid slot")
        owner_match = self.entity_ids[owners] == current_ids[owners]
        target_match = self.entity_ids[targets] == current_ids[targets]
        owner_groups = np.where(owner_match, self.group_tokens[owners], 0)
        target_groups = np.where(target_match, self.group_tokens[targets], 0)
        totals = benefit_flow_totals(owner_groups, target_groups, values)
        self.flow_energy_total += totals
        return totals


def _deterministic_sample(
    active: np.ndarray,
    stable_ids: np.ndarray,
    run_seed: int,
    capacity: int,
) -> np.ndarray:
    if active.size <= capacity:
        return active
    ctx = RandomContext(run_seed, 0, phase=92, stream=Stream.EVOLUTION_EVALUATION)
    score = keys(ctx, stable_ids[active], draw_index=0)
    selected = np.argpartition(score, capacity - 1)[:capacity]
    # Stable-ID order makes all downstream reductions repeatable.
    return active[selected[np.argsort(stable_ids[active[selected]], kind="stable")]]


def _entropy(probability: np.ndarray, axis: int = -1) -> np.ndarray:
    return -np.sum(
        probability * np.log(np.clip(probability, 1e-12, 1.0)),
        axis=axis,
    )


def strategy_structure(
    alive: np.ndarray,
    stable_ids: np.ndarray,
    genotype: np.ndarray,
    *,
    run_seed: int,
    temperature: float,
    sample_capacity: int = 4096,
    compute_effective_dimensions: bool = True,
) -> tuple[dict[str, float | int], np.ndarray]:
    """Measure genotype and policy-function diversity on a stable sample."""
    active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
    sampled = _deterministic_sample(active, stable_ids, run_seed, sample_capacity)
    if sampled.size == 0:
        return {
            "strategy_sample_size": 0,
            "raw_strategy_diversity": 0.0,
            "canonical_strategy_diversity": 0.0,
            "strategy_effective_dimensions": 0.0,
            "policy_probability_diversity": 0.0,
            "mean_probe_policy_entropy": 0.0,
            "dominant_action_coverage": 0,
        }, np.zeros(ParametricPolicy.STRATEGY_GENES, dtype=np.float64)

    raw = np.asarray(
        genotype[sampled, ParametricPolicy.STRATEGY_START : ParametricPolicy.STRATEGY_STOP],
        dtype=np.float64,
    ).reshape(sampled.size, len(Action), ParametricPolicy.STRATEGY_FEATURES)
    # Softmax is invariant to a feature coefficient shared by all actions.
    # Subtracting that action mean selects a canonical representative of each
    # behaviourally equivalent strategy matrix.
    canonical = raw - raw.mean(axis=1, keepdims=True)
    flat_raw = raw.reshape(sampled.size, -1)
    flat = canonical.reshape(sampled.size, -1)
    raw_diversity = float(np.mean(np.std(flat_raw, axis=0)))
    canonical_diversity = float(np.mean(np.std(flat, axis=0)))
    canonical_mean = flat.mean(axis=0)

    centered = flat - canonical_mean
    if compute_effective_dimensions and sampled.size > 1 and np.any(centered):
        singular = np.linalg.svd(centered, compute_uv=False)
        spectrum = singular * singular
        effective_dimensions = float(
            spectrum.sum() ** 2 / max(float(np.dot(spectrum, spectrum)), 1e-30)
        )
    else:
        effective_dimensions = 0.0

    feature_count = ParametricPolicy.STRATEGY_FEATURES
    probes = np.zeros((feature_count, feature_count), dtype=np.float64)
    probes[:, 0] = 1.0
    probes[np.arange(1, feature_count), np.arange(1, feature_count)] = 1.0
    logits = np.einsum("naf,pf->npa", canonical, probes, optimize=True)
    logits /= temperature
    logits -= logits.max(axis=2, keepdims=True)
    probability = np.exp(logits)
    probability /= probability.sum(axis=2, keepdims=True)
    probability_diversity = float(np.mean(np.std(probability, axis=0)))
    dominant = np.argmax(probability, axis=2)

    return {
        "strategy_sample_size": int(sampled.size),
        "raw_strategy_diversity": raw_diversity,
        "canonical_strategy_diversity": canonical_diversity,
        "strategy_effective_dimensions": effective_dimensions,
        "policy_probability_diversity": probability_diversity,
        "mean_probe_policy_entropy": float(np.mean(_entropy(probability))),
        "dominant_action_coverage": int(np.unique(dominant).size),
    }, canonical_mean


def actual_context_policy_diagnostics(
    active: np.ndarray,
    stable_ids: np.ndarray,
    genotype: np.ndarray,
    features: np.ndarray,
    action_mask: np.ndarray,
    logits: np.ndarray,
    *,
    run_seed: int,
    temperature: float,
    sample_capacity: int = 4096,
    strategy_sample_capacity: int = 1024,
    context_panel_capacity: int = 32,
) -> dict[str, Any]:
    """Measure policies on observations and constraints seen by real agents.

    The paired metrics describe the policy outputs actually available on this
    tick.  The common-panel metrics additionally evaluate sampled inherited
    strategies on the same small panel of real contexts, separating strategy
    differences from the fact that different entities inhabit different
    contexts.  Neither result is fed back into the simulation.
    """
    active_slots = np.asarray(active, dtype=np.int32)
    ids = np.asarray(stable_ids, dtype=np.uint64)
    observed_features = np.asarray(features, dtype=np.float32)
    observed_mask = np.asarray(action_mask, dtype=bool)
    observed_logits = np.asarray(logits, dtype=np.float32)
    action_count = len(Action)
    feature_count = ParametricPolicy.STRATEGY_FEATURES
    row_count = active_slots.size
    if not np.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("actual-context temperature must be positive")
    if active_slots.ndim != 1:
        raise ValueError("actual-context active slots must be one-dimensional")
    if observed_features.shape != (row_count, feature_count):
        raise ValueError("actual-context features do not align with active rows")
    if observed_mask.shape != (row_count, action_count):
        raise ValueError("actual-context action masks do not align with active rows")
    if observed_logits.shape != (row_count, action_count):
        raise ValueError("actual-context logits do not align with active rows")
    if active_slots.size and (
        np.any(active_slots < 0)
        or np.any(active_slots >= ids.size)
        or np.any(active_slots >= genotype.shape[0])
    ):
        raise ValueError("actual-context active slot is outside entity storage")
    if np.any(~np.isfinite(observed_features)) or np.any(
        ~np.isfinite(observed_logits)
    ):
        raise ValueError("actual-context values must be finite")
    if np.any(~observed_mask.any(axis=1)):
        raise ValueError("every actual context must permit at least one action")
    if row_count == 0:
        zeros_actions = [0.0] * action_count
        zeros_features = [0.0] * feature_count
        return {
            "actual_context_sample_size": 0,
            "actual_context_feature_mean": zeros_features,
            "actual_context_feature_std": zeros_features,
            "actual_context_action_feasible_fraction": zeros_actions,
            "actual_context_mean_action_probability": zeros_actions,
            "actual_context_policy_probability_diversity": 0.0,
            "actual_context_mean_policy_entropy": 0.0,
            "actual_context_dominant_action_coverage": 0,
            "actual_context_mean_feasible_actions": 0.0,
            "actual_context_mask_pattern_count": 0,
            "actual_context_panel_size": 0,
            "actual_context_strategy_sample_size": 0,
            "actual_context_common_panel_probability_diversity": 0.0,
            "actual_context_common_panel_mean_entropy": 0.0,
            "actual_context_common_panel_dominant_action_coverage": 0,
            "actual_context_common_panel_mean_action_probability": zeros_actions,
        }

    sampled_slots = _deterministic_sample(
        active_slots, ids, run_seed, sample_capacity
    )
    # ``active`` originates from flatnonzero/spatial stable sorting, so slot
    # order is monotonic on both backends.  Search explicitly and assert the
    # mapping rather than relying on a hidden row/slot identity.
    sampled_rows = np.searchsorted(active_slots, sampled_slots)
    if not np.array_equal(active_slots[sampled_rows], sampled_slots):
        raise ValueError("actual-context active rows must be sorted by slot")
    sample_features = observed_features[sampled_rows].astype(np.float64)
    sample_mask = observed_mask[sampled_rows]
    sample_logits = observed_logits[sampled_rows].astype(np.float64) / temperature
    sample_logits = np.where(sample_mask, sample_logits, -np.inf)
    sample_logits -= np.max(sample_logits, axis=1, keepdims=True)
    sample_probability = np.where(sample_mask, np.exp(sample_logits), 0.0)
    sample_probability /= sample_probability.sum(axis=1, keepdims=True)
    mask_bits = np.left_shift(
        np.uint16(1), np.arange(action_count, dtype=np.uint16)
    )
    mask_patterns = np.sum(
        sample_mask.astype(np.uint16) * mask_bits[None, :], axis=1
    )

    strategy_slots = _deterministic_sample(
        active_slots, ids, run_seed, strategy_sample_capacity
    )
    context_slots = _deterministic_sample(
        active_slots, ids, run_seed, context_panel_capacity
    )
    strategy = np.asarray(
        genotype[strategy_slots, ParametricPolicy.STRATEGY_START : ParametricPolicy.STRATEGY_STOP],
        dtype=np.float64,
    ).reshape(strategy_slots.size, action_count, feature_count)
    context_rows = np.searchsorted(active_slots, context_slots)
    context_features = observed_features[context_rows].astype(np.float64)
    context_mask = observed_mask[context_rows]
    panel_logits = np.einsum(
        "saf,cf->sca", strategy, context_features, optimize=True
    )
    panel_logits /= temperature
    panel_logits = np.where(context_mask[None, :, :], panel_logits, -np.inf)
    panel_logits -= np.max(panel_logits, axis=2, keepdims=True)
    panel_probability = np.where(
        context_mask[None, :, :], np.exp(panel_logits), 0.0
    )
    panel_probability /= panel_probability.sum(axis=2, keepdims=True)
    panel_dominant = np.argmax(panel_probability, axis=2)

    return {
        "actual_context_sample_size": int(sampled_slots.size),
        "actual_context_feature_mean": sample_features.mean(axis=0).tolist(),
        "actual_context_feature_std": sample_features.std(axis=0).tolist(),
        "actual_context_action_feasible_fraction": sample_mask.mean(axis=0).tolist(),
        "actual_context_mean_action_probability": sample_probability.mean(axis=0).tolist(),
        "actual_context_policy_probability_diversity": float(
            np.mean(np.std(sample_probability, axis=0))
        ),
        "actual_context_mean_policy_entropy": float(
            np.mean(_entropy(sample_probability))
        ),
        "actual_context_dominant_action_coverage": int(
            np.unique(np.argmax(sample_probability, axis=1)).size
        ),
        "actual_context_mean_feasible_actions": float(sample_mask.sum(axis=1).mean()),
        "actual_context_mask_pattern_count": int(np.unique(mask_patterns).size),
        "actual_context_panel_size": int(context_slots.size),
        "actual_context_strategy_sample_size": int(strategy_slots.size),
        "actual_context_common_panel_probability_diversity": float(
            np.mean(np.std(panel_probability, axis=0))
        ),
        "actual_context_common_panel_mean_entropy": float(
            np.mean(_entropy(panel_probability))
        ),
        "actual_context_common_panel_dominant_action_coverage": int(
            np.unique(panel_dominant).size
        ),
        "actual_context_common_panel_mean_action_probability": (
            panel_probability.mean(axis=(0, 1)).tolist()
        ),
    }


KNOWLEDGE_TRANSFER_TOTAL_KEYS = (
    "knowledge_transfer_proposals_total",
    "knowledge_transfer_attempts_total",
    "knowledge_transfer_delivered_total",
    "knowledge_transfer_lost_total",
    "knowledge_transfer_corrupted_total",
    "knowledge_transfer_committed_total",
    "knowledge_transfer_committed_bytes_total",
    "knowledge_transfer_duplicate_rejected_total",
    "knowledge_transfer_capacity_rejected_total",
    "knowledge_transfer_energy_rejected_total",
    "knowledge_transfer_attention_rejected_total",
    "knowledge_transfer_same_lineage_committed_total",
    "knowledge_transfer_cross_lineage_committed_total",
    "knowledge_transfer_unknown_lineage_committed_total",
    "knowledge_transfer_same_group_committed_total",
    "knowledge_transfer_cross_group_committed_total",
    "knowledge_transfer_unknown_group_committed_total",
    "knowledge_transfer_sender_energy_total",
    "knowledge_transfer_receiver_energy_total",
)


class EvolutionProgressTracker:
    """Write independent, fixed-cadence evolution diagnostics as JSONL."""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        period: int,
        run_seed: int,
        temperature: float,
        alive: np.ndarray,
        stable_ids: np.ndarray,
        genotype: np.ndarray,
        long_run_diagnostics_enabled: bool = False,
        long_run_diagnostics_schema: str = "disabled",
        morphology_trait_indices: tuple[int, ...] = (),
        morphology_trait_names: tuple[str, ...] = (),
    ) -> None:
        self.path = Path(output_dir) / "evolution_progress.jsonl"
        self.period = int(period)
        self.run_seed = int(run_seed)
        self.temperature = float(temperature)
        self.long_run_diagnostics_enabled = bool(long_run_diagnostics_enabled)
        self.long_run_diagnostics_schema = str(long_run_diagnostics_schema)
        self.morphology_trait_indices = tuple(int(value) for value in morphology_trait_indices)
        self.morphology_trait_names = tuple(str(value) for value in morphology_trait_names)
        if len(self.morphology_trait_indices) != len(self.morphology_trait_names):
            raise ValueError("morphology trait indices and names must be aligned")
        active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
        sampled = _deterministic_sample(active, stable_ids, self.run_seed, 4096)
        self.initial_stable_ids = np.asarray(stable_ids[sampled], dtype=np.uint64).copy()
        self.initial_genotype = np.asarray(genotype[sampled], dtype=np.float32).copy()
        initial_strategy = self.initial_genotype[
            :, ParametricPolicy.STRATEGY_START : ParametricPolicy.STRATEGY_STOP
        ].astype(np.float64).reshape(
            sampled.size,
            len(Action),
            ParametricPolicy.STRATEGY_FEATURES,
        )
        initial_canonical = initial_strategy - initial_strategy.mean(
            axis=1, keepdims=True
        )
        self.initial_strategy_mean = initial_canonical.reshape(
            sampled.size, -1
        ).mean(axis=0) if sampled.size else np.zeros(
            ParametricPolicy.STRATEGY_GENES, dtype=np.float64
        )
        self.previous_strategy_mean = self.initial_strategy_mean.copy()
        self.baseline: dict[str, float | int] | None = None
        self.previous_tick = 0
        self.previous_births = 0
        self.previous_deaths = 0
        self.previous_action_counts = np.zeros(len(Action), dtype=np.int64)
        self.previous_benefit_flow_totals = np.zeros(
            BENEFIT_FLOW_COUNT, dtype=np.float64
        )
        self.previous_lagged_benefit_flow_totals = np.zeros(
            BENEFIT_FLOW_COUNT, dtype=np.float64
        )
        self.previous_shared_energy = 0.0
        self.previous_harvested_resources = np.zeros(4, dtype=np.float64)
        self.previous_reproduction_eligible = 0
        self.previous_reproduction_proposals = 0
        self.previous_reproduction_rejected_capacity = 0
        self.previous_reproduction_rejected_resource = 0
        self.previous_reproduction_rejected_other = 0
        self.previous_knowledge_transfer_totals: dict[str, float] = {}
        width = len(self.morphology_trait_indices)
        self.reproduction_eligible_trait_sum = np.zeros(width, dtype=np.float64)
        self.reproduction_parent_trait_sum = np.zeros(width, dtype=np.float64)
        self.reproduction_offspring_trait_sum = np.zeros(width, dtype=np.float64)
        self.reproduction_eligible_trait_count = 0
        self.reproduction_parent_trait_count = 0
        self.reproduction_offspring_trait_count = 0
        self.previous_reproduction_eligible_trait_sum = np.zeros(width, dtype=np.float64)
        self.previous_reproduction_parent_trait_sum = np.zeros(width, dtype=np.float64)
        self.previous_reproduction_offspring_trait_sum = np.zeros(width, dtype=np.float64)
        self.previous_reproduction_eligible_trait_count = 0
        self.previous_reproduction_parent_trait_count = 0
        self.previous_reproduction_offspring_trait_count = 0
        self.records: list[dict[str, Any]] = []
        self._file = None

    def snapshot_state(self) -> dict[str, Any]:
        """Return writer-free progress state for exact continuation."""
        return {
            name: copy.deepcopy(value)
            for name, value in self.__dict__.items()
            if name not in {"path", "_file"}
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore progress counters while retaining this run's output path."""
        for name, value in state.items():
            setattr(self, name, copy.deepcopy(value))
        if not hasattr(self, "previous_knowledge_transfer_totals"):
            self.previous_knowledge_transfer_totals = {}
        self._file = None

    def clone(self, output_dir: str | Path) -> "EvolutionProgressTracker":
        branch = copy.copy(self)
        branch.path = Path(output_dir) / "evolution_progress.jsonl"
        branch.previous_strategy_mean = self.previous_strategy_mean.copy()
        branch.initial_strategy_mean = self.initial_strategy_mean.copy()
        branch.previous_action_counts = self.previous_action_counts.copy()
        branch.previous_benefit_flow_totals = (
            self.previous_benefit_flow_totals.copy()
        )
        branch.previous_lagged_benefit_flow_totals = (
            self.previous_lagged_benefit_flow_totals.copy()
        )
        branch.previous_harvested_resources = (
            self.previous_harvested_resources.copy()
        )
        branch.previous_knowledge_transfer_totals = dict(
            self.previous_knowledge_transfer_totals
        )
        for name in (
            "reproduction_eligible_trait_sum",
            "reproduction_parent_trait_sum",
            "reproduction_offspring_trait_sum",
            "previous_reproduction_eligible_trait_sum",
            "previous_reproduction_parent_trait_sum",
            "previous_reproduction_offspring_trait_sum",
        ):
            setattr(branch, name, getattr(self, name).copy())
        branch.initial_stable_ids = self.initial_stable_ids.copy()
        branch.initial_genotype = self.initial_genotype.copy()
        branch.baseline = copy.deepcopy(self.baseline)
        branch.records = copy.deepcopy(self.records)
        branch._file = None
        return branch

    def observe_reproduction_traits(
        self,
        genotype: np.ndarray,
        *,
        eligible_indices: np.ndarray,
        accepted_parent_indices: np.ndarray,
        newborn_indices: np.ndarray,
    ) -> None:
        """Accumulate observational trait cohorts for the next report window."""
        if not self.long_run_diagnostics_enabled or not self.morphology_trait_indices:
            return
        values = np.asarray(genotype, dtype=np.float32)
        columns = np.asarray(self.morphology_trait_indices, dtype=np.int32)

        def accumulate(indices: np.ndarray, sum_name: str, count_name: str) -> None:
            rows = np.asarray(indices, dtype=np.int32)
            if rows.size == 0:
                return
            cohort = values[np.ix_(rows, columns)].astype(np.float64, copy=False)
            setattr(self, sum_name, getattr(self, sum_name) + cohort.sum(axis=0))
            setattr(self, count_name, int(getattr(self, count_name)) + int(rows.size))

        accumulate(
            eligible_indices,
            "reproduction_eligible_trait_sum",
            "reproduction_eligible_trait_count",
        )
        accumulate(
            accepted_parent_indices,
            "reproduction_parent_trait_sum",
            "reproduction_parent_trait_count",
        )
        accumulate(
            newborn_indices,
            "reproduction_offspring_trait_sum",
            "reproduction_offspring_trait_count",
        )

    def _writer(self):
        if self._file is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self.path.open("w", encoding="utf-8")
            for record in self.records:
                self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return self._file

    def due(self, tick: int) -> bool:
        return tick > 0 and tick % self.period == 0

    def record(
        self,
        *,
        tick: int,
        scheduled: bool,
        alive: np.ndarray,
        stable_ids: np.ndarray,
        lineage_ids: np.ndarray,
        group_ids: np.ndarray | None,
        generation: np.ndarray,
        genotype: np.ndarray,
        births_total: int,
        deaths_total: int,
        action_counts: np.ndarray,
        benefit_flow_energy_total: np.ndarray,
        lagged_benefit_flow_energy_total: np.ndarray,
        lagged_benefit_boundary_snapshot_tick: int,
        shared_energy_total: float,
        harvested_resources_total: np.ndarray,
        reproduction_eligible_total: int,
        reproduction_proposals_total: int,
        reproduction_rejected_capacity_total: int,
        reproduction_rejected_resource_total: int,
        reproduction_rejected_other_total: int,
        mutation_probability: float,
        mutation_std: float,
        actual_context_metrics: dict[str, Any] | None = None,
        environment_metrics: dict[str, Any] | None = None,
        spatial_stress_metrics: dict[str, Any] | None = None,
        knowledge_metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.records and int(self.records[-1]["tick"]) == int(tick):
            return self.records[-1]
        structure, strategy_mean = strategy_structure(
            alive,
            stable_ids,
            genotype,
            run_seed=self.run_seed,
            temperature=self.temperature,
        )
        if self.baseline is None:
            self.baseline, _ = strategy_structure(
                np.ones(self.initial_stable_ids.size, dtype=bool),
                self.initial_stable_ids,
                self.initial_genotype,
                run_seed=self.run_seed,
                temperature=self.temperature,
                sample_capacity=max(self.initial_stable_ids.size, 1),
                compute_effective_dimensions=False,
            )
        active = np.flatnonzero(alive).astype(np.int32)
        if active.size:
            _, counts = np.unique(lineage_ids[active], return_counts=True)
            lineage_count = int(counts.size)
            share = counts.astype(np.float64) / active.size
            effective_lineages = float(1.0 / np.sum(share * share))
            largest_lineage_fraction = float(share.max())
            mean_generation = float(np.mean(generation[active]))
            max_generation = int(np.max(generation[active]))
        else:
            lineage_count = 0
            effective_lineages = largest_lineage_fraction = mean_generation = 0.0
            max_generation = 0

        action_delta = np.asarray(action_counts, dtype=np.int64) - self.previous_action_counts
        action_total = int(action_delta.sum())
        if action_total:
            action_share = action_delta.astype(np.float64) / action_total
            action_entropy = float(_entropy(action_share))
        else:
            action_entropy = 0.0
        benefit_totals = np.asarray(benefit_flow_energy_total, dtype=np.float64)
        if benefit_totals.shape != (BENEFIT_FLOW_COUNT,):
            raise ValueError("benefit flow totals must contain every BenefitFlowKind")
        benefit_window = benefit_totals - self.previous_benefit_flow_totals
        shared_energy_window = float(
            shared_energy_total - self.previous_shared_energy
        )
        internal_window = float(benefit_window[BenefitFlowKind.INTERNAL])
        group_to_group_window = float(
            benefit_window[BenefitFlowKind.GROUP_TO_GROUP]
        )
        group_to_ungrouped_window = float(
            benefit_window[BenefitFlowKind.GROUP_TO_UNGROUPED]
        )
        ungrouped_to_group_window = float(
            benefit_window[BenefitFlowKind.UNGROUPED_TO_GROUP]
        )
        unbounded_window = float(benefit_window[BenefitFlowKind.UNBOUNDED])
        cross_window = (
            group_to_group_window
            + group_to_ungrouped_window
            + ungrouped_to_group_window
        )
        boundary_total = internal_window + cross_window
        all_benefit = boundary_total + unbounded_window
        outgoing_boundary_total = (
            internal_window + group_to_group_window + group_to_ungrouped_window
        )
        lagged_benefit_totals = np.asarray(
            lagged_benefit_flow_energy_total, dtype=np.float64
        )
        if lagged_benefit_totals.shape != (BENEFIT_FLOW_COUNT,):
            raise ValueError(
                "lagged benefit flow totals must contain every BenefitFlowKind"
            )
        lagged_window = (
            lagged_benefit_totals - self.previous_lagged_benefit_flow_totals
        )
        lagged_internal = float(lagged_window[BenefitFlowKind.INTERNAL])
        lagged_group_to_group = float(
            lagged_window[BenefitFlowKind.GROUP_TO_GROUP]
        )
        lagged_group_to_ungrouped = float(
            lagged_window[BenefitFlowKind.GROUP_TO_UNGROUPED]
        )
        lagged_ungrouped_to_group = float(
            lagged_window[BenefitFlowKind.UNGROUPED_TO_GROUP]
        )
        lagged_unbounded = float(lagged_window[BenefitFlowKind.UNBOUNDED])
        lagged_cross = (
            lagged_group_to_group
            + lagged_group_to_ungrouped
            + lagged_ungrouped_to_group
        )
        lagged_boundary_total = lagged_internal + lagged_cross
        lagged_all_benefit = lagged_boundary_total + lagged_unbounded
        lagged_outgoing_total = (
            lagged_internal
            + lagged_group_to_group
            + lagged_group_to_ungrouped
        )
        reproduction_eligible_window = int(
            reproduction_eligible_total - self.previous_reproduction_eligible
        )
        reproduction_proposals_window = int(
            reproduction_proposals_total - self.previous_reproduction_proposals
        )
        reproduction_rejected_capacity_window = int(
            reproduction_rejected_capacity_total
            - self.previous_reproduction_rejected_capacity
        )
        reproduction_rejected_resource_window = int(
            reproduction_rejected_resource_total
            - self.previous_reproduction_rejected_resource
        )
        reproduction_rejected_other_window = int(
            reproduction_rejected_other_total
            - self.previous_reproduction_rejected_other
        )
        harvested_totals = np.asarray(
            harvested_resources_total, dtype=np.float64
        )
        if harvested_totals.shape != (4,):
            raise ValueError("harvested resource totals must contain four channels")
        harvested_window = harvested_totals - self.previous_harvested_resources
        harvested_window_total = float(harvested_window.sum())
        harvested_window_share = (
            harvested_window / harvested_window_total
            if harvested_window_total > 0.0
            else np.zeros(4, dtype=np.float64)
        )
        reproduction_accepted_window = int(births_total - self.previous_births)
        reproduction_accounting_residual = int(
            reproduction_proposals_window
            - reproduction_accepted_window
            - reproduction_rejected_capacity_window
            - reproduction_rejected_resource_window
            - reproduction_rejected_other_window
        )
        baseline_canonical = float(self.baseline["canonical_strategy_diversity"])
        baseline_probability = float(self.baseline["policy_probability_diversity"])
        policy_shift = float(np.linalg.norm(strategy_mean - self.previous_strategy_mean))
        cumulative_policy_shift = float(
            np.linalg.norm(strategy_mean - self.initial_strategy_mean)
        )
        long_run_metrics: dict[str, Any] = {}
        if self.long_run_diagnostics_enabled:
            if group_ids is None:
                raise ValueError("long-run diagnostics require group IDs")
            long_run_metrics.update(
                {
                    "long_run_diagnostics_schema": self.long_run_diagnostics_schema,
                    "mortality_pressure_window": (
                        int(deaths_total - self.previous_deaths)
                        / max(int(active.size) + int(deaths_total - self.previous_deaths), 1)
                    ),
                    "birth_pressure_window": (
                        int(births_total - self.previous_births)
                        / max(int(active.size), 1)
                    ),
                    **lineage_group_diagnostics(alive, lineage_ids, group_ids),
                }
            )

            def cohort_window(
                total_sum: np.ndarray,
                previous_sum: np.ndarray,
                total_count: int,
                previous_count: int,
            ) -> tuple[np.ndarray, int]:
                count = int(total_count - previous_count)
                delta = np.asarray(total_sum, dtype=np.float64) - np.asarray(
                    previous_sum, dtype=np.float64
                )
                return (
                    delta / count if count > 0 else np.zeros_like(delta),
                    count,
                )

            eligible_mean, eligible_count = cohort_window(
                self.reproduction_eligible_trait_sum,
                self.previous_reproduction_eligible_trait_sum,
                self.reproduction_eligible_trait_count,
                self.previous_reproduction_eligible_trait_count,
            )
            parent_mean, parent_count = cohort_window(
                self.reproduction_parent_trait_sum,
                self.previous_reproduction_parent_trait_sum,
                self.reproduction_parent_trait_count,
                self.previous_reproduction_parent_trait_count,
            )
            offspring_mean, offspring_count = cohort_window(
                self.reproduction_offspring_trait_sum,
                self.previous_reproduction_offspring_trait_sum,
                self.reproduction_offspring_trait_count,
                self.previous_reproduction_offspring_trait_count,
            )
            long_run_metrics.update(
                {
                    "selection_trait_names": list(self.morphology_trait_names),
                    "selection_eligible_carrier_samples_window": eligible_count,
                    "selection_successful_parent_samples_window": parent_count,
                    "selection_offspring_samples_window": offspring_count,
                    "selection_eligible_trait_mean_window": eligible_mean.tolist(),
                    "selection_successful_parent_trait_mean_window": parent_mean.tolist(),
                    "selection_offspring_trait_mean_window": offspring_mean.tolist(),
                    "selection_differential_parent_minus_eligible": (
                        parent_mean - eligible_mean
                    ).tolist(),
                    "selection_transmission_offspring_minus_parent": (
                        offspring_mean - parent_mean
                    ).tolist(),
                }
            )
            knowledge_payload = dict(knowledge_metrics or {})
            for total_key in KNOWLEDGE_TRANSFER_TOTAL_KEYS:
                if total_key not in knowledge_payload:
                    continue
                current = float(knowledge_payload[total_key])
                previous = float(
                    self.previous_knowledge_transfer_totals.get(total_key, 0.0)
                )
                window_key = total_key.removesuffix("_total") + "_window"
                delta = current - previous
                if total_key.endswith("_energy_total"):
                    knowledge_payload[window_key] = float(delta)
                else:
                    knowledge_payload[window_key] = int(round(delta))
            long_run_metrics.update(knowledge_payload)
        record: dict[str, Any] = {
            "tick": int(tick),
            "scheduled": bool(scheduled),
            "window_ticks": int(tick - self.previous_tick),
            "alive": int(active.size),
            "births_window": int(births_total - self.previous_births),
            "deaths_window": int(deaths_total - self.previous_deaths),
            "mean_generation": mean_generation,
            "max_generation": max_generation,
            "lineage_count": lineage_count,
            "effective_lineages": effective_lineages,
            "effective_lineages_per_alive": (
                effective_lineages / active.size if active.size else 0.0
            ),
            "largest_lineage_fraction": largest_lineage_fraction,
            "window_action_entropy": action_entropy,
            "window_action_counts": action_delta.tolist(),
            "action_names": [action.name for action in Action],
            "strategy_feature_names": list(ParametricPolicy.FEATURE_NAMES),
            "harvested_resources_window": harvested_window.tolist(),
            "harvested_resource_share_window": harvested_window_share.tolist(),
            "mean_strategy_shift_l2": policy_shift,
            "mean_strategy_shift_from_initial_l2": cumulative_policy_shift,
            "canonical_diversity_ratio_to_initial": (
                float(structure["canonical_strategy_diversity"]) / baseline_canonical
                if baseline_canonical
                else 0.0
            ),
            "policy_diversity_ratio_to_initial": (
                float(structure["policy_probability_diversity"])
                / baseline_probability
                if baseline_probability
                else 0.0
            ),
            "reproduction_eligible_carrier_ticks_window": (
                reproduction_eligible_window
            ),
            "reproduction_proposals_window": reproduction_proposals_window,
            "reproduction_accepted_window": reproduction_accepted_window,
            "reproduction_rejected_capacity_window": (
                reproduction_rejected_capacity_window
            ),
            "reproduction_rejected_resource_window": (
                reproduction_rejected_resource_window
            ),
            "reproduction_rejected_other_window": (
                reproduction_rejected_other_window
            ),
            "reproduction_accounting_residual_window": (
                reproduction_accounting_residual
            ),
            "reproduction_proposal_rate_given_eligible": (
                reproduction_proposals_window / reproduction_eligible_window
                if reproduction_eligible_window
                else 0.0
            ),
            "reproduction_acceptance_rate": (
                reproduction_accepted_window / reproduction_proposals_window
                if reproduction_proposals_window
                else 0.0
            ),
            "benefit_internal_window": internal_window,
            "benefit_group_to_group_window": group_to_group_window,
            "benefit_group_to_ungrouped_window": group_to_ungrouped_window,
            "benefit_ungrouped_to_group_window": ungrouped_to_group_window,
            "benefit_cross_boundary_window": cross_window,
            "benefit_unbounded_window": unbounded_window,
            "benefit_total_window": shared_energy_window,
            "benefit_classification_residual_window": (
                shared_energy_window - float(benefit_window.sum())
            ),
            "benefit_boundary_coverage": (
                boundary_total / all_benefit if all_benefit > 0.0 else 0.0
            ),
            "benefit_boundary_cohesion": (
                internal_window / boundary_total if boundary_total > 0.0 else 0.0
            ),
            "benefit_boundary_outgoing_retention": (
                internal_window / outgoing_boundary_total
                if outgoing_boundary_total > 0.0
                else 0.0
            ),
            "lagged_benefit_boundary_snapshot_tick": int(
                lagged_benefit_boundary_snapshot_tick
            ),
            "lagged_benefit_internal_window": lagged_internal,
            "lagged_benefit_group_to_group_window": lagged_group_to_group,
            "lagged_benefit_group_to_ungrouped_window": (
                lagged_group_to_ungrouped
            ),
            "lagged_benefit_ungrouped_to_group_window": (
                lagged_ungrouped_to_group
            ),
            "lagged_benefit_cross_boundary_window": lagged_cross,
            "lagged_benefit_unbounded_window": lagged_unbounded,
            "lagged_benefit_classification_residual_window": (
                shared_energy_window - float(lagged_window.sum())
            ),
            "lagged_benefit_boundary_coverage": (
                lagged_boundary_total / lagged_all_benefit
                if lagged_all_benefit > 0.0
                else 0.0
            ),
            "lagged_benefit_boundary_cohesion": (
                lagged_internal / lagged_boundary_total
                if lagged_boundary_total > 0.0
                else 0.0
            ),
            "lagged_benefit_boundary_outgoing_retention": (
                lagged_internal / lagged_outgoing_total
                if lagged_outgoing_total > 0.0
                else 0.0
            ),
            "mutation_probability_per_gene": float(mutation_probability),
            "mutation_std_conditional": float(mutation_std),
            "expected_strategy_genes_mutated_per_birth": float(
                mutation_probability * ParametricPolicy.STRATEGY_GENES
            ),
            **structure,
            **(actual_context_metrics or {}),
            **(environment_metrics or {}),
            **(spatial_stress_metrics or {}),
            **long_run_metrics,
        }
        writer = self._writer()
        self.records.append(record)
        writer.write(json.dumps(record, ensure_ascii=False) + "\n")
        writer.flush()
        self.previous_tick = int(tick)
        self.previous_births = int(births_total)
        self.previous_deaths = int(deaths_total)
        self.previous_action_counts = np.asarray(action_counts, dtype=np.int64).copy()
        self.previous_benefit_flow_totals = benefit_totals.copy()
        self.previous_lagged_benefit_flow_totals = lagged_benefit_totals.copy()
        self.previous_shared_energy = float(shared_energy_total)
        self.previous_harvested_resources = harvested_totals.copy()
        self.previous_reproduction_eligible = int(reproduction_eligible_total)
        self.previous_reproduction_proposals = int(reproduction_proposals_total)
        self.previous_reproduction_rejected_capacity = int(
            reproduction_rejected_capacity_total
        )
        self.previous_reproduction_rejected_resource = int(
            reproduction_rejected_resource_total
        )
        self.previous_reproduction_rejected_other = int(
            reproduction_rejected_other_total
        )
        if self.long_run_diagnostics_enabled:
            if knowledge_metrics:
                for total_key in KNOWLEDGE_TRANSFER_TOTAL_KEYS:
                    if total_key in knowledge_metrics:
                        self.previous_knowledge_transfer_totals[total_key] = float(
                            knowledge_metrics[total_key]
                        )
            self.previous_reproduction_eligible_trait_sum = (
                self.reproduction_eligible_trait_sum.copy()
            )
            self.previous_reproduction_parent_trait_sum = (
                self.reproduction_parent_trait_sum.copy()
            )
            self.previous_reproduction_offspring_trait_sum = (
                self.reproduction_offspring_trait_sum.copy()
            )
            self.previous_reproduction_eligible_trait_count = int(
                self.reproduction_eligible_trait_count
            )
            self.previous_reproduction_parent_trait_count = int(
                self.reproduction_parent_trait_count
            )
            self.previous_reproduction_offspring_trait_count = int(
                self.reproduction_offspring_trait_count
            )
        self.previous_strategy_mean = strategy_mean
        return record

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


__all__ = [
    "BENEFIT_FLOW_COUNT",
    "BenefitFlowKind",
    "EvolutionProgressTracker",
    "LaggedBenefitBoundary",
    "benefit_flow_totals",
    "actual_context_policy_diagnostics",
    "strategy_structure",
]
