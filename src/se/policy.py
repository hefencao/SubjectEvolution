from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any
import numpy as np

from .backend import backend_from_array
from .cfg import SimulationConfig
from .differentiation.capacity import capacity_gene_count
from .differentiation.functional import functional_module_gene_count
from .differentiation.physiology import physiology_gene_count
from .information import InformationObservation
from se.knowledge import OUTCOME_WIDTH
from se.knowledge.policy import KnowledgePolicyPlan
from se.knowledge.latent import latent_router_gene_count, sparse_selection_gene_count
from se.knowledge.working_memory import working_memory_gene_count
from .random_api import RandomContext, Stream, categorical_from_logits, normal
from .runtime.danger_messages import direct_danger_bearing
from .runtime.reproduction import reproduction_energy_requirement


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
    genetic_logits: Any | None = None
    knowledge_logits: Any | None = None
    genetic_action: Any | None = None
    # L2 diagnostic shadow: the inherited L1 linear router evaluated with the
    # same knowledge batch and counter-based action draw.
    linear_knowledge_logits: Any | None = None
    linear_knowledge_action: Any | None = None
    # Diagnostic action from the same plan before routing-budget rejection.
    # It never controls the world and uses the same counter-based random draw.
    cost_free_knowledge_action: Any | None = None
    # Same knowledge plan and random draw with working-memory coordinates zeroed.
    memory_free_knowledge_action: Any | None = None


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
    STRATEGY_START = MORPHOLOGY_TRAITS
    STRATEGY_STOP = STRATEGY_START + STRATEGY_GENES
    BASE_GENOME_SIZE = STRATEGY_STOP
    KNOWLEDGE_OUTCOME_PREFERENCE_GENES = OUTCOME_WIDTH
    KNOWLEDGE_PREFERENCE_START = BASE_GENOME_SIZE
    KNOWLEDGE_PREFERENCE_STOP = KNOWLEDGE_PREFERENCE_START + KNOWLEDGE_OUTCOME_PREFERENCE_GENES
    KNOWLEDGE_USE_STRENGTH_INDEX = KNOWLEDGE_PREFERENCE_STOP
    K3_GENOME_SIZE = KNOWLEDGE_USE_STRENGTH_INDEX + 1
    LATENT_ROUTER_START = K3_GENOME_SIZE
    # Legacy alias retained for archived K1/K2 code and external readers.
    GENOME_SIZE = BASE_GENOME_SIZE

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg

    @staticmethod
    def uses_knowledge_residual(cfg: SimulationConfig) -> bool:
        return bool(
            cfg.knowledge.policy_influence_enabled
            and cfg.policy.schema == "inherited-linear-policy-knowledge-residual-v1"
        )

    @staticmethod
    def uses_latent_router(cfg: SimulationConfig) -> bool:
        return bool(
            cfg.knowledge.policy_influence_enabled
            and cfg.knowledge.latent_policy_enabled
            and cfg.policy.schema in {
                "inherited-variable-latent-router-v1",
                "inherited-variable-latent-router-mlp-v1",
            }
        )

    @classmethod
    def latent_router_gene_start(cls, cfg: SimulationConfig) -> int:
        if not cls.uses_latent_router(cfg):
            raise ValueError("configuration does not use the latent router schema")
        return cls.LATENT_ROUTER_START

    @classmethod
    def working_memory_gene_start(cls, cfg: SimulationConfig) -> int:
        if not cls.uses_latent_router(cfg):
            raise ValueError("working memory requires the latent router schema")
        return cls.LATENT_ROUTER_START + latent_router_gene_count(
            cfg.knowledge, len(Action)
        )

    @classmethod
    def sparse_selection_gene_start(cls, cfg: SimulationConfig) -> int:
        return cls.working_memory_gene_start(cfg) + working_memory_gene_count(
            cfg.knowledge
        )


    @classmethod
    def sparse_selection_capacity_gene_index(cls, cfg: SimulationConfig) -> int | None:
        if (
            not cfg.knowledge.sparse_selection_enabled
            or cfg.knowledge.sparse_selection_capacity_schema
            != "inherited-discrete-topk-v1"
        ):
            return None
        return cls.sparse_selection_gene_start(cfg) + sparse_selection_gene_count(
            cfg.knowledge
        ) - 1

    @classmethod
    def core_genome_size_for_config(cls, cfg: SimulationConfig) -> int:
        if cls.uses_latent_router(cfg):
            return (
                cls.LATENT_ROUTER_START
                + latent_router_gene_count(cfg.knowledge, len(Action))
                + working_memory_gene_count(cfg.knowledge)
                + sparse_selection_gene_count(cfg.knowledge)
            )
        return cls.K3_GENOME_SIZE if cls.uses_knowledge_residual(cfg) else cls.BASE_GENOME_SIZE

    @classmethod
    def capacity_gene_start(cls, cfg: SimulationConfig) -> int:
        return cls.core_genome_size_for_config(cfg)

    @classmethod
    def functional_module_gene_start(cls, cfg: SimulationConfig) -> int:
        return cls.capacity_gene_start(cfg) + capacity_gene_count(cfg)

    @classmethod
    def physiology_gene_start(cls, cfg: SimulationConfig) -> int:
        return cls.functional_module_gene_start(cfg) + functional_module_gene_count(cfg)

    @classmethod
    def genome_size_for_config(cls, cfg: SimulationConfig) -> int:
        return (
            cls.core_genome_size_for_config(cfg)
            + capacity_gene_count(cfg)
            + functional_module_gene_count(cfg)
            + physiology_gene_count(cfg)
        )

    @classmethod
    def outcome_preferences_from_genotype(cls, genotype: Any) -> Any:
        xp = backend_from_array(genotype).xp
        raw = genotype[:, cls.KNOWLEDGE_PREFERENCE_START : cls.KNOWLEDGE_PREFERENCE_STOP]
        return xp.tanh(raw).astype(xp.float32, copy=False)

    @classmethod
    def knowledge_use_strength_from_genotype(cls, genotype: Any) -> Any:
        xp = backend_from_array(genotype).xp
        raw = genotype[:, cls.KNOWLEDGE_USE_STRENGTH_INDEX]
        return xp.clip(0.5 * (raw + 1.0), 0.0, 1.0).astype(xp.float32, copy=False)

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
        knowledge_plan: KnowledgePolicyPlan | None = None,
        position_x: Any | None = None,
        position_y: Any | None = None,
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
        strategy = g[:, self.STRATEGY_START : self.STRATEGY_STOP].reshape(
            active.size,
            len(Action),
            self.STRATEGY_FEATURES,
        )
        # Accumulate in a fixed feature order.  Besides making the causal
        # mapping explicit, this avoids backend-dependent contraction plans
        # changing fixed-seed categorical decisions near a logit tie.
        genetic_logits = xp.zeros((active.size, len(Action)), dtype=xp.float32)
        for feature_index in range(self.STRATEGY_FEATURES):
            genetic_logits += strategy[:, :, feature_index] * features[:, feature_index, None]
        has_knowledge = bool(
            knowledge_plan is not None
            and (knowledge_plan.size or knowledge_plan.comparison_size)
        )
        knowledge_logits = (
            knowledge_plan.materialize(xp, active.size, len(Action))
            if knowledge_plan is not None and knowledge_plan.size
            else xp.zeros_like(genetic_logits)
        )
        linear_knowledge_logits = (
            knowledge_plan.materialize_comparison(xp, active.size, len(Action))
            if knowledge_plan is not None and knowledge_plan.comparison_size
            else None
        )
        logits = genetic_logits + knowledge_logits

        mask = xp.ones_like(logits, dtype=bool)
        mask[:, Action.SHARE] = partner_exists > 0
        reproduction_requirement = reproduction_energy_requirement(g, self.cfg)
        mask[:, Action.REPRODUCE] = (energy[active] >= reproduction_requirement) & (fertility[active] >= 0.5)
        mask[:, Action.SIGNAL] = energy[active] > self.cfg.entities.signal_cost
        action_ctx = RandomContext(run_seed, tick, phase=50, stream=Stream.POLICY_ACTION)
        genetic_action = None
        linear_knowledge_action = None
        if has_knowledge:
            genetic_action, _, _ = categorical_from_logits(
                action_ctx,
                ids,
                genetic_logits,
                temperature=self.cfg.policy.temperature,
                mask=mask,
                validate_mask=False,
            )
        if linear_knowledge_logits is not None:
            linear_knowledge_action, _, _ = categorical_from_logits(
                action_ctx,
                ids,
                genetic_logits + linear_knowledge_logits,
                temperature=self.cfg.policy.temperature,
                mask=mask,
                validate_mask=False,
            )
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
        if self.cfg.entities.danger_message_direction_schema != "disabled":
            if position_x is None or position_y is None:
                raise ValueError(
                    "source-bearing danger messages require entity positions"
                )
            direct_x, direct_y = direct_danger_bearing(
                active=active,
                stable_ids=stable_ids,
                x=position_x,
                y=position_y,
                info=info,
                cfg=self.cfg,
            )
            direction_weight = xp.float32(
                self.cfg.entities.danger_message_direction_weight
            )
            dgx_active = dgx[active] + direction_weight * direct_x
            dgy_active = dgy[active] + direction_weight * direct_y
        else:
            dgx_active = dgx[active]
            dgy_active = dgy[active]
        group_dx, group_dy = group_direction
        move_social = action == int(Action.MOVE_SOCIAL)
        flee = action == int(Action.FLEE)
        resource_move = action == int(Action.MOVE_RESOURCE)
        dx = xp.where(move_social, group_dx[active], dx)
        dy = xp.where(move_social, group_dy[active], dy)
        dx = xp.where(flee, -dgx_active, dx)
        dy = xp.where(flee, -dgy_active, dy)

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
            genetic_logits=genetic_logits,
            knowledge_logits=knowledge_logits,
            genetic_action=genetic_action,
            linear_knowledge_logits=linear_knowledge_logits,
            linear_knowledge_action=linear_knowledge_action,
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
