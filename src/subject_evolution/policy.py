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
    # Read-only diagnostics produced by the same policy path that samples the
    # action.  GPU runs only download them on scheduled evaluation ticks.
    features: Any | None = None
    action_mask: Any | None = None


class ParametricPolicy:
    """Shared action semantics with a fully inherited linear strategy.

    The feature vocabulary and physical action masks are model constraints.
    No action has a hand-authored preference: every logit coefficient lives in
    the entity genome, is inherited by offspring, and is changed only through
    mutation.  This separation is important for scientific runs because the
    engine defines what an action *can* mean without encoding which action an
    entity *should* choose.
    """

    MORPHOLOGY_TRAITS = 8
    MEMORY = 4
    FEATURE_NAMES = (
        "bias",
        "energy",
        "integrity",
        "fertility",
        "scarcity",
        "local_resource",
        "resource_signal",
        "danger_signal",
        "social_signal",
        "partner_exists",
        "mean_partner_need",
        "uncertainty",
        "memory_resource",
        "memory_social",
        "memory_danger",
        "memory_uncertainty",
    )
    STRATEGY_FEATURES = len(FEATURE_NAMES)
    STRATEGY_GENES = len(Action) * STRATEGY_FEATURES
    GENOME_SIZE = MORPHOLOGY_TRAITS + STRATEGY_GENES

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

        local_resource = xp.clip(
            local_resources[:, 0]
            / max(self.cfg.environment.resource_capacity[0], 1e-6),
            0.0,
            1.5,
        )
        features = xp.stack(
            (
                xp.ones_like(e),
                e,
                health,
                fert,
                scarcity,
                local_resource,
                resource_signal,
                danger_signal,
                social_signal,
                partner_exists,
                mean_partner_need,
                uncertainty,
                mem[:, 0],
                mem[:, 1],
                mem[:, 2],
                mem[:, 3],
            ),
            axis=1,
        ).astype(xp.float32, copy=False)
        strategy = g[:, self.MORPHOLOGY_TRAITS :].reshape(
            active.size,
            len(Action),
            self.STRATEGY_FEATURES,
        )
        # Accumulate in a fixed feature order.  Besides making the causal
        # mapping explicit, this avoids backend-dependent contraction plans
        # changing fixed-seed categorical decisions near a logit tie.
        logits = xp.zeros((active.size, len(Action)), dtype=xp.float32)
        for feature_index in range(self.STRATEGY_FEATURES):
            logits += strategy[:, :, feature_index] * features[:, feature_index, None]

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
            validate_mask=False,
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
        angle = normal(explore_ctx, ids, 0.0, np.pi, draw_index=0, validate_stddev=False)
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
            features=features,
            action_mask=mask,
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
