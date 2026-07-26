"""Observational spatial stress and cultural-transfer diagnostics.

The tracker partitions the physical world into a small fixed analysis grid. It
never changes policy, movement, resource fields, groups, or knowledge. All
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

SCHEMA_STRESS_V1 = "spatial-local-stress-diagnostics-v1"
SCHEMA_CULTURE_V2 = "spatial-local-stress-culture-diagnostics-v2"
REFERENCE_BOUNDARY_SCHEMA = "checkpoint-frozen-stable-entity-boundary-v1"


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


def _effective_count(values: np.ndarray) -> float:
    counts = np.asarray(values, dtype=np.float64)
    counts = counts[counts > 0.0]
    if counts.size == 0:
        return 0.0
    shares = counts / counts.sum()
    return float(1.0 / np.sum(shares * shares))


@dataclass
class LocalStressDiagnostics:
    """Windowed local population, environment, benefit, and culture accounting."""

    world_width: float
    world_height: float
    regions_x: int
    regions_y: int
    resource_capacity: tuple[float, float, float, float]
    world_grid_x: int
    world_grid_y: int
    schema: str = SCHEMA_STRESS_V1

    def __post_init__(self) -> None:
        self.region_count = int(self.regions_x * self.regions_y)
        if self.regions_x <= 0 or self.regions_y <= 0:
            raise ValueError("local diagnostic region dimensions must be positive")
        if self.schema not in {SCHEMA_STRESS_V1, SCHEMA_CULTURE_V2}:
            raise ValueError(f"unsupported local diagnostic schema {self.schema!r}")
        self.culture_enabled = self.schema == SCHEMA_CULTURE_V2
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
        self.transfer_attempt_flow = np.zeros(
            (self.region_count, self.region_count), dtype=np.int64
        )
        self.transfer_commit_flow = np.zeros(
            (self.region_count, self.region_count), dtype=np.int64
        )
        self.transfer_byte_flow = np.zeros(
            (self.region_count, self.region_count), dtype=np.int64
        )
        self.current_root_presence: set[tuple[int, int]] = set()
        self.previous_root_presence: set[tuple[int, int]] = set()
        self.current_root_holder_presence: set[tuple[int, int, int]] = set()
        self.reference_boundary_enabled = False
        self.reference_boundary_snapshot_tick = 0
        self.reference_boundary_entity_ids = np.zeros(0, dtype=np.uint64)
        self.reference_boundary_group_tokens = np.zeros(0, dtype=np.uint64)
        self.reference_benefit_flow = np.zeros(
            (self.region_count, FLOW_COUNT), dtype=np.float64
        )

    def clone(self) -> "LocalStressDiagnostics":
        return copy.deepcopy(self)

    def snapshot_state(self) -> dict[str, Any]:
        return copy.deepcopy(self.__dict__)

    def restore_state(self, state: dict[str, Any]) -> None:
        for key, value in state.items():
            setattr(self, key, copy.deepcopy(value))
        # Trusted v0.19 checkpoints do not contain cultural accounting fields.
        self.schema = str(getattr(self, "schema", SCHEMA_STRESS_V1))
        self.culture_enabled = bool(
            getattr(self, "culture_enabled", self.schema == SCHEMA_CULTURE_V2)
        )
        if not hasattr(self, "transfer_attempt_flow"):
            self.transfer_attempt_flow = np.zeros(
                (self.region_count, self.region_count), dtype=np.int64
            )
            self.transfer_commit_flow = np.zeros_like(self.transfer_attempt_flow)
            self.transfer_byte_flow = np.zeros_like(self.transfer_attempt_flow)
            self.current_root_presence = set()
            self.previous_root_presence = set()
            self.current_root_holder_presence = set()
        if not hasattr(self, "reference_boundary_enabled"):
            self.reference_boundary_enabled = False
            self.reference_boundary_snapshot_tick = 0
            self.reference_boundary_entity_ids = np.zeros(0, dtype=np.uint64)
            self.reference_boundary_group_tokens = np.zeros(0, dtype=np.uint64)
            self.reference_benefit_flow = np.zeros(
                (self.region_count, FLOW_COUNT), dtype=np.float64
            )

    def freeze_reference_boundary(
        self,
        *,
        tick: int,
        alive: np.ndarray,
        stable_ids: np.ndarray,
        group_tokens: np.ndarray,
    ) -> None:
        """Freeze one diagnostic-only group partition for paired branches.

        Membership is keyed by both physical slot and stable entity ID.  A slot
        reused after the checkpoint therefore does not inherit the old group.
        The boundary affects only accounting fields emitted by this tracker.
        """

        if int(self.observed_ticks) != 0:
            raise ValueError(
                "reference boundary requires a checkpoint aligned with the local diagnostic window"
            )

        alive_values = np.asarray(alive, dtype=bool)
        ids = np.asarray(stable_ids, dtype=np.uint64)
        groups = np.asarray(group_tokens, dtype=np.uint64)
        if any(value.ndim != 1 for value in (alive_values, ids, groups)) or not (
            alive_values.size == ids.size == groups.size
        ):
            raise ValueError("reference boundary arrays must be aligned and one-dimensional")
        self.reference_boundary_entity_ids = np.zeros(ids.size, dtype=np.uint64)
        self.reference_boundary_group_tokens = np.zeros(groups.size, dtype=np.uint64)
        self.reference_boundary_entity_ids[alive_values] = ids[alive_values]
        self.reference_boundary_group_tokens[alive_values] = groups[alive_values]
        self.reference_boundary_snapshot_tick = int(tick)
        self.reference_boundary_enabled = True
        self.reference_benefit_flow.fill(0.0)

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
        stable_ids: np.ndarray | None = None,
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
        if self.reference_boundary_enabled:
            if stable_ids is None:
                raise ValueError(
                    "stable IDs are required while the reference boundary is enabled"
                )
            current_ids = np.asarray(stable_ids, dtype=np.uint64)
            if current_ids.ndim != 1 or current_ids.size != self.reference_boundary_entity_ids.size:
                raise ValueError("stable IDs must match the frozen reference boundary capacity")
            owner_match = (
                self.reference_boundary_entity_ids[owners] == current_ids[owners]
            )
            target_match = (
                self.reference_boundary_entity_ids[targets] == current_ids[targets]
            )
            reference_owner_groups = np.where(
                owner_match, self.reference_boundary_group_tokens[owners], 0
            )
            reference_target_groups = np.where(
                target_match, self.reference_boundary_group_tokens[targets], 0
            )
            reference_kinds = np.full(owners.size, FLOW_UNBOUNDED, dtype=np.int8)
            reference_owner_grouped = reference_owner_groups != 0
            reference_target_grouped = reference_target_groups != 0
            reference_kinds[
                reference_owner_grouped
                & (reference_owner_groups == reference_target_groups)
            ] = FLOW_INTERNAL
            reference_kinds[
                reference_owner_grouped
                & reference_target_grouped
                & (reference_owner_groups != reference_target_groups)
            ] = FLOW_GROUP_TO_GROUP
            reference_kinds[
                reference_owner_grouped & ~reference_target_grouped
            ] = FLOW_GROUP_TO_UNGROUPED
            reference_kinds[
                ~reference_owner_grouped & reference_target_grouped
            ] = FLOW_UNGROUPED_TO_GROUP
            np.add.at(
                self.reference_benefit_flow,
                (regions, reference_kinds),
                values,
            )

    def observe_transfers(
        self,
        *,
        plan: Any,
        audit: Any,
        x: np.ndarray,
        y: np.ndarray,
    ) -> None:
        """Account transfer attempts and successful commits by physical region."""
        if not self.culture_enabled:
            return
        senders = np.asarray(plan.sender_entity_indices, dtype=np.int32)
        receivers = np.asarray(plan.receiver_entity_indices, dtype=np.int32)
        if senders.size:
            source_regions = self.region_ids(np.asarray(x)[senders], np.asarray(y)[senders])
            destination_regions = self.region_ids(
                np.asarray(x)[receivers], np.asarray(y)[receivers]
            )
            np.add.at(
                self.transfer_attempt_flow,
                (source_regions, destination_regions),
                1,
            )
        committed_senders = np.asarray(audit.sender_entity_indices, dtype=np.int32)
        committed_receivers = np.asarray(audit.receiver_entity_indices, dtype=np.int32)
        if committed_senders.size:
            source_regions = self.region_ids(
                np.asarray(x)[committed_senders], np.asarray(y)[committed_senders]
            )
            destination_regions = self.region_ids(
                np.asarray(x)[committed_receivers], np.asarray(y)[committed_receivers]
            )
            committed_bytes = np.asarray(audit.committed_bytes, dtype=np.int64)
            np.add.at(
                self.transfer_commit_flow,
                (source_regions, destination_regions),
                1,
            )
            np.add.at(
                self.transfer_byte_flow,
                (source_regions, destination_regions),
                committed_bytes,
            )

    def observe_transferred_roots(
        self,
        *,
        entity_indices: np.ndarray,
        root_ids: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
    ) -> None:
        if not self.culture_enabled:
            return
        entities = np.asarray(entity_indices, dtype=np.int32)
        roots = np.asarray(root_ids, dtype=np.uint64)
        if entities.shape != roots.shape:
            raise ValueError("transferred-root entity and root arrays must align")
        if entities.size == 0:
            self.current_root_presence = set()
            self.current_root_holder_presence = set()
            return
        regions = self.region_ids(np.asarray(x)[entities], np.asarray(y)[entities])
        self.current_root_holder_presence = {
            (int(region), int(root), int(entity))
            for region, root, entity in zip(regions, roots, entities, strict=True)
        }
        self.current_root_presence = {
            (region, root)
            for region, root, _ in self.current_root_holder_presence
        }

    def _culture_payload(self) -> dict[str, Any]:
        outgoing_attempts = self.transfer_attempt_flow.sum(axis=1)
        incoming_attempts = self.transfer_attempt_flow.sum(axis=0)
        outgoing_commits = self.transfer_commit_flow.sum(axis=1)
        incoming_commits = self.transfer_commit_flow.sum(axis=0)
        outgoing_bytes = self.transfer_byte_flow.sum(axis=1)
        incoming_bytes = self.transfer_byte_flow.sum(axis=0)
        diagonal_attempts = int(np.trace(self.transfer_attempt_flow))
        diagonal_commits = int(np.trace(self.transfer_commit_flow))
        attempts_total = int(self.transfer_attempt_flow.sum())
        commits_total = int(self.transfer_commit_flow.sum())

        roots_by_region: list[set[int]] = [set() for _ in range(self.region_count)]
        previous_by_region: list[set[int]] = [set() for _ in range(self.region_count)]
        for region, root in self.current_root_presence:
            roots_by_region[region].add(root)
        for region, root in self.previous_root_presence:
            previous_by_region[region].add(root)
        new_counts = np.asarray(
            [len(current - previous) for current, previous in zip(roots_by_region, previous_by_region, strict=True)],
            dtype=np.int64,
        )
        lost_counts = np.asarray(
            [len(previous - current) for current, previous in zip(roots_by_region, previous_by_region, strict=True)],
            dtype=np.int64,
        )
        root_counts = np.asarray([len(values) for values in roots_by_region], dtype=np.int64)
        holder_counts_by_region: list[dict[int, int]] = [
            {} for _ in range(self.region_count)
        ]
        for region, root, _ in self.current_root_holder_presence:
            counts = holder_counts_by_region[region]
            counts[root] = counts.get(root, 0) + 1
        effective_roots = np.asarray(
            [
                _effective_count(np.asarray(list(counts.values()), dtype=np.float64))
                for counts in holder_counts_by_region
            ],
            dtype=np.float64,
        )
        root_regions: dict[int, set[int]] = {}
        for region, roots in enumerate(roots_by_region):
            for root in roots:
                root_regions.setdefault(root, set()).add(region)
        multi_region_roots = sum(len(regions) > 1 for regions in root_regions.values())

        return {
            "spatial_local_culture_schema": "spatial-cultural-transfer-diagnostics-v1",
            "spatial_local_region_transfer_attempts_outgoing": outgoing_attempts.tolist(),
            "spatial_local_region_transfer_attempts_incoming": incoming_attempts.tolist(),
            "spatial_local_region_transfer_committed_outgoing": outgoing_commits.tolist(),
            "spatial_local_region_transfer_committed_incoming": incoming_commits.tolist(),
            "spatial_local_region_transfer_committed_bytes_outgoing": outgoing_bytes.tolist(),
            "spatial_local_region_transfer_committed_bytes_incoming": incoming_bytes.tolist(),
            "spatial_local_transfer_attempt_flow": self.transfer_attempt_flow.tolist(),
            "spatial_local_transfer_commit_flow": self.transfer_commit_flow.tolist(),
            "spatial_local_transfer_byte_flow": self.transfer_byte_flow.tolist(),
            "spatial_local_transfer_same_region_attempts": diagonal_attempts,
            "spatial_local_transfer_cross_region_attempts": attempts_total - diagonal_attempts,
            "spatial_local_transfer_same_region_committed": diagonal_commits,
            "spatial_local_transfer_cross_region_committed": commits_total - diagonal_commits,
            "spatial_local_region_active_transferred_roots": root_counts.tolist(),
            "spatial_local_region_effective_transferred_roots": effective_roots.tolist(),
            "spatial_local_region_new_transferred_roots": new_counts.tolist(),
            "spatial_local_region_lost_transferred_roots": lost_counts.tolist(),
            "spatial_local_active_transferred_root_presence_count": int(
                len(self.current_root_holder_presence)
            ),
            "spatial_local_active_transferred_root_count": int(len(root_regions)),
            "spatial_local_multi_region_transferred_root_count": int(multi_region_roots),
            "spatial_local_transfer_commit_rate_by_source": _safe_ratio(
                outgoing_commits, outgoing_attempts
            ).tolist(),
            "spatial_local_transfer_commit_rate_by_destination": _safe_ratio(
                incoming_commits, incoming_attempts
            ).tolist(),
        }

    def consume_window(self) -> dict[str, Any]:
        exposure = self.entity_ticks.astype(np.float64)
        mean_alive = exposure / max(int(self.observed_ticks), 1)
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
        outgoing = (
            internal
            + self.benefit_flow[:, FLOW_GROUP_TO_GROUP]
            + self.benefit_flow[:, FLOW_GROUP_TO_UNGROUPED]
        )
        outgoing_retention = _safe_ratio(internal, outgoing)
        benefit_valid = boundary > 0.0
        occupied = exposure > 0.0

        payload: dict[str, Any] = {
            "spatial_local_stress_schema": self.schema,
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
        if self.reference_boundary_enabled:
            reference_internal = self.reference_benefit_flow[:, FLOW_INTERNAL]
            reference_cross = self.reference_benefit_flow[
                :, FLOW_GROUP_TO_GROUP:FLOW_UNBOUNDED
            ].sum(axis=1)
            reference_unbounded = self.reference_benefit_flow[:, FLOW_UNBOUNDED]
            reference_boundary = reference_internal + reference_cross
            reference_total = reference_boundary + reference_unbounded
            reference_outgoing = (
                reference_internal
                + self.reference_benefit_flow[:, FLOW_GROUP_TO_GROUP]
                + self.reference_benefit_flow[:, FLOW_GROUP_TO_UNGROUPED]
            )
            reference_cohesion = _safe_ratio(
                reference_internal, reference_boundary
            )
            reference_valid = reference_boundary > 0.0
            payload.update(
                {
                    "spatial_local_reference_boundary_schema": REFERENCE_BOUNDARY_SCHEMA,
                    "spatial_local_reference_boundary_snapshot_tick": int(
                        self.reference_boundary_snapshot_tick
                    ),
                    "spatial_local_region_reference_benefit_internal": reference_internal.tolist(),
                    "spatial_local_region_reference_benefit_cross_boundary": reference_cross.tolist(),
                    "spatial_local_region_reference_benefit_unbounded": reference_unbounded.tolist(),
                    "spatial_local_region_reference_boundary_coverage": _safe_ratio(
                        reference_boundary, reference_total
                    ).tolist(),
                    "spatial_local_region_reference_boundary_cohesion": reference_cohesion.tolist(),
                    "spatial_local_region_reference_outgoing_retention": _safe_ratio(
                        reference_internal, reference_outgoing
                    ).tolist(),
                    "spatial_local_region_reference_cohesion_valid": reference_valid.tolist(),
                    "spatial_local_region_boundary_definition_gap": (
                        cohesion - reference_cohesion
                    ).tolist(),
                }
            )
        if self.culture_enabled:
            payload.update(self._culture_payload())

        self.previous_alive = self.current_alive.copy()
        self.previous_root_presence = set(self.current_root_presence)
        self.observed_ticks = 0
        self.entity_ticks.fill(0)
        self.hazard_exposure.fill(0.0)
        self.scarcity_exposure.fill(0.0)
        self.crowding_exposure.fill(0.0)
        self.births.fill(0)
        self.deaths.fill(0)
        self.benefit_flow.fill(0.0)
        self.reference_benefit_flow.fill(0.0)
        self.transfer_attempt_flow.fill(0)
        self.transfer_commit_flow.fill(0)
        self.transfer_byte_flow.fill(0)
        return payload


__all__ = [
    "LocalStressDiagnostics",
    "SCHEMA_STRESS_V1",
    "SCHEMA_CULTURE_V2",
    "REFERENCE_BOUNDARY_SCHEMA",
]
