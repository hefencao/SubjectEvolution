"""Temporal mediation audit for lineage-conditioned D2 module effects.

D2-E confirmed a routed-output effect for a fixed module on target-lineage mean
energy without establishing positive ecological persistence or copy-number
readiness.  This experiment preserves every preselected checkpoint-lineage pair
for the confirmed module and observes the same paired branches at multiple
post-intervention offsets.  The read-only trajectory captures energy stock,
harvest/share flows, reproduction readiness, births, deaths, source survivors
and descendants so a survivor-conditioned mean cannot be mistaken for a causal
ecological benefit.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from se.evolution.lifecycle import DeathCause
from se.experiments.d2_lineage_pairs import (
    BRANCHES,
    EFFECTS,
    PLAN_SCHEMAS as LINEAGE_PAIR_PLAN_SCHEMAS,
    LineagePairCheckpoint,
    LineageSelection,
    load_lineage_pair_plan,
)
from se.runtime.sim import Simulation
from se.runtime.reproduction import reproduction_energy_requirement
from se.runtime.state import StepStats

PLAN_SCHEMA = "d2-lineage-mediation-plan-v1"
RESULT_SCHEMA = "d2-lineage-mediation-results-v1"
ASSESSMENT_SCHEMA = "d2-lineage-paired-assessment-v1"
DEFAULT_OBSERVATION_OFFSETS = (30, 60, 120, 180, 240, 300)
SELECTION_RULE = (
    "module-level-confirmed-output-preserve-all-preselected-checkpoint-lineage-pairs-v1"
)
TRAJECTORY_SCHEMA = "lineage-energy-demography-mediation-trajectory-v1"


@dataclass(frozen=True)
class LineageMediationPlan:
    schema: str
    source_assessment_schema: str
    source_assessment_sha256: str | None
    source_persistent_output_expectations: dict[str, dict[str, int]]
    source_plan_schema: str
    source_plan_horizon_ticks: int
    module_indices: tuple[int, ...]
    observation_offsets: tuple[int, ...]
    checkpoints: tuple[LineagePairCheckpoint, ...]
    branches: tuple[str, ...] = BRANCHES
    effect_decomposition_schema: str = "output-cost-total-additive-v1"
    trajectory_schema: str = TRAJECTORY_SCHEMA
    selection_rule: str = SELECTION_RULE
    outcome_conditioned_pair_selection: bool = False
    preserves_all_source_pairs_for_selected_modules: bool = True
    genotype_preserved: bool = True
    lineage_membership_preserved: bool = True
    copy_number_changed: bool = False
    routing_vocabulary_changed: bool = False


def _normalize_offsets(values: Iterable[int]) -> tuple[int, ...]:
    offsets = tuple(sorted({int(value) for value in values}))
    if not offsets or offsets[0] <= 0:
        raise ValueError("observation offsets must contain positive tick counts")
    return offsets


def _normalize_modules(values: Iterable[int]) -> tuple[int, ...]:
    modules = tuple(sorted({int(value) for value in values}))
    if not modules:
        raise ValueError("at least one confirmed module is required")
    return modules


def _load_assessment(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != ASSESSMENT_SCHEMA:
        raise ValueError(
            f"unsupported D2 lineage-pair assessment: {payload.get('schema')!r}"
        )
    if not payload.get("confirmed_modules"):
        raise ValueError("assessment contains no cross-horizon confirmed modules")
    return payload


def build_mediation_plan(
    assessment: dict[str, Any],
    source_plan_path: str | Path,
    *,
    observation_offsets: Iterable[int] = DEFAULT_OBSERVATION_OFFSETS,
    source_assessment_sha256: str | None = None,
) -> LineageMediationPlan:
    if assessment.get("schema") != ASSESSMENT_SCHEMA:
        raise ValueError(
            f"unsupported D2 lineage-pair assessment: {assessment.get('schema')!r}"
        )
    modules = _normalize_modules(assessment.get("confirmed_modules", ()))
    expectations: dict[str, dict[str, int]] = {}
    for module_index in modules:
        module_name = f"module_{module_index}"
        module = assessment.get("modules", {}).get(module_name, {})
        routed = module.get("effects", {}).get("output_routing_effect", {})
        expected: dict[str, int] = {}
        for outcome in module.get("persistent_output_outcomes", ()):
            metric = routed.get(outcome, {})
            sign = int(metric.get("persistent_sign", 0))
            if sign != 0:
                expected[str(outcome)] = sign
        expectations[module_name] = expected
    offsets = _normalize_offsets(observation_offsets)
    source = load_lineage_pair_plan(source_plan_path)
    if source.schema not in LINEAGE_PAIR_PLAN_SCHEMAS:
        raise ValueError(f"unsupported source lineage-pair plan: {source.schema!r}")
    missing = sorted(set(modules) - set(source.module_indices))
    if missing:
        raise ValueError(
            "confirmed modules are absent from the source confirmation plan: "
            + ", ".join(map(str, missing))
        )
    if max(offsets) > int(source.horizon_ticks):
        raise ValueError(
            "mediation observation horizon exceeds the completed source plan horizon"
        )
    checkpoints = tuple(
        replace(
            checkpoint,
            until_tick=int(checkpoint.checkpoint_tick) + max(offsets),
        )
        for checkpoint in source.checkpoints
    )
    if not checkpoints:
        raise ValueError("source confirmation plan contains no checkpoints")
    if any(not checkpoint.lineages for checkpoint in checkpoints):
        raise ValueError("every mediation checkpoint must retain preselected lineages")
    return LineageMediationPlan(
        schema=PLAN_SCHEMA,
        source_assessment_schema=str(assessment["schema"]),
        source_assessment_sha256=source_assessment_sha256,
        source_persistent_output_expectations=expectations,
        source_plan_schema=str(source.schema),
        source_plan_horizon_ticks=int(source.horizon_ticks),
        module_indices=modules,
        observation_offsets=offsets,
        checkpoints=checkpoints,
    )


def load_mediation_plan(path: str | Path) -> LineageMediationPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported D2 mediation plan: {payload.get('schema')!r}")
    checkpoints: list[LineagePairCheckpoint] = []
    for item in payload.get("checkpoints", ()):
        lineages = tuple(LineageSelection(**row) for row in item.get("lineages", ()))
        checkpoints.append(LineagePairCheckpoint(**{**item, "lineages": lineages}))
    if not checkpoints:
        raise ValueError("D2 mediation plan contains no checkpoints")
    return LineageMediationPlan(
        schema=str(payload["schema"]),
        source_assessment_schema=str(payload["source_assessment_schema"]),
        source_assessment_sha256=(
            str(payload["source_assessment_sha256"])
            if payload.get("source_assessment_sha256") is not None
            else None
        ),
        source_persistent_output_expectations={
            str(module): {str(outcome): int(sign) for outcome, sign in values.items()}
            for module, values in payload.get(
                "source_persistent_output_expectations", {}
            ).items()
        },
        source_plan_schema=str(payload["source_plan_schema"]),
        source_plan_horizon_ticks=int(payload["source_plan_horizon_ticks"]),
        module_indices=_normalize_modules(payload["module_indices"]),
        observation_offsets=_normalize_offsets(payload["observation_offsets"]),
        checkpoints=tuple(checkpoints),
        branches=tuple(payload.get("branches", BRANCHES)),
        effect_decomposition_schema=str(
            payload.get("effect_decomposition_schema", "output-cost-total-additive-v1")
        ),
        trajectory_schema=str(payload.get("trajectory_schema", TRAJECTORY_SCHEMA)),
        selection_rule=str(payload.get("selection_rule", SELECTION_RULE)),
        outcome_conditioned_pair_selection=bool(
            payload.get("outcome_conditioned_pair_selection", False)
        ),
        preserves_all_source_pairs_for_selected_modules=bool(
            payload.get("preserves_all_source_pairs_for_selected_modules", True)
        ),
        genotype_preserved=bool(payload.get("genotype_preserved", True)),
        lineage_membership_preserved=bool(
            payload.get("lineage_membership_preserved", True)
        ),
        copy_number_changed=bool(payload.get("copy_number_changed", False)),
        routing_vocabulary_changed=bool(
            payload.get("routing_vocabulary_changed", False)
        ),
    )


class _LineageTrajectoryObserver:
    """Read-only per-lineage event and state observer for one branch."""

    def __init__(
        self,
        *,
        lineage_ids: Sequence[int],
        source_members: dict[int, int],
        checkpoint_tick: int,
        observation_offsets: Sequence[int],
    ) -> None:
        self.lineage_ids = tuple(int(value) for value in lineage_ids)
        self.source_members = {int(key): int(value) for key, value in source_members.items()}
        self.checkpoint_tick = int(checkpoint_tick)
        self.snapshot_ticks = {
            self.checkpoint_tick + int(offset): int(offset)
            for offset in observation_offsets
        }
        self.initial_ids: dict[int, set[int]] = {}
        self.previous: dict[int, dict[int, tuple[int, float, float]]] = {}
        self.births = {lineage: 0 for lineage in self.lineage_ids}
        self.deaths = {lineage: 0 for lineage in self.lineage_ids}
        self.energy_deaths = {lineage: 0 for lineage in self.lineage_ids}
        self.integrity_deaths = {lineage: 0 for lineage in self.lineage_ids}
        self.age_deaths = {lineage: 0 for lineage in self.lineage_ids}
        self.harvested = {lineage: 0.0 for lineage in self.lineage_ids}
        self.shared = {lineage: 0.0 for lineage in self.lineage_ids}
        self.snapshots: dict[int, list[dict[str, Any]]] = {
            lineage: [] for lineage in self.lineage_ids
        }
        self.initialized = False

    @staticmethod
    def _rows(simulation: Simulation, lineage_id: int) -> np.ndarray:
        return np.flatnonzero(
            simulation.entities.alive
            & (simulation.entities.lineage_id == np.uint64(lineage_id))
        ).astype(np.int32)

    def _state_map(
        self, simulation: Simulation, lineage_id: int
    ) -> dict[int, tuple[int, float, float]]:
        rows = self._rows(simulation, lineage_id)
        return {
            int(simulation.entities.entity_id[row]): (
                int(row),
                float(simulation.entities.harvested_energy_total[row]),
                float(simulation.entities.shared_energy_received_total[row]),
            )
            for row in rows
        }

    def _initialize(self, simulation: Simulation) -> None:
        if int(simulation.tick) != self.checkpoint_tick:
            raise ValueError(
                "mediation observer checkpoint tick mismatch: "
                f"{simulation.tick} vs {self.checkpoint_tick}"
            )
        for lineage_id in self.lineage_ids:
            state = self._state_map(simulation, lineage_id)
            expected = self.source_members[lineage_id]
            if len(state) != expected:
                raise ValueError(
                    "mediation source lineage membership changed before intervention: "
                    f"lineage={lineage_id}, expected={expected}, observed={len(state)}"
                )
            self.previous[lineage_id] = state
            self.initial_ids[lineage_id] = set(state)
        self.initialized = True

    def _accumulate_events(self, simulation: Simulation) -> None:
        ent = simulation.entities
        death_plan = simulation.last_death_events
        death_causes = {
            int(slot): int(cause)
            for slot, cause in zip(
                np.asarray(death_plan.entity_indices, dtype=np.int32),
                np.asarray(death_plan.cause_code, dtype=np.uint8),
            )
        }
        for lineage_id in self.lineage_ids:
            previous = self.previous[lineage_id]
            current = self._state_map(simulation, lineage_id)
            previous_ids = set(previous)
            current_ids = set(current)
            born = current_ids - previous_ids
            died = previous_ids - current_ids
            self.births[lineage_id] += len(born)
            self.deaths[lineage_id] += len(died)

            for entity_id, (slot, old_harvested, old_shared) in previous.items():
                after_entity_id = int(ent.entity_id[slot])
                if after_entity_id not in (0, entity_id):
                    raise RuntimeError(
                        "entity slot was reused within one observed step; mediation flow "
                        "accounting would be ambiguous"
                    )
                harvested_now = float(ent.harvested_energy_total[slot])
                shared_now = float(ent.shared_energy_received_total[slot])
                self.harvested[lineage_id] += harvested_now - old_harvested
                self.shared[lineage_id] += shared_now - old_shared
                if entity_id in died:
                    cause = death_causes.get(slot, 0)
                    if cause & int(DeathCause.ENERGY_DEPLETED):
                        self.energy_deaths[lineage_id] += 1
                    if cause & int(DeathCause.INTEGRITY_DEPLETED):
                        self.integrity_deaths[lineage_id] += 1
                    if cause & int(DeathCause.MAX_AGE):
                        self.age_deaths[lineage_id] += 1

            for entity_id in born:
                _, harvested_now, shared_now = current[entity_id]
                self.harvested[lineage_id] += harvested_now
                self.shared[lineage_id] += shared_now
            self.previous[lineage_id] = current

    @staticmethod
    def _safe_mean(values: np.ndarray) -> float:
        return float(values.mean()) if values.size else 0.0

    @staticmethod
    def _safe_quantile(values: np.ndarray, q: float) -> float:
        return float(np.quantile(values, q)) if values.size else 0.0

    def _snapshot(self, simulation: Simulation, lineage_id: int, offset: int) -> dict[str, Any]:
        ent = simulation.entities
        rows = self._rows(simulation, lineage_id)
        world_rows = np.flatnonzero(ent.alive).astype(np.int32)
        ids = {int(value) for value in ent.entity_id[rows]}
        source_survivors = len(ids & self.initial_ids[lineage_id])
        energy = np.asarray(ent.energy[rows], dtype=np.float64)
        fertility = np.asarray(ent.fertility[rows], dtype=np.float64)
        age = np.asarray(ent.age[rows], dtype=np.float64)
        generation = np.asarray(ent.generation[rows], dtype=np.float64)
        material = np.asarray(ent.material[rows], dtype=np.float64)
        information = np.asarray(ent.information_store[rows], dtype=np.float64)
        ready = (
            (energy >= np.asarray(
                reproduction_energy_requirement(
                    ent.genotype[rows], simulation.cfg
                ),
                dtype=np.float64,
            ))
            & (fertility >= 0.5)
        )
        world_energy = np.asarray(ent.energy[world_rows], dtype=np.float64)
        outcomes = {
            "world.alive": float(world_rows.size),
            "world.mean_energy": self._safe_mean(world_energy),
            "world.total_energy": float(world_energy.sum(dtype=np.float64)),
            "target_lineage.alive": float(rows.size),
            "target_lineage.source_survivors": float(source_survivors),
            "target_lineage.descendants_alive": float(rows.size - source_survivors),
            "target_lineage.births_since_intervention": float(self.births[lineage_id]),
            "target_lineage.deaths_since_intervention": float(self.deaths[lineage_id]),
            "target_lineage.energy_deaths_since_intervention": float(
                self.energy_deaths[lineage_id]
            ),
            "target_lineage.integrity_deaths_since_intervention": float(
                self.integrity_deaths[lineage_id]
            ),
            "target_lineage.age_deaths_since_intervention": float(
                self.age_deaths[lineage_id]
            ),
            "target_lineage.net_population_change": float(
                rows.size - self.source_members[lineage_id]
            ),
            "target_lineage.total_energy": float(energy.sum(dtype=np.float64)),
            "target_lineage.mean_energy": self._safe_mean(energy),
            "target_lineage.energy_q25": self._safe_quantile(energy, 0.25),
            "target_lineage.energy_median": self._safe_quantile(energy, 0.5),
            "target_lineage.energy_q75": self._safe_quantile(energy, 0.75),
            "target_lineage.total_fertility": float(fertility.sum(dtype=np.float64)),
            "target_lineage.mean_fertility": self._safe_mean(fertility),
            "target_lineage.reproduction_ready_count": float(np.count_nonzero(ready)),
            "target_lineage.reproduction_ready_fraction": (
                float(np.mean(ready)) if ready.size else 0.0
            ),
            "target_lineage.mean_age": self._safe_mean(age),
            "target_lineage.mean_generation": self._safe_mean(generation),
            "target_lineage.max_generation": float(generation.max()) if generation.size else 0.0,
            "target_lineage.total_material": float(material.sum(dtype=np.float64)),
            "target_lineage.total_information_store": float(
                information.sum(dtype=np.float64)
            ),
            "target_lineage.harvested_energy_since_intervention": float(
                self.harvested[lineage_id]
            ),
            "target_lineage.shared_energy_received_since_intervention": float(
                self.shared[lineage_id]
            ),
        }
        return {
            "offset_ticks": int(offset),
            "absolute_tick": int(simulation.tick),
            "outcomes": outcomes,
        }

    def __call__(self, simulation: Simulation, stats: StepStats | None) -> None:
        if stats is None:
            if self.initialized:
                raise RuntimeError("mediation observer was initialized twice")
            self._initialize(simulation)
            return
        if not self.initialized:
            raise RuntimeError("mediation observer received a step before initialization")
        self._accumulate_events(simulation)
        offset = self.snapshot_ticks.get(int(simulation.tick))
        if offset is not None:
            for lineage_id in self.lineage_ids:
                self.snapshots[lineage_id].append(
                    self._snapshot(simulation, lineage_id, offset)
                )

    def trajectory(self, lineage_id: int) -> list[dict[str, Any]]:
        rows = self.snapshots[int(lineage_id)]
        expected = sorted(self.snapshot_ticks.values())
        observed = [int(row["offset_ticks"]) for row in rows]
        if observed != expected:
            raise RuntimeError(
                f"incomplete mediation trajectory for lineage {lineage_id}: "
                f"expected={expected}, observed={observed}"
            )
        return rows


def _run_branch(
    checkpoint: LineagePairCheckpoint,
    output_dir: Path,
    *,
    lineage_ids: Sequence[int],
    source_members: dict[int, int],
    observation_offsets: Sequence[int],
    backend: str,
    gpu_semantics_mode: str | None,
    module_index: int | None = None,
    target_lineage_id: int | None = None,
    neutralize_cost: bool = False,
) -> tuple[dict[str, Any], _LineageTrajectoryObserver]:
    simulation = Simulation.from_checkpoint(
        checkpoint.checkpoint_path,
        output_dir,
        backend=backend,
        until_tick=checkpoint.until_tick,
        gpu_semantics_mode=gpu_semantics_mode,
    )
    genotype_before = simulation.entities.genotype.copy()
    lineage_before = simulation.entities.lineage_id.copy()
    if module_index is not None:
        if target_lineage_id is None:
            raise ValueError("target_lineage_id is required for a mediation treatment")
        simulation.apply_functional_module_lineage_intervention(
            module_index=module_index,
            lineage_id=target_lineage_id,
            neutralize_cost=neutralize_cost,
        )
    if not np.array_equal(simulation.entities.genotype, genotype_before):
        raise RuntimeError("mediation treatment modified genotype")
    if not np.array_equal(simulation.entities.lineage_id, lineage_before):
        raise RuntimeError("mediation treatment modified lineage IDs")
    observer = _LineageTrajectoryObserver(
        lineage_ids=lineage_ids,
        source_members=source_members,
        checkpoint_tick=checkpoint.checkpoint_tick,
        observation_offsets=observation_offsets,
    )
    world = simulation.run(
        until_tick=checkpoint.until_tick,
        tick_observer=observer,
    )
    return (
        {
            "world": world,
            "scientific_validity": simulation.scientific_validity(),
            "intervention_history": simulation.intervention_history,
        },
        observer,
    )


def _trajectory_by_offset(rows: Sequence[dict[str, Any]]) -> dict[int, dict[str, float]]:
    return {
        int(row["offset_ticks"]): {
            str(key): float(value) for key, value in row["outcomes"].items()
        }
        for row in rows
    }


def _trajectory_effects(
    baseline: Sequence[dict[str, Any]],
    output_neutral: Sequence[dict[str, Any]],
    expression_neutral: Sequence[dict[str, Any]],
) -> dict[str, dict[str, dict[str, float]]]:
    baseline_by = _trajectory_by_offset(baseline)
    output_by = _trajectory_by_offset(output_neutral)
    expression_by = _trajectory_by_offset(expression_neutral)
    if not (baseline_by.keys() == output_by.keys() == expression_by.keys()):
        raise ValueError("mediation branches do not share observation offsets")
    result = {name: {} for name in (*EFFECTS, "decomposition_residual")}
    for offset in sorted(baseline_by):
        common = sorted(
            set(baseline_by[offset])
            & set(output_by[offset])
            & set(expression_by[offset])
        )
        routed = {
            key: baseline_by[offset][key] - output_by[offset][key]
            for key in common
        }
        retained = {
            key: output_by[offset][key] - expression_by[offset][key]
            for key in common
        }
        total = {
            key: baseline_by[offset][key] - expression_by[offset][key]
            for key in common
        }
        residual = {
            key: total[key] - routed[key] - retained[key]
            for key in common
        }
        if any(abs(value) > 1e-12 for value in residual.values()):
            raise RuntimeError("mediation effect decomposition is not closed")
        key = str(offset)
        result["output_routing_effect"][key] = routed
        result["retained_expression_cost_effect"][key] = retained
        result["total_expression_effect"][key] = total
        result["decomposition_residual"][key] = residual
    return result


def execute_mediation_plan(
    plan: LineageMediationPlan,
    output_dir: str | Path,
    *,
    backend: str = "auto",
    gpu_semantics_mode: str | None = None,
) -> dict[str, Any]:
    if tuple(plan.branches) != BRANCHES:
        raise ValueError(f"unsupported mediation branch layout: {plan.branches!r}")
    if plan.effect_decomposition_schema != "output-cost-total-additive-v1":
        raise ValueError("unsupported mediation effect decomposition")
    if plan.outcome_conditioned_pair_selection:
        raise ValueError("outcome-conditioned lineage pair selection is forbidden")
    if not plan.preserves_all_source_pairs_for_selected_modules:
        raise ValueError("mediation plan must preserve every source pair")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    checkpoint_reports: list[dict[str, Any]] = []
    executed_pairs = 0
    for checkpoint in plan.checkpoints:
        if not checkpoint.eligible:
            checkpoint_reports.append(
                {
                    "checkpoint": asdict(checkpoint),
                    "status": "ineligible",
                    "reason": checkpoint.ineligible_reason,
                    "pairs": [],
                }
            )
            continue
        checkpoint_dir = root / checkpoint.run_name / checkpoint.phase
        lineages = tuple(checkpoint.lineages)
        lineage_ids = tuple(item.lineage_id for item in lineages)
        source_members = {item.lineage_id: item.members for item in lineages}
        baseline_meta, baseline_observer = _run_branch(
            checkpoint,
            checkpoint_dir / "baseline",
            lineage_ids=lineage_ids,
            source_members=source_members,
            observation_offsets=plan.observation_offsets,
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
        )
        pairs: list[dict[str, Any]] = []
        for module_index in plan.module_indices:
            for lineage in lineages:
                pair_dir = checkpoint_dir / f"module_{module_index}" / f"lineage_{lineage.lineage_id}"
                output_meta, output_observer = _run_branch(
                    checkpoint,
                    pair_dir / "output_neutral",
                    lineage_ids=(lineage.lineage_id,),
                    source_members={lineage.lineage_id: lineage.members},
                    observation_offsets=plan.observation_offsets,
                    backend=backend,
                    gpu_semantics_mode=gpu_semantics_mode,
                    module_index=module_index,
                    target_lineage_id=lineage.lineage_id,
                    neutralize_cost=False,
                )
                expression_meta, expression_observer = _run_branch(
                    checkpoint,
                    pair_dir / "expression_neutral",
                    lineage_ids=(lineage.lineage_id,),
                    source_members={lineage.lineage_id: lineage.members},
                    observation_offsets=plan.observation_offsets,
                    backend=backend,
                    gpu_semantics_mode=gpu_semantics_mode,
                    module_index=module_index,
                    target_lineage_id=lineage.lineage_id,
                    neutralize_cost=True,
                )
                baseline_trajectory = baseline_observer.trajectory(lineage.lineage_id)
                output_trajectory = output_observer.trajectory(lineage.lineage_id)
                expression_trajectory = expression_observer.trajectory(lineage.lineage_id)
                row = {
                    "pair": {
                        "run_name": checkpoint.run_name,
                        "phase": checkpoint.phase,
                        "checkpoint_tick": checkpoint.checkpoint_tick,
                        "lineage_id": lineage.lineage_id,
                        "source_members": lineage.members,
                        "source_member_fraction": lineage.member_fraction,
                        "source_abundance_rank": lineage.abundance_rank,
                    },
                    "module_index": int(module_index),
                    "branches": {
                        "baseline": {
                            **baseline_meta,
                            "output_dir": str(checkpoint_dir / "baseline"),
                            "trajectory": baseline_trajectory,
                        },
                        "output-neutral": {
                            **output_meta,
                            "output_dir": str(pair_dir / "output_neutral"),
                            "trajectory": output_trajectory,
                        },
                        "expression-neutral": {
                            **expression_meta,
                            "output_dir": str(pair_dir / "expression_neutral"),
                            "trajectory": expression_trajectory,
                        },
                    },
                    "effects": _trajectory_effects(
                        baseline_trajectory,
                        output_trajectory,
                        expression_trajectory,
                    ),
                }
                pairs.append(row)
                executed_pairs += 1
        checkpoint_reports.append(
            {
                "checkpoint": asdict(checkpoint),
                "status": "executed",
                "pairs": pairs,
            }
        )
    report = {
        "schema": RESULT_SCHEMA,
        "plan": asdict(plan),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "executed_pair_count": executed_pairs,
        "eligible_checkpoint_count": sum(item.eligible for item in plan.checkpoints),
        "checkpoints": checkpoint_reports,
        "interpretation_boundary": (
            "Temporal snapshots are repeated observations of the same paired causal unit, "
            "not independent replicates. Mean energy is interpreted together with total "
            "energy, source survivors, descendants, births, deaths and measured harvest/share "
            "flows. The audit does not add ecological roles, alter module copy number, protect "
            "lineages or select responsive checkpoint-lineage pairs."
        ),
    }
    (root / "d2_lineage_mediation_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "d2_lineage_mediation_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_plan_markdown(plan: LineageMediationPlan) -> str:
    lines = [
        "# D2 lineage temporal mediation plan",
        "",
        f"Schema: `{plan.schema}`",
        f"Modules: `{', '.join(map(str, plan.module_indices))}`",
        f"Observation offsets: `{', '.join(map(str, plan.observation_offsets))}` ticks",
        f"Selection rule: `{plan.selection_rule}`",
        f"Source assessment SHA-256: `{plan.source_assessment_sha256}`",
        f"Source persistent expectations: `{plan.source_persistent_output_expectations}`",
        f"Outcome-conditioned pair selection: **{plan.outcome_conditioned_pair_selection}**",
        "",
        "| Run | Phase | Checkpoint | Selected lineages | Effective lineages | Dominant share |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for checkpoint in plan.checkpoints:
        lines.append(
            f"| {checkpoint.run_name} | {checkpoint.phase} | {checkpoint.checkpoint_tick} | "
            f"{len(checkpoint.lineages)} | {checkpoint.effective_lineages:.4f} | "
            f"{checkpoint.dominant_lineage_fraction:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Read-only mediator trajectory",
            "",
            "- energy stock: mean, total and quartiles;",
            "- demography: source survivors, living descendants, births and deaths by cause;",
            "- conversion: fertility and reproduction-ready count;",
            "- flows: harvested and shared energy accumulated after intervention;",
            "- all three paired branches retain the existing output/cost/total decomposition.",
            "",
            "> The plan selects a confirmed module only and preserves every preselected checkpoint-lineage pair. It does not select responsive lineages.",
            "",
        ]
    )
    return "\n".join(lines)


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2 lineage temporal mediation results",
        "",
        f"Executed pairs: **{report['executed_pair_count']}**",
        "",
        "| Run | Phase | Module | Lineage | Rank | Offset | Mean energy effect | Total energy effect | Birth effect | Death effect | Harvest effect |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for checkpoint in report["checkpoints"]:
        for row in checkpoint.get("pairs", ()):
            pair = row["pair"]
            for offset, outcomes in row["effects"]["output_routing_effect"].items():
                lines.append(
                    f"| {pair['run_name']} | {pair['phase']} | {row['module_index']} | "
                    f"{pair['lineage_id']} | {pair['source_abundance_rank']} | {offset} | "
                    f"{outcomes['target_lineage.mean_energy']:+.6f} | "
                    f"{outcomes['target_lineage.total_energy']:+.6f} | "
                    f"{outcomes['target_lineage.births_since_intervention']:+.0f} | "
                    f"{outcomes['target_lineage.deaths_since_intervention']:+.0f} | "
                    f"{outcomes['target_lineage.harvested_energy_since_intervention']:+.6f} |"
                )
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def _parse_csv_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate or execute a temporal mediation audit for confirmed "
            "lineage-conditioned D2 module output"
        )
    )
    parser.add_argument("--assessment")
    parser.add_argument("--source-plan")
    parser.add_argument("--plan")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--observation-offsets",
        default=",".join(map(str, DEFAULT_OBSERVATION_OFFSETS)),
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    generating = bool(args.assessment or args.source_plan)
    if generating:
        if not args.assessment or not args.source_plan or args.plan:
            raise ValueError(
                "plan generation requires --assessment and --source-plan, without --plan"
            )
        assessment_path = Path(args.assessment)
        assessment = _load_assessment(assessment_path)
        plan = build_mediation_plan(
            assessment,
            args.source_plan,
            observation_offsets=_parse_csv_ints(args.observation_offsets),
            source_assessment_sha256=hashlib.sha256(assessment_path.read_bytes()).hexdigest(),
        )
    else:
        if not args.plan:
            raise ValueError("provide --plan, or --assessment with --source-plan")
        plan = load_mediation_plan(args.plan)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    plan_json = output / "d2_lineage_mediation_plan.json"
    plan_json.write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_lineage_mediation_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )
    result = None
    if args.execute:
        result = execute_mediation_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )
    print(
        json.dumps(
            {
                "passed": True,
                "plan_schema": plan.schema,
                "modules": list(plan.module_indices),
                "checkpoint_count": len(plan.checkpoints),
                "pair_count": sum(len(item.lineages) for item in plan.checkpoints)
                * len(plan.module_indices),
                "executed": result is not None,
            }
        )
    )


if __name__ == "__main__":
    main()
