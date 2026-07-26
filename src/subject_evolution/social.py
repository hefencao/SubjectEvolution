from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import numpy as np

from .config import SimulationConfig


GROUP_LABEL_SCHEMA = "trusted-directed-fixed-round-min-label-v1"


def _readonly_view(value: np.ndarray) -> np.ndarray:
    """Return a zero-copy array view that rejects planner-side mutation."""
    result = value.view()
    result.flags.writeable = False
    return result


@dataclass
class GroupSummary:
    group_ids: np.ndarray
    counts: np.ndarray
    mean_energy: np.ndarray


@dataclass(frozen=True)
class GroupDetectionSnapshot:
    """Read-only inputs for one backend-neutral group-labeling pass.

    The relation table remains a fixed-slot SoA at this boundary.  A future
    device or distributed planner can consume the same value without gaining
    write access to ``SocialSystem`` or the candidate-subject graph.
    """

    active_indices: np.ndarray
    active_entity_ids: np.ndarray
    alive: np.ndarray
    stable_ids: np.ndarray
    energy: np.ndarray
    relation_targets: np.ndarray
    relation_trust: np.ndarray
    resource_grad_x: np.ndarray
    resource_grad_y: np.ndarray
    trust_threshold: float
    min_members: int
    label_schema: str
    propagation_rounds: int
    tick: int


@dataclass(frozen=True)
class GroupLabelPlan:
    """Canonical labels, group aggregates, and segmented group membership."""

    active_indices: np.ndarray
    active_entity_ids: np.ndarray
    entity_group_ids: np.ndarray
    group_tokens: np.ndarray
    member_starts: np.ndarray
    member_counts: np.ndarray
    member_indices: np.ndarray
    group_direction_x: np.ndarray
    group_direction_y: np.ndarray
    mean_energy: np.ndarray
    tick: int

    @property
    def group_count(self) -> int:
        return int(self.group_tokens.size)

    @property
    def member_count(self) -> int:
        return int(self.member_indices.size)


def ungrouped_group_label_plan(
    active_indices: np.ndarray,
    active_entity_ids: np.ndarray,
    tick: int,
) -> GroupLabelPlan:
    """Return a canonical plan that clears group assignment for active rows."""
    active = np.asarray(active_indices, dtype=np.int32)
    entity_ids = np.asarray(active_entity_ids, dtype=np.uint64)
    if active.ndim != 1 or entity_ids.ndim != 1 or active.size != entity_ids.size:
        raise ValueError("ungrouped plan identity arrays must be aligned and one-dimensional")
    return GroupLabelPlan(
        active_indices=active.copy(),
        active_entity_ids=entity_ids.copy(),
        entity_group_ids=np.zeros(active.size, dtype=np.uint64),
        group_tokens=np.empty(0, dtype=np.uint64),
        member_starts=np.empty(0, dtype=np.int64),
        member_counts=np.empty(0, dtype=np.int32),
        member_indices=np.empty(0, dtype=np.int32),
        group_direction_x=np.empty(0, dtype=np.float32),
        group_direction_y=np.empty(0, dtype=np.float32),
        mean_energy=np.empty(0, dtype=np.float32),
        tick=int(tick),
    )


class GroupLabelPlanner(Protocol):
    """Backend-independent group planner contract."""

    def plan(self, snapshot: GroupDetectionSnapshot) -> GroupLabelPlan:
        ...


class DeterministicGroupLabelPlanner:
    """Reference CPU planner preserving the original label propagation rule."""

    scientific_safe = True

    def plan(self, snapshot: GroupDetectionSnapshot) -> GroupLabelPlan:
        active = np.asarray(snapshot.active_indices, dtype=np.int32)
        active_ids = np.asarray(snapshot.active_entity_ids, dtype=np.uint64)
        alive = np.asarray(snapshot.alive, dtype=bool)
        stable_ids = np.asarray(snapshot.stable_ids, dtype=np.uint64)
        energy = np.asarray(snapshot.energy, dtype=np.float32)
        targets = np.asarray(snapshot.relation_targets, dtype=np.int32)
        trust = np.asarray(snapshot.relation_trust, dtype=np.float32)
        grad_x = np.asarray(snapshot.resource_grad_x, dtype=np.float32)
        grad_y = np.asarray(snapshot.resource_grad_y, dtype=np.float32)
        if any(
            value.ndim != 1
            for value in (active, active_ids, alive, stable_ids, energy, grad_x, grad_y)
        ):
            raise ValueError("group detection vectors must be one-dimensional")
        capacity = alive.size
        if any(value.size != capacity for value in (stable_ids, energy, grad_x, grad_y)):
            raise ValueError("group detection world vectors must share one capacity")
        if targets.ndim != 2 or trust.shape != targets.shape or targets.shape[0] != capacity:
            raise ValueError("group detection relation arrays must have aligned fixed-slot shapes")
        if np.any(targets < -1) or np.any(targets >= capacity):
            raise ValueError("group detection relation targets are out of range")
        if active.size != active_ids.size or not np.array_equal(active, np.flatnonzero(alive)):
            raise ValueError("group detection active rows do not match occupancy")
        if not np.array_equal(stable_ids[active], active_ids):
            raise ValueError("group detection active entity IDs are stale")
        if str(snapshot.label_schema) != GROUP_LABEL_SCHEMA:
            raise ValueError(f"unsupported group label schema {snapshot.label_schema!r}")
        if int(snapshot.min_members) <= 0 or int(snapshot.propagation_rounds) < 0:
            raise ValueError("group detection parameters are invalid")
        if active.size == 0:
            return ungrouped_group_label_plan(active, active_ids, snapshot.tick)

        labels = np.arange(capacity, dtype=np.int32)
        trusted = (targets >= 0) & (trust >= np.float32(snapshot.trust_threshold))
        # Fixed-round minimum-label propagation is deliberately kept as the
        # reference semantic.  Alternative planners must emit the same plan
        # contract, while approximate algorithms can be configured explicitly.
        for _ in range(int(snapshot.propagation_rounds)):
            new_labels = labels.copy()
            for slot in range(targets.shape[1]):
                target = targets[:, slot]
                valid = trusted[:, slot] & alive & (target >= 0)
                safe_target = np.where(valid, target, 0)
                candidate = labels[safe_target]
                new_labels = np.where(valid, np.minimum(new_labels, candidate), new_labels)
            labels = new_labels

        roots = labels[active]
        unique_roots, inverse, counts = np.unique(roots, return_inverse=True, return_counts=True)
        valid_group = counts >= int(snapshot.min_members)
        root_to_group = np.zeros(unique_roots.size, dtype=np.uint64)
        root_to_group[valid_group] = stable_ids[unique_roots[valid_group]]
        entity_groups = root_to_group[inverse]
        valid_members = entity_groups != 0
        if not np.any(valid_members):
            empty = ungrouped_group_label_plan(active, active_ids, snapshot.tick)
            return GroupLabelPlan(
                active_indices=empty.active_indices,
                active_entity_ids=empty.active_entity_ids,
                entity_group_ids=entity_groups,
                group_tokens=empty.group_tokens,
                member_starts=empty.member_starts,
                member_counts=empty.member_counts,
                member_indices=empty.member_indices,
                group_direction_x=empty.group_direction_x,
                group_direction_y=empty.group_direction_y,
                mean_energy=empty.mean_energy,
                tick=empty.tick,
            )

        group_tokens, group_inverse = np.unique(
            entity_groups[valid_members], return_inverse=True
        )
        members_active_order = active[valid_members]
        member_counts = np.bincount(group_inverse, minlength=group_tokens.size).astype(np.int32)
        sums_x = np.bincount(
            group_inverse, weights=grad_x[members_active_order], minlength=group_tokens.size
        )
        sums_y = np.bincount(
            group_inverse, weights=grad_y[members_active_order], minlength=group_tokens.size
        )
        dx = sums_x / np.maximum(member_counts, 1)
        dy = sums_y / np.maximum(member_counts, 1)
        norm = np.maximum(np.hypot(dx, dy), 1e-6)
        dx /= norm
        dy /= norm
        mean_energy = np.bincount(
            group_inverse, weights=energy[members_active_order], minlength=group_tokens.size
        ) / np.maximum(member_counts, 1)

        # One stable grouping pass gives downstream graph commit direct slices
        # instead of forcing one full active-row scan per observed group.
        member_order = np.argsort(group_inverse, kind="stable")
        member_indices = members_active_order[member_order]
        member_starts = np.empty(group_tokens.size, dtype=np.int64)
        member_starts[0] = 0
        if group_tokens.size > 1:
            np.cumsum(member_counts[:-1], out=member_starts[1:])
        return GroupLabelPlan(
            active_indices=active.copy(),
            active_entity_ids=active_ids.copy(),
            entity_group_ids=entity_groups.astype(np.uint64, copy=False),
            group_tokens=group_tokens.astype(np.uint64, copy=False),
            member_starts=member_starts,
            member_counts=member_counts,
            member_indices=member_indices.astype(np.int32, copy=False),
            group_direction_x=dx.astype(np.float32),
            group_direction_y=dy.astype(np.float32),
            mean_energy=mean_energy.astype(np.float32),
            tick=int(snapshot.tick),
        )


@dataclass(frozen=True)
class RelationUpdatePlan:
    """Canonical, replayable relation events produced before world commit.

    Events are ordered by ``(owner_index, event_sequence)``.  ``source_rows``
    preserves the originating action-intent row and ``reciprocal`` marks the
    successful target-to-owner acknowledgement generated by a share.  The
    fixed-slot relation store is deliberately absent from this value, so CPU,
    GPU, distributed, and replay planners can share the same event boundary.
    """

    owner_indices: np.ndarray
    target_indices: np.ndarray
    trust_delta: np.ndarray
    familiarity_delta: np.ndarray
    source_rows: np.ndarray
    event_sequence: np.ndarray
    reciprocal: np.ndarray
    tick: int

    @property
    def size(self) -> int:
        return int(self.owner_indices.size)


def empty_relation_update_plan(tick: int) -> RelationUpdatePlan:
    """Return an empty plan with the canonical event dtypes."""
    return RelationUpdatePlan(
        owner_indices=np.empty(0, dtype=np.int32),
        target_indices=np.empty(0, dtype=np.int32),
        trust_delta=np.empty(0, dtype=np.float32),
        familiarity_delta=np.empty(0, dtype=np.float32),
        source_rows=np.empty(0, dtype=np.int32),
        event_sequence=np.empty(0, dtype=np.int64),
        reciprocal=np.empty(0, dtype=bool),
        tick=int(tick),
    )


def build_share_relation_update_plan(
    cfg: SimulationConfig,
    rows: np.ndarray,
    owners: np.ndarray,
    targets: np.ndarray,
    success: np.ndarray,
    eligible: np.ndarray,
    tick: int,
) -> RelationUpdatePlan:
    """Expand resolved shares into canonical forward/reciprocal events.

    Failed shares update trust only when the target was a valid interaction
    partner.  Invalid, dead, out-of-range, or self targets produce no relation
    event.  Successful shares additionally emit a reciprocal half-gain event.
    """
    row_values = np.asarray(rows, dtype=np.int32)
    owner_values = np.asarray(owners, dtype=np.int32)
    target_values = np.asarray(targets, dtype=np.int32)
    success_values = np.asarray(success, dtype=bool)
    eligible_values = np.asarray(eligible, dtype=bool)
    arrays = (row_values, owner_values, target_values, success_values, eligible_values)
    if any(value.ndim != 1 for value in arrays):
        raise ValueError("share relation inputs must be one-dimensional")
    if len({value.size for value in arrays}) != 1:
        raise ValueError("share relation inputs must have the same length")
    if row_values.size == 0:
        return empty_relation_update_plan(tick)

    eligible_positions = np.flatnonzero(eligible_values)
    successful_positions = np.flatnonzero(eligible_values & success_values)
    if eligible_positions.size == 0:
        return empty_relation_update_plan(tick)

    gain = np.float32(cfg.social.trust_gain_share)
    loss = np.float32(cfg.social.trust_loss_failed)
    base_sequence = np.arange(row_values.size, dtype=np.int64) * 2
    forward_delta = np.where(success_values[eligible_positions], gain, -loss).astype(np.float32)
    owner_indices = np.concatenate(
        (owner_values[eligible_positions], target_values[successful_positions])
    )
    target_indices = np.concatenate(
        (target_values[eligible_positions], owner_values[successful_positions])
    )
    trust_delta = np.concatenate(
        (
            forward_delta,
            np.full(successful_positions.size, gain * np.float32(0.5), dtype=np.float32),
        )
    )
    familiarity_delta = np.full(owner_indices.size, 0.05, dtype=np.float32)
    source_rows = np.concatenate(
        (row_values[eligible_positions], row_values[successful_positions])
    )
    event_sequence = np.concatenate(
        (base_sequence[eligible_positions], base_sequence[successful_positions] + 1)
    )
    reciprocal = np.concatenate(
        (
            np.zeros(eligible_positions.size, dtype=bool),
            np.ones(successful_positions.size, dtype=bool),
        )
    )
    order = np.lexsort((event_sequence, owner_indices))
    return RelationUpdatePlan(
        owner_indices=owner_indices[order].astype(np.int32, copy=False),
        target_indices=target_indices[order].astype(np.int32, copy=False),
        trust_delta=trust_delta[order].astype(np.float32, copy=False),
        familiarity_delta=familiarity_delta[order],
        source_rows=source_rows[order].astype(np.int32, copy=False),
        event_sequence=event_sequence[order],
        reciprocal=reciprocal[order],
        tick=int(tick),
    )


class SocialSystem:
    """Fixed-capacity relationships plus approximate connected-group detection."""

    _UNTRACKED_DECAY_TICK = np.iinfo(np.int64).min

    def __init__(self, cfg: SimulationConfig, capacity: int) -> None:
        self.cfg = cfg
        k = cfg.entities.relation_slots
        self.target = np.full((capacity, k), -1, dtype=np.int32)
        self.trust = np.zeros((capacity, k), dtype=np.float32)
        self.familiarity = np.zeros((capacity, k), dtype=np.float32)
        self.last_interaction = np.zeros((capacity, k), dtype=np.uint32)
        # Relationship values are materialized only at the rows that consume
        # them (share updates or group detection).  The stored tick is the
        # last inclusive end-of-tick decay applied to that slot.  The sentinel
        # keeps externally seeded relationship fixtures backward-compatible:
        # they begin to track decay when first updated by the simulation.
        self.last_decay_tick = np.full(
            (capacity, k), self._UNTRACKED_DECAY_TICK, dtype=np.int64
        )
        self.group_id = np.zeros(capacity, dtype=np.uint64)
        self.group_age = np.zeros(capacity, dtype=np.uint32)
        self.group_dir_x = np.zeros(capacity, dtype=np.float32)
        self.group_dir_y = np.zeros(capacity, dtype=np.float32)
        self.group_labels_dirty = True
        self.last_group_update_tick = -1
        self.next_group_decay_due_tick = np.iinfo(np.int64).max
        self.group_update_count = 0
        self.group_update_skipped_count = 0
        self.last_group_update_reason = "initial"
        self.last_group_dirty_reason = "initial"

    def _mark_group_labels_dirty(self, reason: str) -> None:
        self.group_labels_dirty = True
        self.last_group_dirty_reason = str(reason)

    def mark_group_labels_dirty(self, reason: str) -> None:
        self._mark_group_labels_dirty(reason)

    def reset_entities(self, indices: np.ndarray) -> None:
        if indices.size == 0:
            return
        had_group_or_relation = bool(
            np.any(self.group_id[indices] != 0)
            or np.any(self.target[indices] >= 0)
        )
        self.target[indices] = -1
        self.trust[indices] = 0.0
        self.familiarity[indices] = 0.0
        self.last_interaction[indices] = 0
        self.last_decay_tick[indices] = self._UNTRACKED_DECAY_TICK
        self.group_id[indices] = 0
        self.group_age[indices] = 0
        self.group_dir_x[indices] = 0.0
        self.group_dir_y[indices] = 0.0
        if had_group_or_relation:
            self._mark_group_labels_dirty("lifecycle-reset")

    def _materialize_decay(
        self,
        rows: np.ndarray,
        through_tick: int,
        *,
        assume_unique: bool = False,
    ) -> None:
        """Apply deferred geometric decay through an inclusive tick boundary."""
        owner_rows = np.asarray(rows, dtype=np.int32)
        if owner_rows.size == 0:
            return
        if not assume_unique:
            owner_rows = np.unique(owner_rows)
        last = self.last_decay_tick[owner_rows]
        tracked = last != self._UNTRACKED_DECAY_TICK
        if not np.any(tracked):
            return
        elapsed = np.maximum(int(through_tick) - last, 0)
        apply = tracked & (elapsed > 0)
        if np.any(apply):
            factor = np.float32(max(0.0, 1.0 - self.cfg.social.relation_decay))
            decay = np.ones(last.shape, dtype=np.float32)
            decay[apply] = np.power(factor, elapsed[apply], dtype=np.float32)
            self.trust[owner_rows] *= decay
            self.familiarity[owner_rows] *= decay
        last[tracked] = int(through_tick)
        self.last_decay_tick[owner_rows] = last

    def decay(self, alive: np.ndarray) -> None:
        """Eager compatibility operation for callers outside the main loop.

        The simulation uses :meth:`_materialize_decay` at read/write
        boundaries instead, avoiding full relation-table passes on ticks with
        no social interaction or group recomputation.
        """
        factor = max(0.0, 1.0 - self.cfg.social.relation_decay)
        self.trust[alive] *= factor
        self.familiarity[alive] *= factor

    def _update_one(self, owner: int, target: int, trust_delta: float, tick: int) -> None:
        if owner < 0 or target < 0 or owner == target:
            return
        row_targets = self.target[owner]
        existing = np.flatnonzero(row_targets == target)
        if existing.size:
            slot = int(existing[0])
        else:
            empty = np.flatnonzero(row_targets < 0)
            if empty.size:
                slot = int(empty[0])
            else:
                # Keep important and recent ties; replace the weakest effective slot.
                score = self.trust[owner] + 0.25 * self.familiarity[owner]
                slot = int(np.argmin(score))
            self.target[owner, slot] = target
            self.trust[owner, slot] = 0.0
            self.familiarity[owner, slot] = 0.0
        self.trust[owner, slot] = np.clip(self.trust[owner, slot] + trust_delta, 0.0, 1.0)
        self.familiarity[owner, slot] = np.clip(self.familiarity[owner, slot] + 0.05, 0.0, 1.0)
        self.last_interaction[owner, slot] = tick

    def _update_unique_owners(
        self,
        owners: np.ndarray,
        targets: np.ndarray,
        trust_delta: np.ndarray,
        familiarity_delta: np.ndarray,
        tick: int,
    ) -> None:
        """Apply one event for each distinct owner in a vectorized batch."""
        if owners.size == 0:
            return
        row_targets = self.target[owners]
        existing_matches = row_targets == targets[:, None]
        existing = existing_matches.any(axis=1)
        existing_slot = existing_matches.argmax(axis=1)
        empty = row_targets < 0
        has_empty = empty.any(axis=1)
        empty_slot = empty.argmax(axis=1)
        slots = np.where(existing, existing_slot, empty_slot).astype(np.int32)
        needs_replacement = ~existing & ~has_empty
        if np.any(needs_replacement):
            replacement_owners = owners[needs_replacement]
            slots[needs_replacement] = (
                self.trust[replacement_owners]
                + np.float32(0.25) * self.familiarity[replacement_owners]
            ).argmin(axis=1)
        new_relation = ~existing
        if np.any(new_relation):
            inserted_owners = owners[new_relation]
            inserted_slots = slots[new_relation]
            self.target[inserted_owners, inserted_slots] = targets[new_relation]
            self.trust[inserted_owners, inserted_slots] = 0.0
            self.familiarity[inserted_owners, inserted_slots] = 0.0
        self.trust[owners, slots] = np.clip(self.trust[owners, slots] + trust_delta, 0.0, 1.0)
        self.familiarity[owners, slots] = np.clip(
            self.familiarity[owners, slots] + familiarity_delta, 0.0, 1.0
        )
        self.last_interaction[owners, slots] = tick
        # This relation has just been updated before the end-of-tick decay.
        # At a later consumer boundary, ``tick - 1`` therefore denotes the
        # last decay already reflected in its stored value.
        self.last_decay_tick[owners, slots] = int(tick) - 1

    def apply_relation_updates(self, plan: RelationUpdatePlan) -> None:
        """Apply one canonical event plan in owner-local stable order.

        Relation rows are independent: reordering updates for different
        owners cannot affect the result, while updates to one owner must keep
        their original event sequence because a full row may replace its
        weakest slot.  Events are therefore processed in owner-local rank
        order, with each rank forming a vectorized batch of distinct owners.
        """
        owner_values = np.asarray(plan.owner_indices, dtype=np.int32)
        target_values = np.asarray(plan.target_indices, dtype=np.int32)
        trust_delta = np.asarray(plan.trust_delta, dtype=np.float32)
        familiarity_delta = np.asarray(plan.familiarity_delta, dtype=np.float32)
        source_rows = np.asarray(plan.source_rows, dtype=np.int32)
        event_sequence = np.asarray(plan.event_sequence, dtype=np.int64)
        reciprocal = np.asarray(plan.reciprocal, dtype=bool)
        arrays = (
            owner_values,
            target_values,
            trust_delta,
            familiarity_delta,
            source_rows,
            event_sequence,
            reciprocal,
        )
        if any(value.ndim != 1 for value in arrays):
            raise ValueError("relation update plan arrays must be one-dimensional")
        if len({value.size for value in arrays}) != 1:
            raise ValueError("relation update plan arrays must have the same length")
        if owner_values.size == 0:
            return
        if int(plan.tick) < 0:
            raise ValueError("relation update plan tick must be non-negative")
        capacity = self.target.shape[0]
        if (
            np.any(owner_values < 0)
            or np.any(owner_values >= capacity)
            or np.any(target_values < 0)
            or np.any(target_values >= capacity)
            or np.any(owner_values == target_values)
        ):
            raise ValueError("relation update plan contains an invalid owner/target pair")
        if np.any(source_rows < 0) or np.any(event_sequence < 0):
            raise ValueError("relation update plan contains invalid provenance")
        if not np.all(np.isfinite(trust_delta)) or not np.all(np.isfinite(familiarity_delta)):
            raise ValueError("relation update plan deltas must be finite")
        owner_ordered = owner_values[1:] >= owner_values[:-1]
        sequence_ordered = (owner_values[1:] != owner_values[:-1]) | (
            event_sequence[1:] >= event_sequence[:-1]
        )
        if not np.all(owner_ordered & sequence_ordered):
            raise ValueError("relation update plan must be ordered by owner and event sequence")

        # A relationship may be untouched for many ticks.  Materialize only
        # the owner rows that are about to compare, replace, or update slots;
        # their effective values then exactly match the eager schedule at the
        # start of this tick.
        starts = np.concatenate(
            (
                np.asarray([0], dtype=np.int64),
                np.flatnonzero(owner_values[1:] != owner_values[:-1]).astype(np.int64) + 1,
            )
        )
        counts = np.diff(
            np.concatenate((starts, np.asarray([owner_values.size], dtype=np.int64)))
        )
        unique_owners = owner_values[starts]
        self._materialize_decay(
            unique_owners,
            int(plan.tick) - 1,
            assume_unique=True,
        )
        threshold = np.float32(self.cfg.social.trust_group_threshold)
        topology_before = np.where(
            self.trust[unique_owners] >= threshold,
            self.target[unique_owners],
            -1,
        )
        # Each pass contains exactly one event per owner.  Processing the
        # passes in rank order retains the scalar replacement semantics even
        # when several events target one owner in the same tick.
        for event_rank in range(int(counts.max())):
            active_owners = counts > event_rank
            positions = starts[active_owners] + event_rank
            self._update_unique_owners(
                owner_values[positions],
                target_values[positions],
                trust_delta[positions],
                familiarity_delta[positions],
                int(plan.tick),
            )

    def record_shares(self, owners: np.ndarray, targets: np.ndarray, success: np.ndarray, tick: int) -> None:
        """Backward-compatible share-event convenience wrapper."""
        owner_values = np.asarray(owners, dtype=np.int32)
        target_values = np.asarray(targets, dtype=np.int32)
        success_values = np.asarray(success, dtype=bool)
        plan = build_share_relation_update_plan(
            self.cfg,
            rows=np.arange(owner_values.size, dtype=np.int32),
            owners=owner_values,
            targets=target_values,
            success=success_values,
            eligible=(owner_values >= 0) & (target_values >= 0) & (owner_values != target_values),
            tick=tick,
        )
        self.apply_relation_updates(plan)

    def clear_dead_targets(self, alive: np.ndarray) -> None:
        valid_target = self.target >= 0
        dead_link = valid_target & ~alive[np.where(valid_target, self.target, 0)]
        if np.any(dead_link):
            self.target[dead_link] = -1
            self.trust[dead_link] = 0.0
            self.familiarity[dead_link] = 0.0
            self.last_decay_tick[dead_link] = self._UNTRACKED_DECAY_TICK
            self._mark_group_labels_dirty("dead-relation-target")

    def _predict_next_decay_crossing_tick(self, tick: int) -> int:
        threshold = float(self.cfg.social.trust_group_threshold)
        factor = float(max(0.0, 1.0 - self.cfg.social.relation_decay))
        valid = (self.target >= 0) & (self.trust >= np.float32(threshold))
        if not np.any(valid) or factor >= 1.0:
            return int(np.iinfo(np.int64).max)
        if factor <= 0.0:
            return int(tick) + 1
        values = self.trust[valid].astype(np.float64)
        # First integer n >= 1 for which value * factor**n < threshold.
        ratio = np.maximum(threshold / np.maximum(values, 1e-30), 1e-30)
        crossing = np.floor(np.log(ratio) / np.log(factor)).astype(np.int64) + 1
        crossing = np.maximum(crossing, 1)
        return int(tick) + int(crossing.min())

    def group_update_due(self, tick: int) -> tuple[bool, str]:
        cfg = self.cfg.social
        if cfg.group_update_mode == "periodic-v1":
            due = int(tick) % int(cfg.group_update_period) == 0
            return due, ("periodic" if due else "periodic-skip")
        if self.last_group_update_tick < 0:
            return True, "initial"
        elapsed = int(tick) - int(self.last_group_update_tick)
        min_period = int(cfg.group_update_min_period)
        # Adaptive refresh is intentionally rate-limited.  Topology changes and
        # predicted trust-threshold crossings make a refresh eligible, but do
        # not bypass the configured minimum period.  This preserves the goal
        # of avoiding frequent label churn while still bounding staleness.
        if elapsed < min_period:
            return False, "adaptive-skip"
        if self.group_labels_dirty:
            return True, "topology-dirty"
        if int(tick) >= int(self.next_group_decay_due_tick):
            return True, "trust-decay-threshold"
        max_period = int(cfg.group_update_max_period)
        if max_period > 0 and elapsed >= max_period:
            return True, "max-staleness"
        return False, "adaptive-skip"

    def note_group_update_skipped(self) -> None:
        self.group_update_skipped_count += 1

    def update_groups(
        self,
        alive: np.ndarray,
        stable_ids: np.ndarray,
        energy: np.ndarray,
        resource_grad_x: np.ndarray,
        resource_grad_y: np.ndarray,
        tick: int,
    ) -> GroupSummary:
        """Backward-compatible snapshot/plan/commit convenience wrapper."""
        snapshot = self.group_detection_snapshot(
            alive,
            stable_ids,
            energy,
            resource_grad_x,
            resource_grad_y,
            tick,
        )
        plan = DeterministicGroupLabelPlanner().plan(snapshot)
        return self.commit_group_plan(plan, alive, stable_ids)

    def group_detection_snapshot(
        self,
        alive: np.ndarray,
        stable_ids: np.ndarray,
        energy: np.ndarray,
        resource_grad_x: np.ndarray,
        resource_grad_y: np.ndarray,
        tick: int,
    ) -> GroupDetectionSnapshot:
        """Expose the complete read boundary for group-label planners."""
        alive_values = np.asarray(alive, dtype=bool)
        stable_id_values = np.asarray(stable_ids, dtype=np.uint64)
        energy_values = np.asarray(energy, dtype=np.float32)
        grad_x = np.asarray(resource_grad_x, dtype=np.float32)
        grad_y = np.asarray(resource_grad_y, dtype=np.float32)
        capacity = self.target.shape[0]
        if any(
            value.ndim != 1 or value.size != capacity
            for value in (alive_values, stable_id_values, energy_values, grad_x, grad_y)
        ):
            raise ValueError("group detection world vectors must match social capacity")
        active = np.flatnonzero(alive_values).astype(np.int32)
        # Group detection is a lower-frequency relationship consumer.  The
        # lazy decay write belongs to snapshot construction; the planner that
        # follows is pure and has no reference to SocialSystem.
        self._materialize_decay(active, tick, assume_unique=True)
        return GroupDetectionSnapshot(
            active_indices=_readonly_view(active),
            active_entity_ids=_readonly_view(stable_id_values[active].copy()),
            alive=_readonly_view(alive_values),
            stable_ids=_readonly_view(stable_id_values),
            energy=_readonly_view(energy_values),
            relation_targets=_readonly_view(self.target),
            relation_trust=_readonly_view(self.trust),
            resource_grad_x=_readonly_view(grad_x),
            resource_grad_y=_readonly_view(grad_y),
            trust_threshold=float(self.cfg.social.trust_group_threshold),
            min_members=int(self.cfg.social.group_min_members),
            label_schema=str(self.cfg.social.group_label_schema),
            propagation_rounds=int(self.cfg.social.group_label_propagation_rounds),
            tick=int(tick),
        )

    def commit_group_plan(
        self,
        plan: GroupLabelPlan,
        alive: np.ndarray,
        stable_ids: np.ndarray,
    ) -> GroupSummary:
        """Validate and commit one group plan against current world identity."""
        active = np.asarray(plan.active_indices, dtype=np.int32)
        active_ids = np.asarray(plan.active_entity_ids, dtype=np.uint64)
        entity_groups = np.asarray(plan.entity_group_ids, dtype=np.uint64)
        tokens = np.asarray(plan.group_tokens, dtype=np.uint64)
        starts = np.asarray(plan.member_starts, dtype=np.int64)
        counts = np.asarray(plan.member_counts, dtype=np.int32)
        members = np.asarray(plan.member_indices, dtype=np.int32)
        direction_x = np.asarray(plan.group_direction_x, dtype=np.float32)
        direction_y = np.asarray(plan.group_direction_y, dtype=np.float32)
        mean_energy = np.asarray(plan.mean_energy, dtype=np.float32)
        vectors = (
            active,
            active_ids,
            entity_groups,
            tokens,
            starts,
            counts,
            members,
            direction_x,
            direction_y,
            mean_energy,
        )
        if any(value.ndim != 1 for value in vectors):
            raise ValueError("group label plan arrays must be one-dimensional")
        if active.size != active_ids.size or active.size != entity_groups.size:
            raise ValueError("group label plan active arrays must be aligned")
        if any(value.size != tokens.size for value in (starts, counts, direction_x, direction_y, mean_energy)):
            raise ValueError("group label plan aggregate arrays must be aligned")
        current_alive = np.asarray(alive, dtype=bool)
        current_ids = np.asarray(stable_ids, dtype=np.uint64)
        capacity = self.group_id.size
        if current_alive.ndim != 1 or current_ids.ndim != 1 or current_alive.size != capacity or current_ids.size != capacity:
            raise ValueError("group commit world vectors must match social capacity")
        if not np.array_equal(active, np.flatnonzero(current_alive)):
            raise ValueError("group label plan occupancy is stale")
        if not np.array_equal(active_ids, current_ids[active]):
            raise ValueError("group label plan entity identity is stale")
        if tokens.size:
            if np.any(tokens == 0) or np.any(tokens[1:] <= tokens[:-1]):
                raise ValueError("group tokens must be nonzero and strictly ordered")
            expected_starts = np.empty(tokens.size, dtype=np.int64)
            expected_starts[0] = 0
            if tokens.size > 1:
                np.cumsum(counts[:-1], out=expected_starts[1:])
            if np.any(counts <= 0) or not np.array_equal(starts, expected_starts):
                raise ValueError("group membership segments are invalid")
        if int(counts.astype(np.int64).sum()) != members.size:
            raise ValueError("group membership segment sizes do not match members")
        if members.size:
            if np.any(members < 0) or np.any(members >= capacity) or np.unique(members).size != members.size:
                raise ValueError("group membership contains an invalid or duplicate slot")
            member_positions = np.searchsorted(active, members)
            if np.any(member_positions >= active.size) or not np.array_equal(active[member_positions], members):
                raise ValueError("group membership contains an inactive slot")
            expected_member_tokens = np.repeat(tokens, counts)
            if not np.array_equal(entity_groups[member_positions], expected_member_tokens):
                raise ValueError("group membership segments do not match entity labels")
            same_group = expected_member_tokens[1:] == expected_member_tokens[:-1]
            if np.any(same_group & (members[1:] <= members[:-1])):
                raise ValueError("group members must keep ascending slot order per segment")
        if np.count_nonzero(entity_groups) != members.size:
            raise ValueError("group plan labeled-member count is inconsistent")
        if tokens.size and not np.all(np.isin(entity_groups[entity_groups != 0], tokens)):
            raise ValueError("group plan contains an unknown group token")
        if int(plan.tick) < 0:
            raise ValueError("group label plan tick must be non-negative")
        if not np.all(np.isfinite(direction_x)) or not np.all(np.isfinite(direction_y)):
            raise ValueError("group directions must be finite")
        if not np.all(np.isfinite(mean_energy)):
            raise ValueError("group mean energy must be finite")

        if active.size == 0:
            self.group_id.fill(0)
            self.group_age.fill(0)
            self.group_dir_x.fill(0.0)
            self.group_dir_y.fill(0.0)
        else:
            old = self.group_id[active].copy()
            self.group_id[active] = entity_groups
            same = old == entity_groups
            self.group_age[active] = np.where(
                (entity_groups != 0) & same,
                self.group_age[active] + 1,
                np.where(entity_groups != 0, 1, 0),
            )
            self.group_dir_x[active] = 0.0
            self.group_dir_y[active] = 0.0
            if members.size:
                group_rows = np.repeat(np.arange(tokens.size, dtype=np.int32), counts)
                self.group_dir_x[members] = direction_x[group_rows]
                self.group_dir_y[members] = direction_y[group_rows]
        self.group_labels_dirty = False
        self.last_group_update_tick = int(plan.tick)
        self.next_group_decay_due_tick = self._predict_next_decay_crossing_tick(
            int(plan.tick)
        )
        self.group_update_count += 1
        return GroupSummary(tokens.copy(), counts.copy(), mean_energy.copy())
