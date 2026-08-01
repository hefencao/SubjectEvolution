"""Capacity arbitration and commit for energy/raw-resource SHARE intents."""
from __future__ import annotations

import numpy as np

from ..cfg import SimulationConfig
from ..execution import ShareResolution
from ..intents import ActionResolutionBatch, FailureReason
from se.env.niches import RESOURCE_CHANNELS
from se.subjects.social import SocialSystem, build_share_relation_update_plan
from .resource_metabolism import resource_store_capacity_and_room
from .state import EntityState


def finalize_share_capacity(
    *,
    cfg: SimulationConfig,
    entities: EntityState,
    physiology_gene_start: int,
    neutralize_store_allocation: bool,
    tick: int,
    share: ShareResolution,
    resolutions: ActionResolutionBatch,
) -> ShareResolution:
    """Re-arbitrate receiver capacity after same-tick harvest settlement."""
    if share.rows.size == 0:
        return share
    proposed_energy = np.asarray(share.amounts, dtype=np.float32)
    proposed_raw = np.asarray(share.resource_amounts, dtype=np.float32)
    safe_targets = np.where(share.valid_target, share.target_indices, 0)

    total_by_target = np.bincount(
        safe_targets,
        weights=np.where(share.valid_target, proposed_energy, 0.0),
        minlength=entities.alive.size,
    ).astype(np.float32)
    energy_capacity = np.maximum(cfg.entities.max_energy - entities.energy, 0.0).astype(
        np.float32
    )
    energy_scale = np.ones(entities.alive.size, dtype=np.float32)
    occupied = total_by_target > 0.0
    energy_scale[occupied] = np.minimum(
        1.0, energy_capacity[occupied] / total_by_target[occupied]
    )
    actual_energy = proposed_energy * energy_scale[safe_targets]

    actual_raw = np.zeros_like(proposed_raw)
    if np.any(proposed_raw > 0.0):
        active = np.flatnonzero(entities.alive).astype(np.int32)
        capacity_active, _ = resource_store_capacity_and_room(
            entities,
            active,
            cfg,
            genotype=entities.genotype[active],
            gene_start=physiology_gene_start,
            neutralize_store_allocation=neutralize_store_allocation,
        )
        capacity = np.zeros_like(entities.resource_store, dtype=np.float64)
        capacity[active] = capacity_active
        stores = np.asarray(entities.resource_store, dtype=np.float64)
        reserve = float(cfg.social.resource_share_reserve_fraction) * capacity[
            share.owner_indices
        ]
        owner_available = np.maximum(stores[share.owner_indices] - reserve, 0.0)
        target_room = np.maximum(capacity[safe_targets] - stores[safe_targets], 0.0)
        bounded = np.minimum(
            proposed_raw.astype(np.float64), np.minimum(owner_available, target_room)
        )
        pair_totals = np.zeros(
            (entities.alive.size, RESOURCE_CHANNELS), dtype=np.float64
        )
        for channel in range(RESOURCE_CHANNELS):
            np.add.at(
                pair_totals[:, channel],
                safe_targets,
                np.where(share.valid_target, bounded[:, channel], 0.0),
            )
        pair_scale = np.ones_like(pair_totals)
        used = pair_totals > 0.0
        room_all = np.maximum(capacity - stores, 0.0)
        pair_scale[used] = np.minimum(1.0, room_all[used] / pair_totals[used])
        actual_raw = (bounded * pair_scale[safe_targets]).astype(np.float32)

    success = share.valid_target & (
        (actual_energy > 1.0e-8) | np.any(actual_raw > 1.0e-8, axis=1)
    )
    resolutions.success[share.rows] = success
    proposed_any = (proposed_energy > 1.0e-8) | np.any(proposed_raw > 1.0e-8, axis=1)
    capacity_failed = share.valid_target & proposed_any & ~success
    resolutions.failure_reason[share.rows[capacity_failed]] = (
        FailureReason.INSUFFICIENT_CAPACITY
    )
    resolutions.resource_delta[share.rows, 0] = -actual_energy
    resolutions.internal_resource_delta[share.rows] = -actual_raw
    relation_updates = build_share_relation_update_plan(
        cfg,
        share.rows,
        share.owner_indices,
        share.target_indices,
        success,
        share.valid_target,
        tick,
    )
    return ShareResolution(
        rows=share.rows,
        owner_indices=share.owner_indices,
        target_indices=share.target_indices,
        amounts=actual_energy.astype(np.float32, copy=False),
        resource_amounts=actual_raw.astype(np.float32, copy=False),
        success=success,
        valid_target=share.valid_target,
        relation_updates=relation_updates,
    )


def commit_shares(
    *,
    entities: EntityState,
    social: SocialSystem,
    social_connections_enabled: bool,
    share: ShareResolution,
) -> tuple[float, np.ndarray]:
    """Apply one capacity-resolved energy/raw share plan."""
    if share.rows.size == 0:
        if social_connections_enabled:
            social.settle_interest_feedback(int(share.relation_updates.tick))
        return 0.0, np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    committed_energy = share.success & share.valid_target & (share.amounts > 1.0e-8)
    if np.any(committed_energy):
        owners = share.owner_indices[committed_energy]
        targets = share.target_indices[committed_energy]
        amounts = share.amounts[committed_energy]
        np.add.at(entities.energy, owners, -amounts)
        np.add.at(entities.energy, targets, amounts)
        np.add.at(entities.shared_energy_received_total, targets, amounts)

    committed_raw = (
        share.success[:, None]
        & share.valid_target[:, None]
        & (share.resource_amounts > 1.0e-8)
    )
    raw_totals = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    if np.any(committed_raw):
        for channel in range(RESOURCE_CHANNELS):
            selected = committed_raw[:, channel]
            if not np.any(selected):
                continue
            owners = share.owner_indices[selected]
            targets = share.target_indices[selected]
            amounts = share.resource_amounts[selected, channel]
            np.add.at(entities.resource_store[:, channel], owners, -amounts)
            np.add.at(entities.resource_store[:, channel], targets, amounts)
            raw_totals[channel] = float(np.asarray(amounts, dtype=np.float64).sum())
        entities.resource_store[:] = np.maximum(entities.resource_store, 0.0)
    if social_connections_enabled:
        social.apply_relation_updates(share.relation_updates)
        social.record_material_interest_feedback(
            share.owner_indices,
            share.target_indices,
            share.amounts,
            share.resource_amounts,
            share.success & share.valid_target,
            int(share.relation_updates.tick),
        )
        social.settle_interest_feedback(int(share.relation_updates.tick))
    energy_total = float(
        np.asarray(share.amounts[committed_energy], dtype=np.float64).sum()
    )
    return energy_total, raw_totals


__all__ = ["commit_shares", "finalize_share_capacity"]
