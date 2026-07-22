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
        genotype[sampled, ParametricPolicy.MORPHOLOGY_TRAITS :],
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
    ) -> None:
        self.path = Path(output_dir) / "evolution_progress.jsonl"
        self.period = int(period)
        self.run_seed = int(run_seed)
        self.temperature = float(temperature)
        active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
        sampled = _deterministic_sample(active, stable_ids, self.run_seed, 4096)
        self.initial_stable_ids = np.asarray(stable_ids[sampled], dtype=np.uint64).copy()
        self.initial_genotype = np.asarray(genotype[sampled], dtype=np.float32).copy()
        initial_strategy = self.initial_genotype[
            :, ParametricPolicy.MORPHOLOGY_TRAITS :
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
        self.previous_shared_energy = 0.0
        self.previous_reproduction_eligible = 0
        self.previous_reproduction_proposals = 0
        self.previous_reproduction_rejected_capacity = 0
        self.previous_reproduction_rejected_resource = 0
        self.previous_reproduction_rejected_other = 0
        self.records: list[dict[str, Any]] = []
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
        branch.initial_stable_ids = self.initial_stable_ids.copy()
        branch.initial_genotype = self.initial_genotype.copy()
        branch.baseline = copy.deepcopy(self.baseline)
        branch.records = copy.deepcopy(self.records)
        branch._file = None
        return branch

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
        generation: np.ndarray,
        genotype: np.ndarray,
        births_total: int,
        deaths_total: int,
        action_counts: np.ndarray,
        benefit_flow_energy_total: np.ndarray,
        shared_energy_total: float,
        reproduction_eligible_total: int,
        reproduction_proposals_total: int,
        reproduction_rejected_capacity_total: int,
        reproduction_rejected_resource_total: int,
        reproduction_rejected_other_total: int,
        mutation_probability: float,
        mutation_std: float,
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
            "mutation_probability_per_gene": float(mutation_probability),
            "mutation_std_conditional": float(mutation_std),
            "expected_strategy_genes_mutated_per_birth": float(
                mutation_probability * ParametricPolicy.STRATEGY_GENES
            ),
            **structure,
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
        self.previous_shared_energy = float(shared_energy_total)
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
    "benefit_flow_totals",
    "strategy_structure",
]
