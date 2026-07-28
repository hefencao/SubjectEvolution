"""Authoritative harvest commit isolated from the main simulation coordinator."""

from __future__ import annotations

from typing import Any

import numpy as np

from se.differentiation.physiology import resource_metabolism_enabled
from se.env.niches import apply_harvest_effects
from se.runtime.resource_metabolism import commit_assimilated_harvest


def commit_harvest_resolution(
    simulation: Any,
    intents: Any,
    resolution_plan: Any,
    effective_resource_affinity_q: np.ndarray | None,
    stats: Any,
) -> np.ndarray | None:
    """Commit one resolved harvest batch and return immediate body deltas, if any.

    Delayed resource-metabolism schemas return ``None`` because assimilated raw
    channels enter internal stores instead of changing the body in this tick.
    """

    harvest_rows = resolution_plan.harvest_rows
    if harvest_rows.size == 0:
        return None
    cfg = simulation.cfg
    entities = simulation.entities
    gathered = resolution_plan.gathered
    if simulation.gpu_runtime is not None:
        simulation.gpu_runtime.commit_harvest(resolution_plan.harvest_cells, gathered)
    else:
        simulation.environment.commit_harvest(resolution_plan.harvest_cells, gathered)
    harvesters = intents.carrier_index[harvest_rows]
    stats.requested_harvest_resources = np.asarray(
        resolution_plan.requested, dtype=np.float64
    ).sum(axis=0)
    stats.unconstrained_harvest_requests = np.asarray(
        resolution_plan.unconstrained_requested, dtype=np.float64
    ).sum(axis=0)
    stats.resource_intake_capacity_rejected = np.asarray(
        resolution_plan.storage_rejected, dtype=np.float64
    ).sum(axis=0)
    simulation.total_requested_harvest_resources += stats.requested_harvest_resources
    simulation.total_resource_intake_capacity_rejected += (
        stats.resource_intake_capacity_rejected
    )
    stats.harvested_resources = np.asarray(gathered, dtype=np.float64).sum(axis=0)
    simulation.total_harvested_resources += stats.harvested_resources

    if cfg.environment.schema == "legacy-four-channel-v1":
        entities.energy[harvesters] = np.minimum(
            entities.energy[harvesters] + gathered[:, 0], cfg.entities.max_energy
        )
        entities.integrity[harvesters] = np.minimum(
            entities.integrity[harvesters] + gathered[:, 1] * 0.05, 1.0
        )
        entities.information_store[harvesters] = np.minimum(
            entities.information_store[harvesters] + gathered[:, 2], 3.0
        )
        entities.fertility[harvesters] = np.minimum(
            entities.fertility[harvesters] + gathered[:, 3], 3.0
        )
        entities.harvested_energy_total[harvesters] += gathered[:, 0]
        stats.harvested_energy = float(gathered[:, 0].sum())
        return None

    if effective_resource_affinity_q is None:
        raise RuntimeError("effective resource affinity was not prepared")
    assimilated, body_delta = apply_harvest_effects(
        gathered,
        entities.genotype[harvesters],
        cfg,
        resource_affinity_q=effective_resource_affinity_q[harvesters],
    )
    if resource_metabolism_enabled(cfg):
        commit_assimilated_harvest(simulation, harvesters, assimilated, stats)
        return None

    entities.energy[harvesters] = np.minimum(
        entities.energy[harvesters] + body_delta[:, 0], cfg.entities.max_energy
    )
    entities.integrity[harvesters] = np.minimum(
        entities.integrity[harvesters] + body_delta[:, 1], 1.0
    )
    entities.material[harvesters] = np.maximum(
        entities.material[harvesters] + body_delta[:, 2], 0.0
    )
    entities.information_store[harvesters] = np.minimum(
        entities.information_store[harvesters] + body_delta[:, 3], 3.0
    )
    entities.fertility[harvesters] = np.minimum(
        entities.fertility[harvesters] + body_delta[:, 4], 3.0
    )
    entities.harvested_energy_total[harvesters] += body_delta[:, 0]
    stats.harvested_energy = float(
        np.asarray(body_delta[:, 0], dtype=np.float64).sum()
    )
    return body_delta


__all__ = ["commit_harvest_resolution"]
