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

from .config import SimulationConfig
from .intents import ActionIntentBatch, ActionResolutionBatch, FailureReason, action_rows, empty_resolutions
from .policy import Action


# The strict CPU allocator accepts NumPy arrays while a device planner keeps
# its temporary keys on its selected backend.  The plan itself is always a
# host-side, auditable value consumed by the world-commit phase.
HarvestAllocator = Callable[[Any, Any], Any]


@dataclass(frozen=True)
class ActionResolutionSnapshot:
    """The minimal immutable world view required for intent arbitration."""

    active: np.ndarray
    cells: np.ndarray
    entity_id: np.ndarray
    alive: np.ndarray
    energy: np.ndarray
    fertility: np.ndarray
    free_slot_count: int


@dataclass(frozen=True)
class ActionResolutionPlan:
    """Resolved effects, still separated from all world mutation."""

    resolutions: ActionResolutionBatch
    harvest_rows: np.ndarray
    harvest_cells: np.ndarray
    gathered: np.ndarray
    share_rows: np.ndarray
    share_targets: np.ndarray
    shared: np.ndarray
    signal_rows: np.ndarray
    accepted_reproduce_rows: np.ndarray


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

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg

    def _resolve_shares(
        self,
        snapshot: ActionResolutionSnapshot,
        intents: ActionIntentBatch,
        resolutions: ActionResolutionBatch,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        rows = action_rows(intents, Action.SHARE)
        if rows.size == 0:
            return rows, np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32)
        owners = intents.carrier_index[rows]
        targets = intents.target_index[rows]
        valid = (targets >= 0) & snapshot.alive[targets]
        safe_targets = np.where(valid, targets, 0)
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
        if not np.any(proposed > 0):
            resolutions.success[rows] = False
            resolutions.failure_reason[rows] = np.where(
                valid, FailureReason.INSUFFICIENT_RESOURCE, FailureReason.INVALID_TARGET
            )
            return rows, targets, proposed
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
        resolutions.failure_reason[rows[~success]] = FailureReason.INSUFFICIENT_CAPACITY
        resolutions.resource_delta[rows, 0] = -actual
        return rows, safe_targets, actual

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
            )
        observation_rows = np.searchsorted(snapshot.active, intents.carrier_index[harvest_rows])
        harvest_cells = snapshot.cells[observation_rows]
        order = np.lexsort((intents.carrier_id[harvest_rows], harvest_cells))
        harvest_rows = harvest_rows[order]
        harvest_cells = harvest_cells[order]
        base = self.cfg.entities.harvest_rate
        rates = np.tile(
            np.asarray([base, base * 0.45, base * 0.25, base * 0.18], dtype=np.float32),
            (harvest_rows.size, 1),
        )
        gathered = np.asarray(harvest_allocator(harvest_cells, rates), dtype=np.float32)
        return HarvestResolution(harvest_rows, harvest_cells, gathered)

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
            harvested = gathered[:, 0] > 1e-8
            resolutions.success[harvest_rows] = harvested
            resolutions.failure_reason[harvest_rows[~harvested]] = FailureReason.INSUFFICIENT_RESOURCE

        share_rows, share_targets, shared = self._resolve_shares(snapshot, intents, resolutions)

        signal_rows = action_rows(intents, Action.SIGNAL)
        if signal_rows.size:
            resolutions.energy_cost[signal_rows] = self.cfg.entities.signal_cost

        reproduce_rows = action_rows(intents, Action.REPRODUCE)
        accepted_reproduce_rows = np.empty(0, dtype=np.int32)
        if reproduce_rows.size:
            parents = intents.carrier_index[reproduce_rows]
            valid_parent = (
                snapshot.energy[parents] >= self.cfg.entities.reproduction_threshold
            ) & (snapshot.fertility[parents] >= 0.5)
            invalid_rows = reproduce_rows[~valid_parent]
            resolutions.success[invalid_rows] = False
            resolutions.failure_reason[invalid_rows] = FailureReason.INSUFFICIENT_RESOURCE
            candidates = reproduce_rows[valid_parent]
            candidates = candidates[np.argsort(intents.carrier_id[candidates], kind="stable")]
            accepted_reproduce_rows = candidates[: snapshot.free_slot_count]
            rejected = candidates[snapshot.free_slot_count :]
            resolutions.success[rejected] = False
            resolutions.failure_reason[rejected] = FailureReason.INSUFFICIENT_CAPACITY
            resolutions.energy_cost[accepted_reproduce_rows] = self.cfg.entities.reproduction_cost

        return ActionResolutionPlan(
            resolutions=resolutions,
            harvest_rows=harvest_rows,
            harvest_cells=harvest_cells,
            gathered=gathered,
            share_rows=share_rows,
            share_targets=share_targets,
            shared=shared,
            signal_rows=signal_rows,
            accepted_reproduce_rows=accepted_reproduce_rows,
        )


class GpuActionConflictResolver(DeterministicActionConflictResolver):
    """Device-backed harvest planning with the reference CPU commit contract.

    Only the harvest subset is delegated.  Movement is deliberately left as
    a successful intent in the common resolution batch because it has no
    contested shared state in the present model; its actual position change
    remains in the single world-commit phase.  Shares and reproduction reuse
    the strict reference code until their independent event plans exist.
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
]
