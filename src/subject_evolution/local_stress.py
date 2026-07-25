"""Observational spatial stress diagnostics for heterogeneous worlds.

The tracker partitions the physical world into a small fixed analysis grid.  It
never changes policy, movement, resource fields, groups, or knowledge.  All
state is accounting state so exact checkpoint continuation remains possible.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import numpy as np


FLOW_INTERNAL = 0
FLOW_GROUP_TO_GROUP = 1
FLOW_GROUP_TO_UNGROUPED = 2
FLOW_UNGROUPED_TO_GROUP = 3
FLOW_UNBOUNDED = 4
FLOW_COUNT = 5


def _safe_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    out = np.zeros_like(np.asarray(numerator, dtype=np.float64), dtype=np.float64)
    np.divide(numerator, denominator, out=out, where=np.asarray(denominator) > 0)
    return out


def _coefficient_of_variation(values: np.ndarray, valid: np.ndarray | None = None) -> float:
    array = np.asarray(values, dtype=np.float64)
    if valid is not None:
        array = array[np.asarray(valid, dtype=bool)]
    array = array[np.isfinite(array)]
    if array.size == 0:
        return 0.0
    mean = float(np.mean(array))
    return float(np.std(array) / mean) if abs(mean) > 1e-30 else 0.0


@dataclass
class LocalStressDiagnostics:
    """Windowed local population, environment, and benefit-flow accounting."""

    world_width: float
    world_height: float
    regions_x: int
    regions_y: int
    resource_capacity: tuple[float, float, float, float]
    world_grid_x: int
    world_grid_y: int

    def __post_init__(self) -> None:
        self.region_count = int(self.regions_x * self.regions_y)
        if self.regions_x <= 0 or self.regions_y <= 0:
            raise ValueError("local diagnostic region dimensions must be positive")
        self.observed_ticks = 0
        self.entity_ticks = np.zeros(self.region_count, dtype=np.int64)
        self.hazard_exposure = np.zeros(self.region_count, dtype=np.float64)
        self.scarcity_exposure = np.zeros(self.region_count, dtype=np.float64)
        self.crowding_exposure = np.zeros(self.region_count, dtype=np.float64)
        self.births = np.zeros(self.region_count, dtype=np.int64)
        self.deaths = np.zeros(self.region_count, dtype=np.int64)
        self.benefit_flow = np.zeros((self.region_count, FLOW_COUNT), dtype=np.float64)
        self.current_alive = np.zeros(self.region_count, dtype=np.int64)
        self.previous_alive = np.zeros(self.region_count, dtype=np.int64)

    def clone(self) -> "LocalStressDiagnostics":
        return copy.deepcopy(self)

    def snapshot_state(self) -> dict[str, Any]:
        return copy.deepcopy(self.__dict__)

    def restore_state(self, state: dict[str, Any]) -> None:
        for key, value in state.items():
            setattr(self, key, copy.deepcopy(value))

    def region_ids(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        px = np.asarray(x, dtype=np.float64)
        py = np.asarray(y, dtype=np.float64)
        rx = np.floor(px / self.world_width * self.regions_x).astype(np.int64)
        ry = np.floor(py / self.world_height * self.regions_y).astype(np.int64)
        rx = np.clip(rx, 0, self.regions_x - 1)
        ry = np.clip(ry, 0, self.regions_y - 1)
        return (ry * self.regions_x + rx).astype(np.int32, copy=False)

    def observe_population(
        self,
        *,
        x: np.ndarray,
        y: np.ndarray,
        cell_ids: np.ndarray,
        local_resources: np.ndarray,
        local_hazard: np.ndarray,
    ) -> None:
        regions = self.region_ids(x, y)
        self.observed_ticks += 1
        self.current_alive = np.bincount(
            regions, minlength=self.region_count
        ).astype(np.int64, copy=False)
        self.entity_ticks += self.current_alive
        if regions.size == 0:
            return
        hazard = np.asarray(local_hazard, dtype=np.float64)
        resources = np.asarray(local_resources, dtype=np.float64)
        capacities = np.maximum(np.asarray(self.resource_capacity, dtype=np.float64), 1e-30)
        scarcity = 1.0 - np.clip(resources / capacities[None, :], 0.0, 1.0).mean(axis=1)
        cells = np.asarray(cell_ids, dtype=np.int64)
        occupancy = np.bincount(
            cells, minlength=int(self.world_grid_x * self.world_grid_y)
        ).astype(np.float64, copy=False)
        local_crowding = occupancy[cells]
        self.hazard_exposure += np.bincount(
            regions, weights=hazard, minlength=self.region_count
        )
        self.scarcity_exposure += np.bincount(
            regions, weights=scarcity, minlength=self.region_count
        )
        self.crowding_exposure += np.bincount(
            regions, weights=local_crowding, minlength=self.region_count
        )

    def observe_births(self, indices: np.ndarray, x: np.ndarray, y: np.ndarray) -> None:
        rows = np.asarray(indices, dtype=np.int32)
        if rows.size:
            regions = self.region_ids(np.asarray(x)[rows], np.asarray(y)[rows])
            self.births += np.bincount(regions, minlength=self.region_count)

    def observe_deaths(self, indices: np.ndarray, x: np.ndarray, y: np.ndarray) -> None:
        rows = np.asarray(indices, dtype=np.int32)
        if rows.size:
            regions = self.region_ids(np.asarray(x)[rows], np.asarray(y)[rows])
            self.deaths += np.bincount(regions, minlength=self.region_count)

    def observe_benefits(
        self,
        *,
        owner_indices: np.ndarray,
        target_indices: np.ndarray,
        group_ids: np.ndarray,
        amounts: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
    ) -> None:
        owners = np.asarray(owner_indices, dtype=np.int32)
        targets = np.asarray(target_indices, dtype=np.int32)
        values = np.asarray(amounts, dtype=np.float64)
        if owners.size == 0:
            return
        owner_groups = np.asarray(group_ids, dtype=np.uint64)[owners]
        target_groups = np.asarray(group_ids, dtype=np.uint64)[targets]
        kinds = np.full(owners.size, FLOW_UNBOUNDED, dtype=np.int8)
        owner_grouped = owner_groups != 0
        target_grouped = target_groups != 0
        kinds[owner_grouped & (owner_groups == target_groups)] = FLOW_INTERNAL
        kinds[owner_grouped & target_grouped & (owner_groups != target_groups)] = (
            FLOW_GROUP_TO_GROUP
        )
        kinds[owner_grouped & ~target_grouped] = FLOW_GROUP_TO_UNGROUPED
        kinds[~owner_grouped & target_grouped] = FLOW_UNGROUPED_TO_GROUP
        regions = self.region_ids(np.asarray(x)[owners], np.asarray(y)[owners])
        np.add.at(self.benefit_flow, (regions, kinds), values)

    def consume_window(self) -> dict[str, Any]:
        exposure = self.entity_ticks.astype(np.float64)
        mean_alive = exposure / max(int(self.observed_ticks), 1)
        # Match the global-window denominator: deaths divided by surviving
        # population plus deaths.  Entity-tick rates remain available through
        # the raw exposure arrays when needed.
        mortality = _safe_ratio(self.deaths, mean_alive + self.deaths)
        birth_rate = _safe_ratio(self.births, np.maximum(mean_alive, 1.0))
        hazard = _safe_ratio(self.hazard_exposure, exposure)
        scarcity = _safe_ratio(self.scarcity_exposure, exposure)
        crowding = _safe_ratio(self.crowding_exposure, exposure)
        alive_delta = self.current_alive - self.previous_alive
        alive_change_rate = _safe_ratio(alive_delta, np.maximum(self.previous_alive, 1))

        internal = self.benefit_flow[:, FLOW_INTERNAL]
        cross = self.benefit_flow[:, FLOW_GROUP_TO_GROUP:FLOW_UNBOUNDED].sum(axis=1)
        unbounded = self.benefit_flow[:, FLOW_UNBOUNDED]
        boundary = internal + cross
        benefit_total = boundary + unbounded
        cohesion = _safe_ratio(internal, boundary)
        coverage = _safe_ratio(boundary, benefit_total)
        outgoing = internal + self.benefit_flow[:, FLOW_GROUP_TO_GROUP] + self.benefit_flow[:, FLOW_GROUP_TO_UNGROUPED]
        outgoing_retention = _safe_ratio(internal, outgoing)
        benefit_valid = boundary > 0.0
        occupied = exposure > 0.0

        payload: dict[str, Any] = {
            "spatial_local_stress_schema": "spatial-local-stress-diagnostics-v1",
            "spatial_local_regions_x": int(self.regions_x),
            "spatial_local_regions_y": int(self.regions_y),
            "spatial_local_observed_ticks": int(self.observed_ticks),
            "spatial_local_region_alive": self.current_alive.tolist(),
            "spatial_local_region_alive_delta": alive_delta.tolist(),
            "spatial_local_region_alive_change_rate": alive_change_rate.tolist(),
            "spatial_local_region_entity_ticks": self.entity_ticks.tolist(),
            "spatial_local_region_births": self.births.tolist(),
            "spatial_local_region_deaths": self.deaths.tolist(),
            "spatial_local_region_mortality_pressure": mortality.tolist(),
            "spatial_local_region_birth_pressure": birth_rate.tolist(),
            "spatial_local_region_hazard_exposure": hazard.tolist(),
            "spatial_local_region_resource_scarcity": scarcity.tolist(),
            "spatial_local_region_crowding": crowding.tolist(),
            "spatial_local_region_benefit_internal": internal.tolist(),
            "spatial_local_region_benefit_cross_boundary": cross.tolist(),
            "spatial_local_region_benefit_unbounded": unbounded.tolist(),
            "spatial_local_region_boundary_coverage": coverage.tolist(),
            "spatial_local_region_boundary_cohesion": cohesion.tolist(),
            "spatial_local_region_outgoing_retention": outgoing_retention.tolist(),
            "spatial_local_region_cohesion_valid": benefit_valid.tolist(),
            "spatial_local_occupied_region_count": int(np.count_nonzero(occupied)),
            "spatial_local_population_cv": _coefficient_of_variation(self.current_alive, occupied),
            "spatial_local_mortality_pressure_cv": _coefficient_of_variation(mortality, occupied),
            "spatial_local_resource_scarcity_cv": _coefficient_of_variation(scarcity, occupied),
            "spatial_local_hazard_exposure_cv": _coefficient_of_variation(hazard, occupied),
            "spatial_local_crowding_cv": _coefficient_of_variation(crowding, occupied),
            "spatial_local_cohesion_cv": _coefficient_of_variation(cohesion, benefit_valid),
            "spatial_local_max_mortality_pressure": float(np.max(mortality[occupied])) if np.any(occupied) else 0.0,
            "spatial_local_max_resource_scarcity": float(np.max(scarcity[occupied])) if np.any(occupied) else 0.0,
            "spatial_local_max_crowding": float(np.max(crowding[occupied])) if np.any(occupied) else 0.0,
        }
        self.previous_alive = self.current_alive.copy()
        self.observed_ticks = 0
        self.entity_ticks.fill(0)
        self.hazard_exposure.fill(0.0)
        self.scarcity_exposure.fill(0.0)
        self.crowding_exposure.fill(0.0)
        self.births.fill(0)
        self.deaths.fill(0)
        self.benefit_flow.fill(0.0)
        return payload


__all__ = ["LocalStressDiagnostics"]
