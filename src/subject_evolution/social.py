from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .config import SimulationConfig


@dataclass
class GroupSummary:
    group_ids: np.ndarray
    counts: np.ndarray
    mean_energy: np.ndarray


class SocialSystem:
    """Fixed-capacity relationships plus approximate connected-group detection."""

    def __init__(self, cfg: SimulationConfig, capacity: int) -> None:
        self.cfg = cfg
        k = cfg.entities.relation_slots
        self.target = np.full((capacity, k), -1, dtype=np.int32)
        self.trust = np.zeros((capacity, k), dtype=np.float32)
        self.familiarity = np.zeros((capacity, k), dtype=np.float32)
        self.last_interaction = np.zeros((capacity, k), dtype=np.uint32)
        self.group_id = np.zeros(capacity, dtype=np.uint64)
        self.group_age = np.zeros(capacity, dtype=np.uint32)
        self.group_dir_x = np.zeros(capacity, dtype=np.float32)
        self.group_dir_y = np.zeros(capacity, dtype=np.float32)


    def reset_entities(self, indices: np.ndarray) -> None:
        if indices.size == 0:
            return
        self.target[indices] = -1
        self.trust[indices] = 0.0
        self.familiarity[indices] = 0.0
        self.last_interaction[indices] = 0
        self.group_id[indices] = 0
        self.group_age[indices] = 0
        self.group_dir_x[indices] = 0.0
        self.group_dir_y[indices] = 0.0

    def decay(self, alive: np.ndarray) -> None:
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
        weakest_slot = (self.trust[owners] + 0.25 * self.familiarity[owners]).argmin(axis=1)
        slots = np.where(existing, existing_slot, np.where(has_empty, empty_slot, weakest_slot)).astype(np.int32)
        new_relation = ~existing
        if np.any(new_relation):
            inserted_owners = owners[new_relation]
            inserted_slots = slots[new_relation]
            self.target[inserted_owners, inserted_slots] = targets[new_relation]
            self.trust[inserted_owners, inserted_slots] = 0.0
            self.familiarity[inserted_owners, inserted_slots] = 0.0
        self.trust[owners, slots] = np.clip(self.trust[owners, slots] + trust_delta, 0.0, 1.0)
        self.familiarity[owners, slots] = np.clip(self.familiarity[owners, slots] + 0.05, 0.0, 1.0)
        self.last_interaction[owners, slots] = tick

    def record_shares(self, owners: np.ndarray, targets: np.ndarray, success: np.ndarray, tick: int) -> None:
        """Apply share-derived relation events in owner-local stable order.

        Relation rows are independent: reordering updates for different
        owners cannot affect the result, while updates to one owner must keep
        their original event sequence because a full row may replace its
        weakest slot.  Events are therefore processed in owner-local rank
        order, with each rank forming a vectorized batch of distinct owners.
        """
        owner_values = np.asarray(owners, dtype=np.int32)
        target_values = np.asarray(targets, dtype=np.int32)
        success_values = np.asarray(success, dtype=bool)
        if owner_values.ndim != 1 or target_values.ndim != 1 or success_values.ndim != 1:
            raise ValueError("share relation events must be one-dimensional")
        if not (owner_values.size == target_values.size == success_values.size):
            raise ValueError("share relation event arrays must have the same length")
        if owner_values.size == 0:
            return

        gain = self.cfg.social.trust_gain_share
        loss = self.cfg.social.trust_loss_failed
        sequence = np.arange(owner_values.size, dtype=np.int64) * 2
        forward_delta = np.where(success_values, gain, -loss).astype(np.float64)
        successful = np.flatnonzero(success_values)
        event_owners = np.concatenate((owner_values, target_values[successful]))
        event_targets = np.concatenate((target_values, owner_values[successful]))
        event_delta = np.concatenate(
            (forward_delta, np.full(successful.size, gain * 0.5, dtype=np.float64))
        )
        event_sequence = np.concatenate((sequence, sequence[successful] + 1))
        valid = (event_owners >= 0) & (event_targets >= 0) & (event_owners != event_targets)
        if not np.any(valid):
            return
        event_owners = event_owners[valid]
        event_targets = event_targets[valid]
        event_delta = event_delta[valid]
        event_sequence = event_sequence[valid]

        order = np.lexsort((event_sequence, event_owners))
        event_owners = event_owners[order]
        event_targets = event_targets[order]
        event_delta = event_delta[order]
        _, starts, counts = np.unique(event_owners, return_index=True, return_counts=True)
        rank_within_owner = np.arange(event_owners.size, dtype=np.int32) - np.repeat(starts, counts)
        # Each pass contains exactly one event per owner.  Processing the
        # passes in rank order retains the scalar replacement semantics even
        # when several events target one owner in the same tick.
        for event_rank in range(int(counts.max())):
            positions = np.flatnonzero(rank_within_owner == event_rank)
            self._update_unique_owners(
                event_owners[positions],
                event_targets[positions],
                event_delta[positions],
                tick,
            )

    def clear_dead_targets(self, alive: np.ndarray) -> None:
        valid_target = self.target >= 0
        dead_link = valid_target & ~alive[np.where(valid_target, self.target, 0)]
        self.target[dead_link] = -1
        self.trust[dead_link] = 0.0
        self.familiarity[dead_link] = 0.0

    def update_groups(
        self,
        alive: np.ndarray,
        stable_ids: np.ndarray,
        energy: np.ndarray,
        resource_grad_x: np.ndarray,
        resource_grad_y: np.ndarray,
    ) -> GroupSummary:
        active = np.flatnonzero(alive).astype(np.int32)
        if active.size == 0:
            self.group_id.fill(0)
            return GroupSummary(np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32))

        labels = np.arange(alive.size, dtype=np.int32)
        trusted = (self.target >= 0) & (self.trust >= self.cfg.social.trust_group_threshold)
        # Label propagation is approximate but vectorizable and deterministic.
        for _ in range(8):
            new_labels = labels.copy()
            for slot in range(self.target.shape[1]):
                target = self.target[:, slot]
                valid = trusted[:, slot] & alive & (target >= 0)
                safe_target = np.where(valid, target, 0)
                candidate = labels[safe_target]
                new_labels = np.where(valid, np.minimum(new_labels, candidate), new_labels)
            labels = new_labels

        roots = labels[active]
        unique_roots, inverse, counts = np.unique(roots, return_inverse=True, return_counts=True)
        valid_group = counts >= self.cfg.social.group_min_members
        root_to_group = np.zeros(unique_roots.size, dtype=np.uint64)
        root_to_group[valid_group] = stable_ids[unique_roots[valid_group]]
        new_group = root_to_group[inverse]

        old = self.group_id[active].copy()
        self.group_id[active] = new_group
        same = old == new_group
        self.group_age[active] = np.where((new_group != 0) & same, self.group_age[active] + 1, np.where(new_group != 0, 1, 0))
        self.group_dir_x[active] = 0.0
        self.group_dir_y[active] = 0.0

        valid_members = new_group != 0
        if np.any(valid_members):
            group_values, group_inverse = np.unique(new_group[valid_members], return_inverse=True)
            member_indices = active[valid_members]
            sums_x = np.bincount(group_inverse, weights=resource_grad_x[member_indices], minlength=group_values.size)
            sums_y = np.bincount(group_inverse, weights=resource_grad_y[member_indices], minlength=group_values.size)
            member_counts = np.bincount(group_inverse, minlength=group_values.size)
            dx = sums_x / np.maximum(member_counts, 1)
            dy = sums_y / np.maximum(member_counts, 1)
            norm = np.maximum(np.hypot(dx, dy), 1e-6)
            dx /= norm
            dy /= norm
            self.group_dir_x[member_indices] = dx[group_inverse].astype(np.float32)
            self.group_dir_y[member_indices] = dy[group_inverse].astype(np.float32)
            mean_energy = np.bincount(group_inverse, weights=energy[member_indices], minlength=group_values.size) / np.maximum(member_counts, 1)
            return GroupSummary(group_values, member_counts.astype(np.int32), mean_energy.astype(np.float32))

        return GroupSummary(np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32))
