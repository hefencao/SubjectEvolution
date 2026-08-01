"""Signal commit helpers kept outside the simulation orchestrator."""
from __future__ import annotations

from typing import Any

import numpy as np

from se.env.danger_evidence import (
    DANGER_EVIDENCE_SCALE,
    danger_evidence_enabled,
    danger_evidence_quantized,
)
from se.env.niches import public_resource_signal
from se.information import SignalEmissionBatch, SignalEmissionPlan


def emit_actor_signals(
    simulation: Any,
    actors: np.ndarray,
    cells: np.ndarray,
    local_resources: np.ndarray,
    target_indices: np.ndarray,
    strength_multiplier: np.ndarray | None = None,
) -> tuple[SignalEmissionPlan, int, float]:
    if actors.size == 0:
        return SignalEmissionPlan(()), 0, 0.0
    ent = simulation.entities
    multiplier = (
        np.ones(actors.size, dtype=np.float32)
        if strength_multiplier is None
        else np.asarray(strength_multiplier, dtype=np.float32)
    )
    if multiplier.shape != (actors.size,):
        raise ValueError("signal strength multiplier must match actors")
    resource_signal = public_resource_signal(local_resources, simulation.cfg)
    strengths_resource = np.clip(resource_signal, 0.0, 2.0) * 0.15 * multiplier
    actor_evidence_q = (
        (
            np.full((actors.size, 2), DANGER_EVIDENCE_SCALE, dtype=np.int32)
            if simulation.danger_evidence_ablation_enabled
            else danger_evidence_quantized(ent.genotype[actors], simulation.cfg)
        )
        if danger_evidence_enabled(simulation.cfg)
        else None
    )
    hazard = (
        simulation.gpu_runtime.danger_for_cells(cells, actor_evidence_q)
        if simulation.gpu_runtime is not None
        else simulation.environment.danger_for_cells(cells, actor_evidence_q)
    )
    contest_signal = ent.recent_contest_pressure[actors] * np.float32(
        simulation.cfg.entities.resource_contest_signal_weight
    )
    public_danger = np.maximum(hazard, contest_signal).astype(np.float32)
    group_member = simulation.social.group_id[actors] != 0
    plan = SignalEmissionPlan(
        (
            SignalEmissionBatch(0, cells, strengths_resource, emitter="actor-resource"),
            SignalEmissionBatch(
                1, cells, public_danger * 0.15 * multiplier, emitter="actor-danger"
            ),
            SignalEmissionBatch(
                2,
                cells,
                group_member.astype(np.float32) * 0.12 * multiplier,
                emitter="actor-social",
            ),
        )
    )
    signal_energy = float(simulation.cfg.entities.signal_cost) * np.square(
        multiplier.astype(np.float64)
    )
    ent.energy[actors] -= signal_energy.astype(np.float32)
    valid_target = (target_indices >= 0) & ent.alive[target_indices]
    safe_targets = np.where(valid_target, target_indices, 0)
    payloads = np.stack(
        [resource_signal, public_danger, group_member.astype(np.float32)], axis=1
    ).astype(np.float32)
    direct_messages = 0
    if simulation.direct_messages_enabled:
        direct_messages = simulation.information.emit_direct(
            ent.entity_id[actors],
            ent.entity_id[safe_targets] * valid_target.astype(np.uint64),
            payloads,
            np.ones(actors.size, dtype=np.float32),
            simulation.cfg.run.seed,
            simulation.tick,
        )
    return plan, direct_messages, float(signal_energy.sum(dtype=np.float64))


__all__ = ["emit_actor_signals"]
