from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any
import numpy as np

from .backend import backend_from_array
from .config import SimulationConfig
from .information import InformationObservation
from .random_api import RandomContext, Stream, categorical_from_logits, normal


class Action(IntEnum):
    REST = 0
    MOVE_RESOURCE = 1
    MOVE_SOCIAL = 2
    HARVEST = 3
    SHARE = 4
    SIGNAL = 5
    REPRODUCE = 6
    FLEE = 7


@dataclass
class PolicyDecision:
    action: np.ndarray
    probability: np.ndarray
    entropy: np.ndarray
    direction_x: np.ndarray
    direction_y: np.ndarray
    selected_partner: np.ndarray
    logits: np.ndarray


class ParametricPolicy:
    """Shared policy form with per-entity inherited latent traits and finite memory."""

    TRAITS = 8
    MEMORY = 4

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg

    def decide(
        self,
        active: Any,
        stable_ids: Any,
        energy: Any,
        integrity: Any,
        fertility: Any,
        genotype: Any,
        memory: Any,
        local_resources: Any,
        resource_gradient: tuple[Any, Any],
        danger_gradient: tuple[Any, Any],
        group_direction: tuple[Any, Any],
        partners: Any,
        info: InformationObservation,
        run_seed: int,
        tick: int,
    ) -> PolicyDecision:
        xp = backend_from_array(active).xp
        ids = stable_ids[active]
        e = xp.clip(energy[active] / self.cfg.entities.max_energy, 0.0, 1.5)
        health = xp.clip(integrity[active], 0.0, 1.0)
        fert = xp.clip(fertility[active], 0.0, 2.0)
        g = genotype[active]
        mem = memory[active]
        resource_signal = info.signals[:, 0]
        danger_signal = info.signals[:, 1]
        social_signal = info.signals[:, 2]
        partner_exists = info.partner_mask.any(axis=1).astype(xp.float32)
        partner_need = xp.maximum(e[:, None] - info.partner_energy / self.cfg.entities.max_energy, 0.0)
        mean_partner_need = xp.where(
            info.partner_mask.any(axis=1),
            (partner_need * info.partner_mask).sum(axis=1) / xp.maximum(info.partner_mask.sum(axis=1), 1),
            0.0,
        )
        scarcity = 1.0 - xp.clip(local_resources[:, 0] / max(self.cfg.environment.resource_capacity[0], 1e-6), 0.0, 1.0)
        uncertainty = info.uncertainty.mean(axis=1)

        logits = xp.zeros((active.size, len(Action)), dtype=xp.float32)
        # Traits: resource seeking, sociality, signalling, reproduction, danger aversion,
        # exploration, trust, group dependence. Values are centered near 0 and transformed here.
        seek = 1.0 + g[:, 0]
        social = 1.0 + g[:, 1]
        signal_trait = 1.0 + g[:, 2]
        reproduce_trait = 1.0 + g[:, 3]
        danger_avoid = 1.0 + g[:, 4]
        explore = 1.0 + g[:, 5]
        trust = 1.0 + g[:, 6]
        group_dependence = 1.0 + g[:, 7]

        logits[:, Action.REST] = 0.25 + (1.0 - health) * 0.8 - scarcity * 0.2
        logits[:, Action.MOVE_RESOURCE] = seek * (scarcity + resource_signal * 0.25) + uncertainty * explore * 0.25
        logits[:, Action.MOVE_SOCIAL] = (
            social
            * group_dependence
            * (0.5 + 2.0 * self.cfg.policy.group_influence)
            * (social_signal + 0.25)
            * partner_exists
        )
        logits[:, Action.HARVEST] = seek * xp.clip(local_resources[:, 0], 0.0, 2.0) * (1.2 - e)
        logits[:, Action.SHARE] = social * trust * xp.maximum(e - 0.45, 0.0) * mean_partner_need * 2.5
        logits[:, Action.SIGNAL] = signal_trait * (local_resources[:, 0] + danger_signal) * xp.maximum(e - 0.2, 0.0) * 0.35
        logits[:, Action.REPRODUCE] = reproduce_trait * xp.maximum(e - 0.55, 0.0) * xp.maximum(fert - 0.25, 0.0) * 2.0
        logits[:, Action.FLEE] = danger_avoid * (danger_signal + (1.0 - health) * 0.5)

        # Memory produces modest path dependence without online backpropagation.
        logits[:, Action.MOVE_RESOURCE] += mem[:, 0] * 0.25
        logits[:, Action.MOVE_SOCIAL] += mem[:, 1] * 0.25
        logits[:, Action.FLEE] += mem[:, 2] * 0.25
        logits[:, Action.REST] += mem[:, 3] * 0.10

        mask = xp.ones_like(logits, dtype=bool)
        mask[:, Action.SHARE] = partner_exists > 0
        mask[:, Action.REPRODUCE] = (energy[active] >= self.cfg.entities.reproduction_threshold) & (fertility[active] >= 0.5)
        mask[:, Action.SIGNAL] = energy[active] > self.cfg.entities.signal_cost
        action_ctx = RandomContext(run_seed, tick, phase=50, stream=Stream.POLICY_ACTION)
        action, probability, entropy = categorical_from_logits(
            action_ctx,
            ids,
            logits,
            temperature=self.cfg.policy.temperature,
            mask=mask,
        )

        gx, gy = resource_gradient
        dx = gx[active].astype(xp.float64)
        dy = gy[active].astype(xp.float64)
        dgx, dgy = danger_gradient
        group_dx, group_dy = group_direction
        move_social = action == int(Action.MOVE_SOCIAL)
        flee = action == int(Action.FLEE)
        resource_move = action == int(Action.MOVE_RESOURCE)
        dx = xp.where(move_social, group_dx[active], dx)
        dy = xp.where(move_social, group_dy[active], dy)
        dx = xp.where(flee, -dgx[active], dx)
        dy = xp.where(flee, -dgy[active], dy)

        # When gradients vanish, exploration supplies a direction.
        magnitude = xp.hypot(dx, dy)
        explore_ctx = RandomContext(run_seed, tick, phase=51, stream=Stream.ACTION_EXECUTION)
        angle = normal(explore_ctx, ids, 0.0, np.pi, draw_index=0)
        fallback_x = xp.cos(angle)
        fallback_y = xp.sin(angle)
        needs_fallback = (magnitude < 1e-6) & (resource_move | move_social | flee)
        dx = xp.where(needs_fallback, fallback_x, dx)
        dy = xp.where(needs_fallback, fallback_y, dy)
        magnitude = xp.maximum(xp.hypot(dx, dy), 1e-6)
        dx = (dx / magnitude).astype(xp.float32)
        dy = (dy / magnitude).astype(xp.float32)

        selected_partner = (
            partners[:, 0].astype(xp.int32, copy=False)
            if partners.shape[1] > 0
            else xp.full(active.size, -1, dtype=xp.int32)
        )
        return PolicyDecision(
            action=action,
            probability=probability,
            entropy=entropy,
            direction_x=dx,
            direction_y=dy,
            selected_partner=selected_partner,
            logits=logits,
        )

    def update_memory(
        self,
        active: Any,
        memory: Any,
        local_resources: Any,
        info: InformationObservation,
    ) -> None:
        decay = self.cfg.information.memory_decay
        xp = backend_from_array(memory).xp
        target = xp.stack(
            [
                xp.clip(local_resources[:, 0], 0.0, 1.0),
                xp.clip(info.signals[:, 2], 0.0, 1.0),
                xp.clip(info.signals[:, 1], 0.0, 1.0),
                info.uncertainty.mean(axis=1),
            ],
            axis=1,
        )
        memory[active] = ((1.0 - decay) * memory[active] + decay * target).astype(xp.float32)
