"""Run preregistered acute D3-H matched processing-response panels.

A baseline source trajectory writes every predeclared full-world checkpoint.
Each available checkpoint is restored into original active, original neutral,
reversed active, and reversed neutral processing-support branches. No checkpoint
is selected or discarded from endpoint outcomes: unavailable and sampling-
insufficient checkpoints remain in the report with explicit reasons.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se.checkpointing import read_checkpoint_bundle
from se.cfg import SimulationConfig, load_config
from se.experiments.d3_conservative_intake import parse_seeds
from se.experiments.d3_processing_response import (
    BRANCHES as D3F_BRANCHES,
    NEUTRAL_INTERVENTION,
    REVERSE_INTERVENTION,
    SpatialProcessingResponseObserver,
)
from se.experiments.d3_spatial_processing import _require, _snapshot
from se.runtime.sim import Simulation
from se.runtime.state import StepStats

PLAN_SCHEMA = "d3-processing-response-panel-plan-v2"
RESULT_SCHEMA = "d3-processing-response-panel-results-v2"
SAMPLE_SCHEMA = "nested-seed-checkpoint-response-sampling-v1"
BRANCHES = (*D3F_BRANCHES, "reversed-neutral-support")


@dataclass(frozen=True)
class SampleSupportRequirements:
    minimum_alive: int = 100
    minimum_alive_entity_ticks: int = 12_000
    minimum_eligible_entity_ticks: int = 6_000
    minimum_resource_moves: int = 1_000
    minimum_unique_entities: int = 100
    minimum_effective_lineages: float = 20.0
    maximum_largest_lineage_fraction: float = 0.25
    evolutionary_minimum_births_per_initial_entity: float = 1.0
    evolutionary_minimum_mean_generation: float = 1.0
    evolutionary_minimum_max_generation: int = 3

    def validate(self) -> None:
        if self.minimum_alive <= 0:
            raise ValueError("minimum_alive must be positive")
        if self.minimum_alive_entity_ticks <= 0:
            raise ValueError("minimum_alive_entity_ticks must be positive")
        if self.minimum_eligible_entity_ticks <= 0:
            raise ValueError("minimum_eligible_entity_ticks must be positive")
        if self.minimum_resource_moves <= 0:
            raise ValueError("minimum_resource_moves must be positive")
        if self.minimum_unique_entities <= 0:
            raise ValueError("minimum_unique_entities must be positive")
        if self.minimum_effective_lineages <= 0.0:
            raise ValueError("minimum_effective_lineages must be positive")
        if not 0.0 < self.maximum_largest_lineage_fraction <= 1.0:
            raise ValueError("maximum_largest_lineage_fraction must be in (0, 1]")
        if self.evolutionary_minimum_births_per_initial_entity < 0.0:
            raise ValueError("evolutionary birth floor cannot be negative")
        if self.evolutionary_minimum_mean_generation < 0.0:
            raise ValueError("evolutionary mean-generation floor cannot be negative")
        if self.evolutionary_minimum_max_generation < 0:
            raise ValueError("evolutionary max-generation floor cannot be negative")


def parse_ticks(values: str | Iterable[int]) -> tuple[int, ...]:
    raw = values.split(",") if isinstance(values, str) else values
    ticks = tuple(sorted(set(int(value) for value in raw)))
    if not ticks:
        raise ValueError("at least one checkpoint tick is required")
    if any(value < 0 for value in ticks):
        raise ValueError("checkpoint ticks must be non-negative")
    return ticks


def _effective_lineages(lineages: np.ndarray) -> tuple[float, float, int]:
    values = np.asarray(lineages, dtype=np.uint64)
    if values.size == 0:
        return 0.0, 0.0, 0
    _, counts = np.unique(values, return_counts=True)
    proportions = counts.astype(np.float64) / float(values.size)
    denominator = float(np.dot(proportions, proportions))
    effective = 1.0 / denominator if denominator > 0.0 else 0.0
    return effective, float(proportions.max(initial=0.0)), int(counts.size)


def _population_state(simulation: Simulation) -> dict[str, np.ndarray]:
    rows = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    return {
        "ids": np.asarray(simulation.entities.entity_id[rows], dtype=np.uint64).copy(),
        "lineages": np.asarray(
            simulation.entities.lineage_id[rows], dtype=np.uint64
        ).copy(),
        "generation": np.asarray(
            simulation.entities.generation[rows], dtype=np.uint32
        ).copy(),
        "age": np.asarray(simulation.entities.age[rows], dtype=np.uint32).copy(),
    }


def _population_diagnostics_from_arrays(
    state: dict[str, np.ndarray],
    *,
    births_total: int,
    deaths_total: int,
    initial_entities: int,
    requirements: SampleSupportRequirements,
) -> dict[str, Any]:
    effective, largest, lineage_count = _effective_lineages(state["lineages"])
    generation = np.asarray(state["generation"], dtype=np.float64)
    age = np.asarray(state["age"], dtype=np.float64)
    alive = int(state["ids"].size)
    mean_generation = float(generation.mean()) if generation.size else 0.0
    max_generation = int(generation.max(initial=0.0))
    population_support = {
        "minimum_alive_met": alive >= requirements.minimum_alive,
        "minimum_effective_lineages_met": (
            effective >= requirements.minimum_effective_lineages
        ),
        "maximum_largest_lineage_fraction_met": (
            largest <= requirements.maximum_largest_lineage_fraction
        ),
    }
    evolutionary_support = {
        "minimum_births_per_initial_entity_met": (
            births_total
            >= requirements.evolutionary_minimum_births_per_initial_entity
            * float(initial_entities)
        ),
        "minimum_mean_generation_met": (
            mean_generation >= requirements.evolutionary_minimum_mean_generation
        ),
        "minimum_max_generation_met": (
            max_generation >= requirements.evolutionary_minimum_max_generation
        ),
    }
    return {
        "alive": alive,
        "unique_entities": alive,
        "lineage_count": lineage_count,
        "effective_lineages": effective,
        "largest_lineage_fraction": largest,
        "mean_generation": mean_generation,
        "max_generation": max_generation,
        "mean_age": float(age.mean()) if age.size else 0.0,
        "births_total": int(births_total),
        "deaths_total": int(deaths_total),
        "population_support": {
            **population_support,
            "eligible": all(population_support.values()),
        },
        "evolutionary_support": {
            **evolutionary_support,
            "eligible": all(evolutionary_support.values()),
        },
    }


def _checkpoint_diagnostics(
    record: dict[str, Any], requirements: SampleSupportRequirements
) -> dict[str, Any]:
    simulation = record["simulation"]
    entities = simulation["entities"]
    rows = np.flatnonzero(entities.alive).astype(np.int32)
    state = {
        "ids": np.asarray(entities.entity_id[rows], dtype=np.uint64),
        "lineages": np.asarray(entities.lineage_id[rows], dtype=np.uint64),
        "generation": np.asarray(entities.generation[rows], dtype=np.uint32),
        "age": np.asarray(entities.age[rows], dtype=np.uint32),
    }
    return _population_diagnostics_from_arrays(
        state,
        births_total=int(simulation["total_births"]),
        deaths_total=int(simulation["total_deaths"]),
        initial_entities=int(record["config"].world.initial_entities),
        requirements=requirements,
    )


class WindowedSampleSupportObserver:
    """Compose response measurement with exact nested sample-support accounting."""

    def __init__(
        self,
        *,
        horizon: int,
        observation_period: int,
        branch: str,
        initial_entities: int,
        requirements: SampleSupportRequirements,
    ) -> None:
        self.response = SpatialProcessingResponseObserver(
            horizon=horizon,
            observation_period=observation_period,
            branch=branch,
        )
        self.horizon = int(horizon)
        self.observation_period = int(observation_period)
        self.initial_entities = int(initial_entities)
        self.requirements = requirements
        self.previous: dict[str, np.ndarray] | None = None
        self.started_tick: int | None = None
        self.sample_trajectory: list[dict[str, Any]] = []
        self.total_alive_entity_ticks = 0
        self.total_alive_min: int | None = None
        self.total_alive_max = 0
        self.total_births = 0
        self.total_deaths = 0
        self.total_entity_ids: set[int] = set()
        self.total_lineage_ticks: dict[int, int] = {}
        self._window_reset(0, {})

    def _window_reset(self, tick: int, response_summary: dict[str, float]) -> None:
        self.window_start_tick = int(tick)
        self.window_alive_entity_ticks = 0
        self.window_births = 0
        self.window_deaths = 0
        self.window_alive_min: int | None = None
        self.window_alive_max = 0
        self.window_entity_ids: set[int] = set()
        self.window_lineage_ticks: dict[int, int] = {}
        self.window_response_baseline = dict(response_summary)

    @staticmethod
    def _lineage_tick_add(target: dict[int, int], lineages: np.ndarray) -> None:
        unique, counts = np.unique(np.asarray(lineages, dtype=np.uint64), return_counts=True)
        for lineage, count in zip(unique, counts, strict=True):
            key = int(lineage)
            target[key] = target.get(key, 0) + int(count)

    @staticmethod
    def _lineage_tick_metrics(values: dict[int, int]) -> tuple[float, float, int]:
        if not values:
            return 0.0, 0.0, 0
        counts = np.asarray(list(values.values()), dtype=np.float64)
        proportions = counts / counts.sum()
        denominator = float(np.dot(proportions, proportions))
        return (
            1.0 / denominator if denominator > 0.0 else 0.0,
            float(proportions.max(initial=0.0)),
            int(counts.size),
        )

    def _accumulate_population_step(
        self,
        previous: dict[str, np.ndarray],
        current: dict[str, np.ndarray],
    ) -> None:
        alive = int(previous["ids"].size)
        self.total_alive_entity_ticks += alive
        self.total_alive_min = alive if self.total_alive_min is None else min(self.total_alive_min, alive)
        self.total_alive_max = max(self.total_alive_max, alive)
        self.window_alive_entity_ticks += alive
        self.window_alive_min = alive if self.window_alive_min is None else min(
            self.window_alive_min, alive
        )
        self.window_alive_max = max(self.window_alive_max, alive)
        ids = {int(value) for value in previous["ids"]}
        self.total_entity_ids.update(ids)
        self.window_entity_ids.update(ids)
        self._lineage_tick_add(self.total_lineage_ticks, previous["lineages"])
        self._lineage_tick_add(self.window_lineage_ticks, previous["lineages"])
        previous_ids = ids
        current_ids = {int(value) for value in current["ids"]}
        births = len(current_ids - previous_ids)
        deaths = len(previous_ids - current_ids)
        self.total_births += births
        self.total_deaths += deaths
        self.window_births += births
        self.window_deaths += deaths

    def _support_flags(
        self,
        *,
        population: dict[str, Any],
        minimum_alive_observed: int,
        alive_entity_ticks: int,
        eligible_entity_ticks: float,
        resource_moves: float,
        unique_entities: int,
        effective_lineages: float,
        largest_lineage_fraction: float,
    ) -> dict[str, bool]:
        flags = {
            "minimum_alive_met": minimum_alive_observed >= self.requirements.minimum_alive,
            "minimum_alive_entity_ticks_met": (
                alive_entity_ticks >= self.requirements.minimum_alive_entity_ticks
            ),
            "minimum_eligible_entity_ticks_met": (
                eligible_entity_ticks >= self.requirements.minimum_eligible_entity_ticks
            ),
            "minimum_resource_moves_met": (
                resource_moves >= self.requirements.minimum_resource_moves
            ),
            "minimum_unique_entities_met": (
                unique_entities >= self.requirements.minimum_unique_entities
            ),
            "minimum_effective_lineages_met": (
                effective_lineages >= self.requirements.minimum_effective_lineages
            ),
            "maximum_largest_lineage_fraction_met": (
                largest_lineage_fraction
                <= self.requirements.maximum_largest_lineage_fraction
            ),
        }
        return {**flags, "eligible": all(flags.values())}

    def _close_window(self, simulation: Simulation) -> dict[str, Any]:
        current_response = self.response.summary()
        eligible_entity_ticks = float(
            current_response["eligible_entity_ticks"]
            - self.window_response_baseline.get("eligible_entity_ticks", 0.0)
        )
        resource_moves = float(
            current_response["resource_move_count"]
            - self.window_response_baseline.get("resource_move_count", 0.0)
        )
        state = _population_state(simulation)
        population = _population_diagnostics_from_arrays(
            state,
            births_total=simulation.total_births,
            deaths_total=simulation.total_deaths,
            initial_entities=self.initial_entities,
            requirements=self.requirements,
        )
        effective, largest, lineage_count = self._lineage_tick_metrics(
            self.window_lineage_ticks
        )
        support = self._support_flags(
            population=population,
            minimum_alive_observed=min(self.window_alive_min or population["alive"], population["alive"]),
            alive_entity_ticks=self.window_alive_entity_ticks,
            eligible_entity_ticks=eligible_entity_ticks,
            resource_moves=resource_moves,
            unique_entities=len(self.window_entity_ids),
            effective_lineages=effective,
            largest_lineage_fraction=largest,
        )
        return {
            "schema": SAMPLE_SCHEMA,
            "start_tick": self.window_start_tick,
            "end_tick": int(simulation.tick),
            "duration_ticks": int(simulation.tick) - self.window_start_tick,
            "alive_entity_ticks": self.window_alive_entity_ticks,
            "eligible_entity_ticks": eligible_entity_ticks,
            "resource_move_count": resource_moves,
            "unique_entities": len(self.window_entity_ids),
            "births": self.window_births,
            "deaths": self.window_deaths,
            "minimum_pre_step_alive": self.window_alive_min or 0,
            "maximum_pre_step_alive": self.window_alive_max,
            "lineage_entity_tick_count": lineage_count,
            "effective_lineage_entity_ticks": effective,
            "largest_lineage_entity_tick_fraction": largest,
            "end_population": population,
            "analysis_support": support,
        }

    def __call__(self, simulation: Simulation, stats: StepStats | None) -> None:
        self.response(simulation, stats)
        current = _population_state(simulation)
        if stats is None:
            self.previous = current
            self.started_tick = int(simulation.tick)
            self.total_entity_ids.update(int(value) for value in current["ids"])
            self._window_reset(simulation.tick, self.response.summary())
            return
        assert self.previous is not None
        self._accumulate_population_step(self.previous, current)
        self.previous = current
        if (
            simulation.tick % self.observation_period == 0
            or simulation.tick == self.horizon
        ):
            self.sample_trajectory.append(self._close_window(simulation))
            self._window_reset(simulation.tick, self.response.summary())

    def finalize(self, simulation: Simulation) -> None:
        if not self.response.trajectory or int(self.response.trajectory[-1]["tick"]) != int(
            simulation.tick
        ):
            self.response.trajectory.append(self.response._snapshot(simulation))
        if not self.sample_trajectory or int(self.sample_trajectory[-1]["end_tick"]) != int(
            simulation.tick
        ):
            if int(simulation.tick) > self.window_start_tick:
                self.sample_trajectory.append(self._close_window(simulation))
                self._window_reset(simulation.tick, self.response.summary())

    def summary(self, simulation: Simulation) -> dict[str, Any]:
        response = self.response.summary()
        state = _population_state(simulation)
        population = _population_diagnostics_from_arrays(
            state,
            births_total=simulation.total_births,
            deaths_total=simulation.total_deaths,
            initial_entities=self.initial_entities,
            requirements=self.requirements,
        )
        effective, largest, lineage_count = self._lineage_tick_metrics(
            self.total_lineage_ticks
        )
        support = self._support_flags(
            population=population,
            minimum_alive_observed=min(self.total_alive_min or population["alive"], population["alive"]),
            alive_entity_ticks=self.total_alive_entity_ticks,
            eligible_entity_ticks=float(response["eligible_entity_ticks"]),
            resource_moves=float(response["resource_move_count"]),
            unique_entities=len(self.total_entity_ids),
            effective_lineages=effective,
            largest_lineage_fraction=largest,
        )
        return {
            "schema": SAMPLE_SCHEMA,
            "start_tick": self.started_tick,
            "end_tick": int(simulation.tick),
            "duration_ticks": int(simulation.tick) - int(self.started_tick or 0),
            "alive_entity_ticks": self.total_alive_entity_ticks,
            "eligible_entity_ticks": float(response["eligible_entity_ticks"]),
            "resource_move_count": float(response["resource_move_count"]),
            "unique_entities": len(self.total_entity_ids),
            "births": self.total_births,
            "deaths": self.total_deaths,
            "minimum_pre_step_alive": self.total_alive_min or 0,
            "maximum_pre_step_alive": self.total_alive_max,
            "lineage_entity_tick_count": lineage_count,
            "effective_lineage_entity_ticks": effective,
            "largest_lineage_entity_tick_fraction": largest,
            "end_population": population,
            "analysis_support": support,
            "response": response,
        }


def _ledger_state(simulation: Simulation) -> dict[str, np.ndarray]:
    environment = simulation.environment
    return {
        "resource": np.asarray(environment.resources, dtype=np.float64).sum(axis=(1, 2)),
        "residue": np.asarray(environment.resource_residue, dtype=np.float64).sum(
            axis=(1, 2)
        ),
        "source": np.asarray(environment.total_resource_renewal_source, dtype=np.float64).copy(),
        "sink": np.asarray(environment.total_resource_renewal_sink, dtype=np.float64).copy(),
        "field_roundoff": np.asarray(
            environment.total_resource_field_roundoff, dtype=np.float64
        ).copy(),
        "harvest_roundoff": np.asarray(
            environment.total_resource_harvest_roundoff, dtype=np.float64
        ).copy(),
        "harvested": np.asarray(simulation.total_harvested_resources, dtype=np.float64).copy(),
        "released": np.asarray(
            simulation.total_resource_residue_released, dtype=np.float64
        ).copy(),
        "decay": np.asarray(simulation.total_resource_store_decay, dtype=np.float64).copy(),
        "death": np.asarray(
            simulation.total_resource_store_death_loss, dtype=np.float64
        ).copy(),
        "deposited": np.asarray(
            simulation.total_resource_residue_deposited, dtype=np.float64
        ).copy(),
        "residue_field_roundoff": np.asarray(
            getattr(
                environment, "total_resource_residue_field_roundoff", np.zeros(4)
            ),
            dtype=np.float64,
        ).copy(),
        "residue_deposit_roundoff": np.asarray(
            getattr(
                environment, "total_resource_residue_deposit_roundoff", np.zeros(4)
            ),
            dtype=np.float64,
        ).copy(),
    }


def _interval_ledgers(
    start: dict[str, np.ndarray], end: dict[str, np.ndarray]
) -> dict[str, Any]:
    def delta(key: str) -> np.ndarray:
        return end[key] - start[key]

    resource_residual = (
        start["resource"]
        + delta("source")
        + delta("released")
        + delta("field_roundoff")
        - delta("harvested")
        - delta("sink")
        - end["resource"]
        - delta("harvest_roundoff")
    )
    resource_scale = np.maximum.reduce(
        [
            np.ones(4),
            np.abs(start["resource"]),
            np.abs(delta("source")),
            np.abs(delta("harvested")),
            np.abs(end["resource"]),
        ]
    )
    source_residual = delta("decay") + delta("death") - delta("deposited")
    external_residual = (
        start["residue"] + delta("deposited") - delta("released") - end["residue"]
    )
    residue_field_roundoff = delta("residue_field_roundoff")
    residue_deposit_roundoff = delta("residue_deposit_roundoff")
    residue_numerical_adjustment = residue_field_roundoff + residue_deposit_roundoff
    corrected_external_residual = external_residual + residue_numerical_adjustment
    recycling_scale = max(1.0, float(np.max(np.abs(delta("deposited")), initial=0.0)))
    return {
        "external_resource": {
            "residual": resource_residual.tolist(),
            "relative_residual": (np.abs(resource_residual) / resource_scale).tolist(),
            "valid": bool(
                np.all(np.isfinite(resource_residual))
                and np.all(np.abs(resource_residual) <= 2.0e-5 * resource_scale)
            ),
        },
        "external_recycling": {
            "source_residual": source_residual.tolist(),
            "external_residual_before_numerical_adjustment": external_residual.tolist(),
            "residue_field_roundoff": residue_field_roundoff.tolist(),
            "residue_deposit_roundoff": residue_deposit_roundoff.tolist(),
            "residue_numerical_adjustment": residue_numerical_adjustment.tolist(),
            "corrected_external_residual": corrected_external_residual.tolist(),
            "valid": bool(
                np.all(np.isfinite(source_residual))
                and np.all(np.isfinite(corrected_external_residual))
                and np.all(np.abs(source_residual) <= 2.0e-5 * recycling_scale)
                and np.all(
                    np.abs(corrected_external_residual)
                    <= 2.0e-5 * recycling_scale
                )
            ),
        },
    }


def build_plan(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    checkpoint_ticks: Iterable[int],
    *,
    response_window: int,
    observation_period: int,
    requirements: SampleSupportRequirements,
) -> dict[str, Any]:
    _require(cfg)
    requirements.validate()
    selected = parse_seeds(seeds)
    checkpoints = parse_ticks(checkpoint_ticks)
    if response_window <= 0:
        raise ValueError("response_window must be positive")
    if observation_period <= 0:
        raise ValueError("observation_period must be positive")
    return {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected),
        "checkpoint_ticks": list(checkpoints),
        "response_window_ticks": int(response_window),
        "observation_period_ticks": int(observation_period),
        "branches": list(BRANCHES),
        "matched_orientation_controls": {
            "original-support": "neutral-support",
            "reversed-support": "reversed-neutral-support",
        },
        "reversed_neutral_interventions": [
            REVERSE_INTERVENTION,
            NEUTRAL_INTERVENTION,
        ],
        "float32_residue_inventory_roundoff_recorded_separately": True,
        "sample_schema": SAMPLE_SCHEMA,
        "requirements": asdict(requirements),
        "checkpoint_selection": "predeclared-all-retained-v1",
        "outcome_conditioned_checkpoint_selection": False,
        "insufficient_checkpoints_rerun_or_replaced": False,
        "nested_independent_unit": "seed/checkpoint",
        "movement_events_independent_replicates": False,
        "acute_response_and_evolutionary_support_reported_separately": True,
        "source_population_rules_changed": False,
        "non_world_long_run_diagnostics_disabled_for_panel": True,
        "diagnostic_override_feedback_to_world": False,
        "movement_reward_or_controller_added": False,
        "support_sensor_added": False,
        "entity_lineage_and_group_feedback": False,
        "named_resource_roles": False,
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "pass_fail_gate_feedback_to_world": False,
    }


def _run_branch(
    checkpoint: Path,
    output: Path,
    *,
    branch: str,
    end_tick: int,
    observation_period: int,
    backend: str,
    requirements: SampleSupportRequirements,
) -> dict[str, Any]:
    simulation = Simulation.from_checkpoint(
        checkpoint, output, backend=backend, until_tick=end_tick
    )
    genotype_before = simulation.entities.genotype.copy()
    resources_before = np.asarray(simulation.environment.resources).copy()
    residue_before = np.asarray(simulation.environment.resource_residue).copy()
    start_ledger = _ledger_state(simulation)
    interventions: list[str] = []
    if branch == "reversed-support":
        simulation.apply_intervention(REVERSE_INTERVENTION)
        interventions.append(REVERSE_INTERVENTION)
    elif branch == "neutral-support":
        simulation.apply_intervention(NEUTRAL_INTERVENTION)
        interventions.append(NEUTRAL_INTERVENTION)
    elif branch == "reversed-neutral-support":
        simulation.apply_intervention(REVERSE_INTERVENTION)
        simulation.apply_intervention(NEUTRAL_INTERVENTION)
        interventions.extend((REVERSE_INTERVENTION, NEUTRAL_INTERVENTION))
    elif branch != "original-support":
        raise ValueError(f"unknown response-panel branch {branch!r}")
    if not np.array_equal(genotype_before, simulation.entities.genotype):
        raise RuntimeError("response-panel intervention modified genotype")
    if not np.array_equal(resources_before, np.asarray(simulation.environment.resources)):
        raise RuntimeError("response-panel intervention modified resource fields")
    if not np.array_equal(residue_before, np.asarray(simulation.environment.resource_residue)):
        raise RuntimeError("response-panel intervention modified resource residue")
    observer = WindowedSampleSupportObserver(
        horizon=end_tick,
        observation_period=observation_period,
        branch=branch,
        initial_entities=simulation.cfg.world.initial_entities,
        requirements=requirements,
    )
    final_world = simulation.run(until_tick=end_tick, tick_observer=observer)
    observer.finalize(simulation)
    replay = json.loads((output / "replay_provenance.json").read_text(encoding="utf-8"))
    end_ledger = _ledger_state(simulation)
    return {
        "branch": branch,
        "output": str(output),
        "checkpoint_state_sha256": replay["checkpoint_lineage"][-1][
            "checkpoint_state_sha256"
        ],
        "interventions": interventions,
        "scientific_validity": simulation.scientific_validity(),
        "final": _snapshot(simulation, final_world),
        "response_summary": observer.response.summary(),
        "response_trajectory": observer.response.trajectory,
        "sample_support": observer.summary(simulation),
        "sample_windows": observer.sample_trajectory,
        "interval_ledgers": _interval_ledgers(start_ledger, end_ledger),
    }


def _matched_orientation_contrasts(branches: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {row["branch"]: row for row in branches}
    pairs = {
        "original": ("original-support", "neutral-support"),
        "reversed": ("reversed-support", "reversed-neutral-support"),
    }
    metrics = {
        "resource_move_mean_support_gain": "mean_support_gain",
        "resource_move_mean_alignment_cosine": "mean_alignment_cosine",
        "resource_move_positive_support_gain_fraction": "positive_gain_fraction",
    }
    result: dict[str, Any] = {"schema": "matched-orientation-active-neutral-contrast-v1"}
    for source_key, output_key in metrics.items():
        effects = {
            orientation: float(
                by_name[active]["response_summary"][source_key]
                - by_name[neutral]["response_summary"][source_key]
            )
            for orientation, (active, neutral) in pairs.items()
        }
        result[output_key] = {
            **effects,
            "reversed_minus_original": effects["reversed"] - effects["original"],
        }
    return result


def _checkpoint_panel(
    seed: int,
    checkpoint_tick: int,
    checkpoint: Path | None,
    *,
    response_window: int,
    observation_period: int,
    backend: str,
    requirements: SampleSupportRequirements,
    output: Path,
) -> dict[str, Any]:
    if checkpoint is None or not checkpoint.is_file():
        return {
            "seed": int(seed),
            "checkpoint_tick": int(checkpoint_tick),
            "status": "unavailable-source-terminated-before-checkpoint",
            "checkpoint_state_sha256": None,
            "checkpoint_population": None,
            "branches": [],
            "shared_checkpoint_state": False,
            "acute_quartet_analysis_eligible": False,
        }
    metadata, record = read_checkpoint_bundle(checkpoint)
    checkpoint_population = _checkpoint_diagnostics(record, requirements)
    end_tick = int(checkpoint_tick) + int(response_window)
    panel_dir = output / f"checkpoint_{checkpoint_tick:08d}"
    branches = [
        _run_branch(
            checkpoint,
            panel_dir / branch.replace("-", "_"),
            branch=branch,
            end_tick=end_tick,
            observation_period=observation_period,
            backend=backend,
            requirements=requirements,
        )
        for branch in BRANCHES
    ]
    shared = len({row["checkpoint_state_sha256"] for row in branches}) == 1
    if any(row["checkpoint_state_sha256"] != metadata["state_sha256"] for row in branches):
        raise RuntimeError("D3-H branch did not preserve the source checkpoint state")
    eligible = bool(
        checkpoint_population["population_support"]["eligible"]
        and all(row["sample_support"]["analysis_support"]["eligible"] for row in branches)
    )
    return {
        "seed": int(seed),
        "checkpoint_tick": int(checkpoint_tick),
        "status": "completed",
        "checkpoint": str(checkpoint),
        "checkpoint_state_sha256": metadata["state_sha256"],
        "checkpoint_population": checkpoint_population,
        "branches": branches,
        "shared_checkpoint_state": shared,
        "matched_orientation_contrasts": _matched_orientation_contrasts(branches),
        "acute_quartet_analysis_eligible": eligible,
        "evolutionary_checkpoint_analysis_eligible": checkpoint_population[
            "evolutionary_support"
        ]["eligible"],
    }


def _payload(plan: dict[str, Any], panels: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in panels if row["status"] == "completed"]
    eligible = [row for row in completed if row["acute_quartet_analysis_eligible"]]
    evolutionary = [
        row
        for row in completed
        if row.get("evolutionary_checkpoint_analysis_eligible", False)
    ]
    all_branches = [branch for row in completed for branch in row["branches"]]
    audit = {
        "every_predeclared_checkpoint_accounted_for": (
            len(panels)
            == len(plan["seeds"]) * len(plan["checkpoint_ticks"])
        ),
        "all_completed_quartets_share_checkpoint_state": all(
            row["shared_checkpoint_state"] for row in completed
        ),
        "all_completed_branches_have_complete_response_and_sample_trajectories": all(
            branch["response_trajectory"]
            and branch["sample_windows"]
            and int(branch["response_trajectory"][-1]["tick"])
            == int(branch["final"]["tick"])
            and int(branch["sample_windows"][-1]["end_tick"])
            == int(branch["final"]["tick"])
            for branch in all_branches
        ),
        "acute_interval_resource_ledger_valid_in_every_completed_branch": all(
            branch["interval_ledgers"]["external_resource"]["valid"]
            for branch in all_branches
        ),
        "acute_interval_recycling_ledger_valid_in_every_completed_branch": all(
            branch["interval_ledgers"]["external_recycling"]["valid"]
            for branch in all_branches
        ),
        "outcome_conditioned_checkpoint_selection": False,
        "insufficient_checkpoint_replacement": False,
    }
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "panel_count": len(panels),
        "completed_panel_count": len(completed),
        "acute_analysis_eligible_panel_count": len(eligible),
        "evolutionary_analysis_eligible_checkpoint_count": len(evolutionary),
        "panels": panels,
        "audit_completeness": audit,
        "recommendation": (
            "analyze-only-preregistered-acute-panels-marked-eligible"
            if eligible
            else "increase-unprotected-system-scale-or-revise-preregistered-checkpoints-before-new-mechanism"
        ),
        "causal_claim_scope": (
            "Within each completed seed/checkpoint quartet, active-versus-neutral differences "
            "are attributable to support execution under a matched observation orientation. "
            "Checkpoints within one seed are nested repeated panels, not independent seeds."
        ),
        "interpretation_boundary": (
            "Sampling eligibility controls interpretation only and never feeds back into the world, "
            "protects lineages, retries failed populations, or selects checkpoints by outcomes. "
            "Acute response support does not establish evolutionary adaptation, migration, "
            "specialization, coexistence, or ecological roles."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# D3-H matched acute processing-response panel",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Seed | Checkpoint | Status | Alive | Effective lineages | Mean generation | Evolutionary support | Branch | Alive entity-ticks | Resource moves | Acute support | Mean gain | Mean cosine |",
        "|---:|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for panel in payload["panels"]:
        if panel["status"] != "completed":
            lines.append(
                f"| {panel['seed']} | {panel['checkpoint_tick']} | {panel['status']} | 0 | 0 | 0 | False | — | 0 | 0 | False | 0 | 0 |"
            )
            continue
        population = panel["checkpoint_population"]
        for branch in panel["branches"]:
            sample = branch["sample_support"]
            response = branch["response_summary"]
            lines.append(
                f"| {panel['seed']} | {panel['checkpoint_tick']} | completed | "
                f"{population['alive']} | {population['effective_lineages']} | "
                f"{population['mean_generation']} | "
                f"{panel['evolutionary_checkpoint_analysis_eligible']} | "
                f"{branch['branch']} | {sample['alive_entity_ticks']} | "
                f"{int(sample['resource_move_count'])} | "
                f"{sample['analysis_support']['eligible']} | "
                f"{response['resource_move_mean_support_gain']} | "
                f"{response['resource_move_mean_alignment_cosine']} |"
            )
    lines += ["", "## Audit completeness", ""]
    lines += [
        f"- {key.replace('_', ' ')}: `{value}`"
        for key, value in payload["audit_completeness"].items()
    ]
    lines += [
        "",
        f"Acute analysis-eligible panels: `{payload['acute_analysis_eligible_panel_count']}`",
        "",
        f"Evolutionary analysis-eligible checkpoints: `{payload['evolutionary_analysis_eligible_checkpoint_count']}`",
        "",
        f"Recommendation: `{payload['recommendation']}`",
        "",
        payload["causal_claim_scope"],
        "",
        payload["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def execute_processing_response_panel(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    checkpoint_ticks: Iterable[int],
    response_window: int = 120,
    observation_period: int = 30,
    backend: str = "auto",
    requirements: SampleSupportRequirements | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    selected = parse_seeds(seeds)
    checkpoints = parse_ticks(checkpoint_ticks)
    support_requirements = requirements or SampleSupportRequirements()
    plan = build_plan(
        cfg,
        selected,
        checkpoints,
        response_window=response_window,
        observation_period=observation_period,
        requirements=support_requirements,
    )
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        if not overwrite:
            raise RuntimeError(f"output exists: {output}; pass --overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d3_processing_response_panel_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    panels: list[dict[str, Any]] = []
    source_horizon = max(checkpoints)
    nonzero_checkpoints = tuple(value for value in checkpoints if value > 0)
    for seed in selected:
        seed_dir = output / f"seed_{seed}"
        source_dir = seed_dir / "source"
        source_period = max(1, source_horizon + response_window + 1)
        run_cfg = replace(
            cfg,
            run=replace(
                cfg.run,
                seed=seed,
                ticks=source_horizon,
                checkpoint_period=source_period,
                checkpoint_ticks=nonzero_checkpoints,
                full_checkpoint_enabled=True,
                long_run_diagnostics_enabled=False,
                long_run_diagnostics_schema="disabled",
                spatial_stress_diagnostics_enabled=False,
                spatial_stress_diagnostics_schema="disabled",
                subject_structure_diagnostics_enabled=False,
                subject_structure_diagnostics_schema="disabled",
                environment_atlas_diagnostics_enabled=False,
                environment_atlas_diagnostics_schema="disabled",
                environment_atlas_scales=(),
            ),
        )
        seed_dir.mkdir(parents=True, exist_ok=True)
        (seed_dir / "resolved_config.json").write_text(
            json.dumps(asdict(run_cfg), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        source = Simulation(run_cfg, source_dir, backend=backend)
        if 0 in checkpoints:
            source.save_full_checkpoint(source_dir / "checkpoint_00000000.sechk")
        source_final = source.run(until_tick=source_horizon)
        (seed_dir / "source_final.json").write_text(
            json.dumps(source_final, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for checkpoint_tick in checkpoints:
            checkpoint = source_dir / f"checkpoint_{checkpoint_tick:08d}.sechk"
            panels.append(
                _checkpoint_panel(
                    seed,
                    checkpoint_tick,
                    checkpoint if checkpoint.is_file() else None,
                    response_window=response_window,
                    observation_period=observation_period,
                    backend=backend,
                    requirements=support_requirements,
                    output=seed_dir,
                )
            )
            partial = _payload(plan, panels)
            (output / "d3_processing_response_panel_results.json").write_text(
                json.dumps(partial, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    payload = _payload(plan, panels)
    (output / "d3_processing_response_panel_results.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--checkpoint-ticks", required=True)
    parser.add_argument("--response-window", type=int, default=120)
    parser.add_argument("--observation-period", type=int, default=30)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument("--min-alive", type=int, default=100)
    parser.add_argument("--min-alive-entity-ticks", type=int, default=12_000)
    parser.add_argument("--min-eligible-entity-ticks", type=int, default=6_000)
    parser.add_argument("--min-resource-moves", type=int, default=1_000)
    parser.add_argument("--min-unique-entities", type=int, default=100)
    parser.add_argument("--min-effective-lineages", type=float, default=20.0)
    parser.add_argument("--max-largest-lineage-fraction", type=float, default=0.25)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    requirements = SampleSupportRequirements(
        minimum_alive=args.min_alive,
        minimum_alive_entity_ticks=args.min_alive_entity_ticks,
        minimum_eligible_entity_ticks=args.min_eligible_entity_ticks,
        minimum_resource_moves=args.min_resource_moves,
        minimum_unique_entities=args.min_unique_entities,
        minimum_effective_lineages=args.min_effective_lineages,
        maximum_largest_lineage_fraction=args.max_largest_lineage_fraction,
    )
    payload = execute_processing_response_panel(
        load_config(args.config),
        parse_seeds(args.seeds),
        args.output,
        checkpoint_ticks=parse_ticks(args.checkpoint_ticks),
        response_window=args.response_window,
        observation_period=args.observation_period,
        backend=args.backend,
        requirements=requirements,
        overwrite=args.overwrite,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
