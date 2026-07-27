"""Backend-neutral action conflict planning.

Policies emit immutable intents; this module turns a read-only world snapshot
into a resolution plan without mutating the world.  The plan is deliberately
separate from the later commit so CPU, GPU, distributed, or replay resolvers
can share the same auditable intent/result contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

import numpy as np

from .cfg import SimulationConfig
from .intents import ActionIntentBatch, ActionResolutionBatch, FailureReason, action_rows, empty_resolutions
from se.evolution.lifecycle import BirthRequestPlan, empty_birth_request_plan
from .policy import Action
from .random_api import RandomContext, Stream, keys, uniform01
from se.env.niches import harvest_request_rates, selective_harvest_enabled
from se.subjects.social import (
    RelationUpdatePlan,
    build_share_relation_update_plan,
    empty_relation_update_plan,
)


# The strict CPU allocator accepts NumPy arrays while a device planner keeps
# its temporary keys on its selected backend.  The plan itself is always a
# host-side, auditable value consumed by the world-commit phase.
HarvestAllocator = Callable[[Any, Any], Any]


def order_reproduction_candidates(
    candidates: np.ndarray,
    carrier_ids: np.ndarray,
    *,
    rule: str,
    run_seed: int,
    tick: int,
) -> np.ndarray:
    """Return a canonical capacity-priority order for reproduction intents.

    ``stable-id-v1`` preserves archived-run semantics.  The current
    ``stateless-random-v1`` rule derives one reproducible uint64 priority from
    run seed, tick, stream, and stable entity ID.  SplitMix64 is a permutation
    over uint64 inputs for a fixed context, so distinct stable IDs receive a
    total order without mutable RNG state.  Stable ID remains only a defensive
    tie breaker for malformed third-party batches containing duplicate IDs.
    """
    rows = np.asarray(candidates)
    ids = np.asarray(carrier_ids)
    if rows.ndim != 1 or not np.issubdtype(rows.dtype, np.integer):
        raise ValueError("reproduction candidates must be a one-dimensional integer array")
    if ids.ndim != 1 or not np.issubdtype(ids.dtype, np.integer):
        raise ValueError("reproduction carrier IDs must be a one-dimensional integer array")
    if int(tick) < 0:
        raise ValueError("reproduction arbitration tick must be non-negative")
    if rows.size == 0:
        return rows.astype(np.int32, copy=True)
    if np.any(rows < 0) or np.any(rows >= ids.size):
        raise ValueError("reproduction candidate row is outside the intent batch")
    candidate_ids = ids[rows].astype(np.uint64, copy=False)
    if np.any(candidate_ids == 0):
        raise ValueError("reproduction candidates require positive stable IDs")
    if rule == "stable-id-v1":
        priority = candidate_ids
    elif rule == "stateless-random-v1":
        priority = keys(
            RandomContext(
                int(run_seed),
                int(tick),
                phase=60,
                stream=Stream.REPRODUCTION_CAPACITY,
            ),
            candidate_ids,
            draw_index=0,
        )
    else:
        raise ValueError(f"unknown reproduction capacity arbitration rule: {rule!r}")
    order = np.lexsort((candidate_ids, priority))
    return rows[order].astype(np.int32, copy=False)


@dataclass(frozen=True)
class ActionResolutionSnapshot:
    """The minimal immutable world view required for intent arbitration."""

    active: np.ndarray
    cells: np.ndarray
    entity_id: np.ndarray
    alive: np.ndarray
    energy: np.ndarray
    fertility: np.ndarray
    primary_subject_id: np.ndarray
    free_slot_count: int
    resource_affinity_q: np.ndarray | None = None
    harvest_preference_q: np.ndarray | None = None


@dataclass(frozen=True)
class ActionResolutionPlan:
    """Resolved effects, still separated from all world mutation."""

    resolutions: ActionResolutionBatch
    harvest_rows: np.ndarray
    harvest_cells: np.ndarray
    gathered: np.ndarray
    requested: np.ndarray
    share: ShareResolution
    signal_rows: np.ndarray
    birth_requests: BirthRequestPlan


@dataclass(frozen=True)
class HarvestResolution:
    """The resolved harvest portion of an otherwise backend-neutral plan.

    ``rows`` and ``cells`` use the same stable ``(cell, entity_id)`` ordering
    as the reference implementation.  Producing this value never deducts
    resources; the simulation's later commit phase remains the sole writer.
    """

    rows: np.ndarray
    cells: np.ndarray
    gathered: np.ndarray
    requested: np.ndarray


@dataclass(frozen=True)
class ShareResolution:
    """Resolved energy transfers and their independent relation-event plan."""

    rows: np.ndarray
    owner_indices: np.ndarray
    target_indices: np.ndarray
    amounts: np.ndarray
    success: np.ndarray
    valid_target: np.ndarray
    relation_updates: RelationUpdatePlan


class GpuHarvestPlanner(Protocol):
    """Minimal device-facing capability needed by :class:`GpuActionConflictResolver`.

    Deliberately passing only immutable intent/snapshot data prevents a GPU
    planner from observing policy-internal state or mutating the host world.
    """

    def resolve_harvest_plan(
        self,
        snapshot: ActionResolutionSnapshot,
        intents: ActionIntentBatch,
    ) -> HarvestResolution:
        """Return one stable, non-mutating harvest allocation plan."""


class ActionConflictResolver(Protocol):
    """Extension point for strict, GPU, distributed, or replay resolution."""

    def resolve(
        self,
        snapshot: ActionResolutionSnapshot,
        intents: ActionIntentBatch,
        harvest_allocator: HarvestAllocator,
    ) -> ActionResolutionPlan:
        """Resolve a stable intent batch without mutating the supplied snapshot."""


class DeterministicActionConflictResolver:
    """Reference resolver using explicit stable ordering for contested targets."""

    scientific_safe = True

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg

    def _resolve_shares(
        self,
        snapshot: ActionResolutionSnapshot,
        intents: ActionIntentBatch,
        resolutions: ActionResolutionBatch,
    ) -> ShareResolution:
        rows = action_rows(intents, Action.SHARE)
        if rows.size == 0:
            return ShareResolution(
                rows=rows,
                owner_indices=np.empty(0, dtype=np.int32),
                target_indices=np.empty(0, dtype=np.int32),
                amounts=np.empty(0, dtype=np.float32),
                success=np.empty(0, dtype=bool),
                valid_target=np.empty(0, dtype=bool),
                relation_updates=empty_relation_update_plan(intents.submit_tick),
            )
        owners = intents.carrier_index[rows]
        targets = intents.target_index[rows]
        in_bounds = (targets >= 0) & (targets < snapshot.alive.size)
        safe_targets = np.where(in_bounds, targets, 0)
        valid = in_bounds & snapshot.alive[safe_targets] & (safe_targets != owners)
        order = np.lexsort((intents.carrier_id[rows], snapshot.entity_id[safe_targets]))
        rows = rows[order]
        owners = owners[order]
        targets = targets[order]
        valid = valid[order]
        safe_targets = safe_targets[order]
        proposed = np.where(
            valid,
            np.minimum(self.cfg.entities.share_amount, np.maximum(snapshot.energy[owners] - 0.5, 0.0)),
            0.0,
        ).astype(np.float32)
        total_by_target = np.bincount(
            safe_targets, weights=proposed, minlength=snapshot.alive.size
        ).astype(np.float32)
        capacity = np.maximum(self.cfg.entities.max_energy - snapshot.energy, 0.0)
        scale = np.ones(snapshot.alive.size, dtype=np.float32)
        occupied = total_by_target > 0
        scale[occupied] = np.minimum(1.0, capacity[occupied] / total_by_target[occupied])
        actual = proposed * scale[safe_targets]
        success = actual > 1e-8
        resolutions.success[rows] = success
        invalid = ~valid
        insufficient_resource = valid & (proposed <= 1e-8)
        insufficient_capacity = valid & (proposed > 1e-8) & ~success
        resolutions.failure_reason[rows[invalid]] = FailureReason.INVALID_TARGET
        resolutions.failure_reason[rows[insufficient_resource]] = FailureReason.INSUFFICIENT_RESOURCE
        resolutions.failure_reason[rows[insufficient_capacity]] = FailureReason.INSUFFICIENT_CAPACITY
        resolutions.resource_delta[rows, 0] = -actual
        relation_updates = build_share_relation_update_plan(
            self.cfg,
            rows,
            owners,
            targets,
            success,
            valid,
            intents.submit_tick,
        )
        return ShareResolution(
            rows=rows,
            owner_indices=owners.astype(np.int32, copy=False),
            target_indices=targets.astype(np.int32, copy=False),
            amounts=actual.astype(np.float32, copy=False),
            success=success,
            valid_target=valid,
            relation_updates=relation_updates,
        )

    def _resolve_harvest(
        self,
        snapshot: ActionResolutionSnapshot,
        intents: ActionIntentBatch,
        harvest_allocator: HarvestAllocator,
    ) -> HarvestResolution:
        """Resolve harvests with the strict CPU reference ordering."""
        harvest_rows = action_rows(intents, Action.HARVEST)
        if harvest_rows.size == 0:
            return HarvestResolution(
                harvest_rows,
                np.empty(0, dtype=np.int32),
                np.empty((0, 4), dtype=np.float32),
                np.empty((0, 4), dtype=np.float32),
            )
        observation_rows = np.searchsorted(snapshot.active, intents.carrier_index[harvest_rows])
        harvest_cells = snapshot.cells[observation_rows]
        order = np.lexsort((intents.carrier_id[harvest_rows], harvest_cells))
        harvest_rows = harvest_rows[order]
        harvest_cells = harvest_cells[order]
        harvester_indices = intents.carrier_index[harvest_rows]
        affinity = (
            None
            if not selective_harvest_enabled(self.cfg)
            else (
                None
                if (snapshot.harvest_preference_q is None and snapshot.resource_affinity_q is None)
                else (
                    snapshot.harvest_preference_q[harvester_indices]
                    if snapshot.harvest_preference_q is not None
                    else snapshot.resource_affinity_q[harvester_indices]
                )
            )
        )
        channel_draws = (
            None
            if not selective_harvest_enabled(self.cfg)
            else uniform01(
                RandomContext(
                    self.cfg.run.seed,
                    intents.submit_tick,
                    phase=42,
                    stream=Stream.HARVEST_CHANNEL,
                ),
                intents.carrier_id[harvest_rows],
                draw_index=0,
            )
        )
        rates = harvest_request_rates(
            affinity,
            self.cfg,
            rows=int(harvest_rows.size),
            channel_draws=channel_draws,
        )
        gathered = np.asarray(harvest_allocator(harvest_cells, rates), dtype=np.float32)
        return HarvestResolution(harvest_rows, harvest_cells, gathered, rates)

    def resolve(
        self,
        snapshot: ActionResolutionSnapshot,
        intents: ActionIntentBatch,
        harvest_allocator: HarvestAllocator,
    ) -> ActionResolutionPlan:
        resolutions = empty_resolutions(intents)

        harvest = self._resolve_harvest(snapshot, intents, harvest_allocator)
        harvest_rows = harvest.rows
        harvest_cells = harvest.cells
        gathered = harvest.gathered
        if harvest_rows.size:
            resolutions.resource_delta[harvest_rows] = gathered
            harvested = (
                gathered[:, 0] > 1e-8
                if self.cfg.environment.schema == "legacy-four-channel-v1"
                else np.any(gathered > 1e-8, axis=1)
            )
            resolutions.success[harvest_rows] = harvested
            resolutions.failure_reason[harvest_rows[~harvested]] = FailureReason.INSUFFICIENT_RESOURCE

        share = self._resolve_shares(snapshot, intents, resolutions)

        signal_rows = action_rows(intents, Action.SIGNAL)
        if signal_rows.size:
            resolutions.energy_cost[signal_rows] = self.cfg.entities.signal_cost

        reproduce_rows = action_rows(intents, Action.REPRODUCE)
        capacity_rule = self.cfg.entities.reproduction_capacity_arbitration
        birth_requests = empty_birth_request_plan(
            intents.submit_tick,
            capacity_arbitration=capacity_rule,
            capacity_available_slots=snapshot.free_slot_count,
        )
        if reproduce_rows.size:
            parents = intents.carrier_index[reproduce_rows]
            valid_parent = (
                snapshot.energy[parents] >= self.cfg.entities.reproduction_threshold
            ) & (snapshot.fertility[parents] >= 0.5)
            invalid_rows = reproduce_rows[~valid_parent]
            resolutions.success[invalid_rows] = False
            resolutions.failure_reason[invalid_rows] = FailureReason.INSUFFICIENT_RESOURCE
            candidates = order_reproduction_candidates(
                reproduce_rows[valid_parent],
                intents.carrier_id,
                rule=self.cfg.entities.reproduction_capacity_arbitration,
                run_seed=self.cfg.run.seed,
                tick=intents.submit_tick,
            )
            accepted_reproduce_rows = candidates[: snapshot.free_slot_count]
            rejected = candidates[snapshot.free_slot_count :]
            resolutions.success[rejected] = False
            resolutions.failure_reason[rejected] = FailureReason.INSUFFICIENT_CAPACITY
            resolutions.energy_cost[accepted_reproduce_rows] = self.cfg.entities.reproduction_cost
            accepted_parents = intents.carrier_index[accepted_reproduce_rows]
            birth_requests = BirthRequestPlan(
                source_rows=accepted_reproduce_rows.astype(np.int32, copy=False),
                parent_indices=accepted_parents.astype(np.int32, copy=False),
                parent_entity_ids=snapshot.entity_id[accepted_parents].astype(np.uint64, copy=True),
                parent_subject_ids=snapshot.primary_subject_id[accepted_parents].astype(
                    np.uint64, copy=True
                ),
                tick=int(intents.submit_tick),
                capacity_arbitration=capacity_rule,
                capacity_candidate_count=int(candidates.size),
                capacity_available_slots=int(snapshot.free_slot_count),
            )

        return ActionResolutionPlan(
            resolutions=resolutions,
            harvest_rows=harvest_rows,
            harvest_cells=harvest_cells,
            gathered=gathered,
            requested=harvest.requested,
            share=share,
            signal_rows=signal_rows,
            birth_requests=birth_requests,
        )


class GpuActionConflictResolver(DeterministicActionConflictResolver):
    """Device-backed harvest planning with the reference CPU commit contract.

    Only the harvest subset is delegated.  Movement is deliberately left as
    a successful intent in the common resolution batch because it has no
    contested shared state in the present model; its actual position change
    remains in the single world-commit phase.  Share arbitration still
    reuses the strict reference code but now emits an independent relation-
    event plan; reproduction remains on the CPU.
    """

    def __init__(self, cfg: SimulationConfig, planner: GpuHarvestPlanner | None = None) -> None:
        super().__init__(cfg)
        self._planner = planner

    def bind_harvest_planner(self, planner: GpuHarvestPlanner) -> None:
        """Bind this portable resolver to the runtime of one simulation branch."""
        self._planner = planner

    def __deepcopy__(self, memo: dict[int, Any]) -> "GpuActionConflictResolver":
        """Do not copy a device runtime into a cloned simulation branch.

        :class:`Simulation` binds the clone to the branch's freshly-created
        runtime.  This preserves independent device field mirrors for
        counterfactual runs.
        """
        clone = type(self)(self.cfg)
        memo[id(self)] = clone
        return clone

    def _resolve_harvest(
        self,
        snapshot: ActionResolutionSnapshot,
        intents: ActionIntentBatch,
        harvest_allocator: HarvestAllocator,
    ) -> HarvestResolution:
        del harvest_allocator  # Allocation is part of the device plan boundary.
        if self._planner is None:
            raise RuntimeError(
                "GpuActionConflictResolver is not bound to a GPU harvest planner; "
                "create it through Simulation(..., backend='gpu') or bind one explicitly."
            )
        return self._planner.resolve_harvest_plan(snapshot, intents)


__all__ = [
    "ActionConflictResolver",
    "ActionResolutionPlan",
    "ActionResolutionSnapshot",
    "DeterministicActionConflictResolver",
    "GpuActionConflictResolver",
    "GpuHarvestPlanner",
    "HarvestAllocator",
    "HarvestResolution",
    "order_reproduction_candidates",
    "ShareResolution",
]
