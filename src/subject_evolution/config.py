from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunConfig:
    seed: int
    ticks: int
    metrics_period: int
    checkpoint_period: int
    # Complete action/trajectory records are opt-in.  Keeping the list empty
    # preserves the small, aggregate-only output of the reference runner.
    trajectory_subject_ids: tuple[int, ...] = ()
    # Device harvest planning keeps the same resolution/commit contract.
    # It is enabled for the GPU hybrid path after fixed-seed plan and
    # 100k-entity profiling checks; set false to profile the CPU key builder
    # while retaining the device allocation/commit stages.
    gpu_harvest_conflict_planner: bool = True
    # Scientific mode forbids direct action replacement and opt-in heuristic
    # controllers.  Entertainment mode keeps those mechanisms available for
    # demos without allowing their output to masquerade as scientific data.
    experiment_mode: str = "scientific"
    evolution_evaluation_period: int = 500
    validation_mode: bool = False
    # Until accelerated multi-tick CPU/GPU parity is proven on real CUDA,
    # scientific GPU requests use the CPU reference world semantics.  The
    # legacy hybrid accelerator remains available only as an explicit
    # experimental mode for parity diagnostics and profiling.
    gpu_semantics_mode: str = "strict-reference"
    # Full-world bundles are opt-in because they are larger than the legacy
    # analysis-only NPZ snapshots.  When enabled they use checkpoint_period.
    full_checkpoint_enabled: bool = False


@dataclass(frozen=True)
class WorldConfig:
    width: float
    height: float
    grid_x: int
    grid_y: int
    initial_entities: int
    max_entities: int
    periodic: bool


@dataclass(frozen=True)
class EnvironmentConfig:
    resource_regeneration: tuple[float, float, float, float]
    resource_capacity: tuple[float, float, float, float]
    season_period: int
    season_amplitude: float
    signal_decay: float
    signal_diffusion: float


@dataclass(frozen=True)
class EntityConfig:
    relation_slots: int
    maintenance_cost: float
    movement_cost: float
    signal_cost: float
    share_amount: float
    harvest_rate: float
    reproduction_threshold: float
    reproduction_cost: float
    initial_energy: float
    max_energy: float
    max_age: int
    # Capacity contention is a model rule, not an execution optimization.
    # Missing fields retain the historical stable-ID ordering so archived
    # configs remain replayable; bundled current configs opt into the neutral
    # stateless rule explicitly.
    reproduction_capacity_arbitration: str = "stable-id-v1"


@dataclass(frozen=True)
class InformationConfig:
    channel_loss: float
    receiver_noise: float
    classification_error: float
    memory_decay: float
    max_signal_delay: int
    direct_message_capacity: int = 16
    source_noise: float = 0.0
    # Field-emission delivery cadence for the current resource/danger/social
    # channels.  A period greater than one is an explicit aggregation delay:
    # events queue until that channel's next flush, while field propagation
    # itself continues at the simulation tick cadence.
    signal_flush_periods: tuple[int, ...] = (1, 1, 1)


@dataclass(frozen=True)
class KnowledgeConfig:
    """Dynamic knowledge-copy settings for K1/K2/K3/K4.

    K3 is separately gated and never changes the meaning of the legacy 128
    inherited linear-policy genes.  K4 is a diagnostic-only candidate-subject
    graph and cannot affect policy or world commits.
    """

    enabled: bool = False
    schema: str = "dynamic-knowledge-k1-v1"
    initial_content_count: int = 0
    initial_holders_fraction: float = 0.0
    holder_capacity_bytes: int = 0
    encoded_bytes_per_copy: int = 64
    maintenance_energy_per_byte: float = 0.0
    transfer_period: int = 1
    transfer_probability: float = 0.0
    attention_slots_per_tick: int = 1
    transfer_base_energy_cost: float = 0.0
    transfer_energy_per_byte: float = 0.0
    receive_energy_per_byte: float = 0.0
    forget_probability: float = 0.0
    capacity_eviction: str = "oldest-copy-v1"
    log_transfer_events: bool = False

    # K2 local consequence learning.  These fields are inert when disabled.
    learning_enabled: bool = False
    outcome_schema: str = "local-outcome-v1"
    experience_creation_enabled: bool = True
    experience_creation_requires_free_capacity: bool = True
    verification_energy_cost: float = 0.0
    confidence_learning_rate: float = 0.25
    confidence_decay_per_tick: float = 0.0
    initial_experience_confidence: float = 0.25
    max_updates_per_outcome: int = 1
    log_outcome_updates: bool = False

    # K3 sparse local-outcome residuals.  All fields are inert unless the
    # separately versioned policy and knowledge schemas are enabled.
    policy_influence_enabled: bool = False
    policy_residual_schema: str = "sparse-local-outcome-residual-v1"
    policy_min_confidence: float = 0.0
    policy_min_local_samples: int = 1
    policy_sample_saturation: float = 4.0
    policy_unverified_transfer_weight: float = 0.25
    policy_outcome_scales: tuple[float, float, float, float, float] = (1.0, 1.0, 1.0, 1.0, 1.0)
    policy_outcome_clip: float = 1.0
    policy_max_abs_logit_residual: float = 1.0
    log_policy_contributions: bool = False

    # High-extensibility latent knowledge.  Variable-length content payloads
    # are routed through separately versioned inherited quantized L1/L2
    # parameters and publish only to the action-logit residual boundary.
    latent_policy_enabled: bool = False
    latent_schema: str = "variable-latent-knowledge-v1"
    latent_router_schema: str = "quantized-linear-latent-router-v1"
    latent_length_levels: tuple[int, ...] = (4, 8, 16, 32)
    # Width of the deterministic latent projection shared by L1 and L2.
    latent_router_hidden_width: int = 8
    # L2-only inherited MLP width.  The activation is an exact integer hard-tanh.
    latent_router_mlp_hidden_width: int = 8
    latent_router_activation_clip: float = 1.0
    latent_value_quantization_scale: int = 4096
    latent_router_weight_quantization_scale: int = 2048
    latent_outcome_injection: float = 0.5
    latent_base_encoded_bytes: int = 32
    latent_bytes_per_value: int = 2
    latent_length_mutation_probability: float = 0.125
    latent_max_abs_logit_residual: float = 1.0

    # K4 candidate knowledge-subject diagnostics.  This layer is observational
    # and is inert unless explicitly enabled.
    candidate_tracking_enabled: bool = False
    candidate_schema: str = "knowledge-subject-candidate-v1"
    candidate_graph_schema: str = "candidate-subject-graph-v1"
    candidate_update_period: int = 10
    candidate_region_grid_x: int = 8
    candidate_region_grid_y: int = 8


@dataclass(frozen=True)
class PolicyConfig:
    temperature: float
    partner_samples: int
    mutation_std: float
    # Per-gene mutation incidence.  Mutation magnitude is conditional on this
    # gate; separating incidence from magnitude prevents a 128-gene strategy
    # from receiving 128 independent perturbations at every birth.
    mutation_probability: float = 0.01
    schema: str = "inherited-linear-policy-v1"


@dataclass(frozen=True)
class SocialConfig:
    group_update_period: int
    trust_group_threshold: float
    group_min_members: int
    relation_decay: float
    trust_gain_share: float
    trust_loss_failed: float


@dataclass(frozen=True)
class ControlConfig:
    """Entertainment controller settings; all heuristic behaviour is opt-in."""

    heuristic_social_guidance: bool = False
    heuristic_social_guidance_weight: float = 0.25
    # The recovery intervention deterministically selects this fraction of
    # the living cohort.  It only affects the entertainment-only
    # ``independent-foraging-override`` action-replacement intervention.
    autonomy_recovery_fraction: float = 0.25
    autonomy_activation_energy_fraction: float = 0.35
    autonomy_harvest_threshold: float = 0.05


@dataclass(frozen=True)
class SimulationConfig:
    run: RunConfig
    world: WorldConfig
    environment: EnvironmentConfig
    entities: EntityConfig
    information: InformationConfig
    knowledge: KnowledgeConfig
    policy: PolicyConfig
    social: SocialConfig
    control: ControlConfig

    @property
    def cell_width(self) -> float:
        return self.world.width / self.world.grid_x

    @property
    def cell_height(self) -> float:
        return self.world.height / self.world.grid_y


def _require(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Missing configuration section: {key}")
    return mapping[key]


def _probability(name: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")
    return value


def load_config(path: str | Path) -> SimulationConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    information_raw = _require(raw, "information")
    policy_raw = dict(_require(raw, "policy"))
    # Accepted for old run files, but no longer used: action preferences are
    # inherited genome data rather than a global hand-authored group weight.
    policy_raw.pop("group_influence", None)
    cfg = SimulationConfig(
        run=RunConfig(
            **{
                **_require(raw, "run"),
                "trajectory_subject_ids": tuple(_require(raw, "run").get("trajectory_subject_ids", ())),
                "gpu_harvest_conflict_planner": _require(raw, "run").get(
                    "gpu_harvest_conflict_planner", True
                ),
            }
        ),
        world=WorldConfig(**_require(raw, "world")),
        environment=EnvironmentConfig(
            resource_regeneration=tuple(_require(raw, "environment")["resource_regeneration"]),
            resource_capacity=tuple(_require(raw, "environment")["resource_capacity"]),
            season_period=_require(raw, "environment")["season_period"],
            season_amplitude=_require(raw, "environment")["season_amplitude"],
            signal_decay=_require(raw, "environment")["signal_decay"],
            signal_diffusion=_require(raw, "environment")["signal_diffusion"],
        ),
        entities=EntityConfig(**_require(raw, "entities")),
        information=InformationConfig(
            **{
                **information_raw,
                "signal_flush_periods": tuple(information_raw.get("signal_flush_periods", (1, 1, 1))),
            }
        ),
        knowledge=KnowledgeConfig(
            **{
                **raw.get("knowledge", {}),
                "policy_outcome_scales": tuple(
                    raw.get("knowledge", {}).get(
                        "policy_outcome_scales", (1.0, 1.0, 1.0, 1.0, 1.0)
                    )
                ),
                "latent_length_levels": tuple(
                    raw.get("knowledge", {}).get(
                        "latent_length_levels", (4, 8, 16, 32)
                    )
                ),
            }
        ),
        policy=PolicyConfig(**policy_raw),
        social=SocialConfig(**_require(raw, "social")),
        control=ControlConfig(**raw.get("control", {})),
    )
    validate_config(cfg)
    return cfg


def validate_config(cfg: SimulationConfig) -> None:
    if cfg.world.initial_entities <= 0:
        raise ValueError("initial_entities must be positive")
    if cfg.world.max_entities < cfg.world.initial_entities:
        raise ValueError("max_entities must be >= initial_entities")
    if cfg.world.grid_x <= 0 or cfg.world.grid_y <= 0:
        raise ValueError("grid dimensions must be positive")
    if (
        not math.isfinite(cfg.world.width)
        or not math.isfinite(cfg.world.height)
        or cfg.world.width <= 0.0
        or cfg.world.height <= 0.0
    ):
        raise ValueError("world width and height must be finite and positive")
    if cfg.run.ticks <= 0:
        raise ValueError("ticks must be positive")
    if not isinstance(cfg.run.gpu_harvest_conflict_planner, bool):
        raise ValueError("run.gpu_harvest_conflict_planner must be a boolean")
    if cfg.run.experiment_mode not in {"scientific", "entertainment"}:
        raise ValueError("run.experiment_mode must be 'scientific' or 'entertainment'")
    if cfg.run.evolution_evaluation_period <= 0:
        raise ValueError("run.evolution_evaluation_period must be positive")
    if not isinstance(cfg.run.full_checkpoint_enabled, bool):
        raise ValueError("run.full_checkpoint_enabled must be a boolean")
    if not isinstance(cfg.run.validation_mode, bool):
        raise ValueError("run.validation_mode must be a boolean")
    if cfg.run.gpu_semantics_mode not in {"strict-reference", "hybrid-accelerated"}:
        raise ValueError(
            "run.gpu_semantics_mode must be one of: "
            "'strict-reference', 'hybrid-accelerated'"
        )
    if len(cfg.environment.resource_regeneration) != 4 or len(cfg.environment.resource_capacity) != 4:
        raise ValueError("MVP requires exactly four resource channels")
    if any(v < 0 for v in cfg.environment.resource_regeneration):
        raise ValueError("resource regeneration cannot be negative")
    if any(v <= 0 for v in cfg.environment.resource_capacity):
        raise ValueError("resource capacities must be positive")
    _probability("channel_loss", cfg.information.channel_loss)
    _probability("classification_error", cfg.information.classification_error)
    if cfg.information.receiver_noise < 0:
        raise ValueError("receiver_noise cannot be negative")
    if cfg.information.source_noise < 0:
        raise ValueError("source_noise cannot be negative")
    if cfg.information.max_signal_delay < 0:
        raise ValueError("max_signal_delay cannot be negative")
    if cfg.information.direct_message_capacity < 0:
        raise ValueError("direct_message_capacity cannot be negative")
    if len(cfg.information.signal_flush_periods) != 3 or any(
        not isinstance(period, int) or isinstance(period, bool) or period <= 0
        for period in cfg.information.signal_flush_periods
    ):
        raise ValueError("information.signal_flush_periods must contain three positive integers")

    if not isinstance(cfg.knowledge.enabled, bool):
        raise ValueError("knowledge.enabled must be a boolean")
    if cfg.knowledge.schema not in {
        "dynamic-knowledge-k1-v1",
        "dynamic-knowledge-k2-v1",
        "dynamic-knowledge-k3-v1",
        "dynamic-knowledge-k4-v1",
        "dynamic-knowledge-latent-v1",
    }:
        raise ValueError(
            "knowledge.schema must be one of: 'dynamic-knowledge-k1-v1', "
            "'dynamic-knowledge-k2-v1', 'dynamic-knowledge-k3-v1', "
            "'dynamic-knowledge-k4-v1', 'dynamic-knowledge-latent-v1'"
        )
    if cfg.knowledge.initial_content_count < 0:
        raise ValueError("knowledge.initial_content_count cannot be negative")
    _probability("knowledge.initial_holders_fraction", cfg.knowledge.initial_holders_fraction)
    if cfg.knowledge.holder_capacity_bytes < 0:
        raise ValueError("knowledge.holder_capacity_bytes cannot be negative")
    if cfg.knowledge.encoded_bytes_per_copy <= 0:
        raise ValueError("knowledge.encoded_bytes_per_copy must be positive")
    if cfg.knowledge.transfer_period <= 0:
        raise ValueError("knowledge.transfer_period must be positive")
    _probability("knowledge.transfer_probability", cfg.knowledge.transfer_probability)
    _probability("knowledge.forget_probability", cfg.knowledge.forget_probability)
    if cfg.knowledge.attention_slots_per_tick < 0:
        raise ValueError("knowledge.attention_slots_per_tick cannot be negative")
    if any(
        value < 0.0
        for value in (
            cfg.knowledge.maintenance_energy_per_byte,
            cfg.knowledge.transfer_base_energy_cost,
            cfg.knowledge.transfer_energy_per_byte,
            cfg.knowledge.receive_energy_per_byte,
        )
    ):
        raise ValueError("knowledge energy costs cannot be negative")
    if cfg.knowledge.capacity_eviction != "oldest-copy-v1":
        raise ValueError("knowledge.capacity_eviction must be 'oldest-copy-v1'")
    if not isinstance(cfg.knowledge.log_transfer_events, bool):
        raise ValueError("knowledge.log_transfer_events must be a boolean")
    if not isinstance(cfg.knowledge.learning_enabled, bool):
        raise ValueError("knowledge.learning_enabled must be a boolean")
    if cfg.knowledge.outcome_schema != "local-outcome-v1":
        raise ValueError("knowledge.outcome_schema must be 'local-outcome-v1'")
    if not isinstance(cfg.knowledge.experience_creation_enabled, bool):
        raise ValueError("knowledge.experience_creation_enabled must be a boolean")
    if not isinstance(cfg.knowledge.experience_creation_requires_free_capacity, bool):
        raise ValueError(
            "knowledge.experience_creation_requires_free_capacity must be a boolean"
        )
    if cfg.knowledge.verification_energy_cost < 0.0:
        raise ValueError("knowledge.verification_energy_cost cannot be negative")
    _probability(
        "knowledge.confidence_learning_rate",
        cfg.knowledge.confidence_learning_rate,
    )
    _probability(
        "knowledge.confidence_decay_per_tick",
        cfg.knowledge.confidence_decay_per_tick,
    )
    _probability(
        "knowledge.initial_experience_confidence",
        cfg.knowledge.initial_experience_confidence,
    )
    if cfg.knowledge.max_updates_per_outcome <= 0:
        raise ValueError("knowledge.max_updates_per_outcome must be positive")
    if not isinstance(cfg.knowledge.log_outcome_updates, bool):
        raise ValueError("knowledge.log_outcome_updates must be a boolean")
    if cfg.knowledge.learning_enabled and cfg.knowledge.schema not in {
        "dynamic-knowledge-k2-v1",
        "dynamic-knowledge-k3-v1",
        "dynamic-knowledge-k4-v1",
        "dynamic-knowledge-latent-v1",
    }:
        raise ValueError(
            "knowledge.learning_enabled requires K2 or K3 knowledge schema"
        )
    if cfg.knowledge.learning_enabled and not cfg.knowledge.enabled:
        raise ValueError("knowledge.learning_enabled requires knowledge.enabled")
    if cfg.knowledge.enabled and cfg.knowledge.holder_capacity_bytes <= 0:
        raise ValueError("enabled knowledge requires a positive holder_capacity_bytes")
    if not isinstance(cfg.knowledge.policy_influence_enabled, bool):
        raise ValueError("knowledge.policy_influence_enabled must be a boolean")
    if cfg.knowledge.policy_residual_schema not in {
        "sparse-local-outcome-residual-v1",
        "quantized-variable-latent-residual-v1",
        "quantized-variable-latent-mlp-residual-v1",
    }:
        raise ValueError("unknown knowledge.policy_residual_schema")
    _probability("knowledge.policy_min_confidence", cfg.knowledge.policy_min_confidence)
    if cfg.knowledge.policy_min_local_samples < 0:
        raise ValueError("knowledge.policy_min_local_samples cannot be negative")
    if cfg.knowledge.policy_sample_saturation <= 0.0:
        raise ValueError("knowledge.policy_sample_saturation must be positive")
    _probability(
        "knowledge.policy_unverified_transfer_weight",
        cfg.knowledge.policy_unverified_transfer_weight,
    )
    if (
        len(cfg.knowledge.policy_outcome_scales) != 5
        or any(not math.isfinite(v) or v <= 0.0 for v in cfg.knowledge.policy_outcome_scales)
    ):
        raise ValueError("knowledge.policy_outcome_scales must contain five positive finite values")
    if not math.isfinite(cfg.knowledge.policy_outcome_clip) or cfg.knowledge.policy_outcome_clip <= 0.0:
        raise ValueError("knowledge.policy_outcome_clip must be positive and finite")
    if (
        not math.isfinite(cfg.knowledge.policy_max_abs_logit_residual)
        or cfg.knowledge.policy_max_abs_logit_residual <= 0.0
    ):
        raise ValueError("knowledge.policy_max_abs_logit_residual must be positive and finite")
    if not isinstance(cfg.knowledge.log_policy_contributions, bool):
        raise ValueError("knowledge.log_policy_contributions must be a boolean")
    if not isinstance(cfg.knowledge.latent_policy_enabled, bool):
        raise ValueError("knowledge.latent_policy_enabled must be a boolean")
    if cfg.knowledge.latent_schema != "variable-latent-knowledge-v1":
        raise ValueError("unknown knowledge.latent_schema")
    if cfg.knowledge.latent_router_schema not in {
        "quantized-linear-latent-router-v1",
        "quantized-mlp-latent-router-v1",
    }:
        raise ValueError("unknown knowledge.latent_router_schema")
    levels = cfg.knowledge.latent_length_levels
    if (
        not levels
        or tuple(sorted(set(levels))) != tuple(levels)
        or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 or value > 256 for value in levels)
    ):
        raise ValueError("knowledge.latent_length_levels must be unique ascending integers in [1, 256]")
    if cfg.knowledge.latent_router_hidden_width <= 0 or cfg.knowledge.latent_router_hidden_width > 32:
        raise ValueError("knowledge.latent_router_hidden_width must be in [1, 32]")
    if (
        cfg.knowledge.latent_router_mlp_hidden_width <= 0
        or cfg.knowledge.latent_router_mlp_hidden_width > 32
    ):
        raise ValueError("knowledge.latent_router_mlp_hidden_width must be in [1, 32]")
    if (
        not math.isfinite(cfg.knowledge.latent_router_activation_clip)
        or cfg.knowledge.latent_router_activation_clip <= 0.0
        or cfg.knowledge.latent_router_activation_clip > 8.0
    ):
        raise ValueError(
            "knowledge.latent_router_activation_clip must be finite and in (0, 8]"
        )
    if cfg.knowledge.latent_value_quantization_scale <= 0:
        raise ValueError("knowledge.latent_value_quantization_scale must be positive")
    if cfg.knowledge.latent_router_weight_quantization_scale <= 0:
        raise ValueError("knowledge.latent_router_weight_quantization_scale must be positive")
    if not math.isfinite(cfg.knowledge.latent_outcome_injection) or cfg.knowledge.latent_outcome_injection < 0.0:
        raise ValueError("knowledge.latent_outcome_injection must be finite and non-negative")
    if cfg.knowledge.latent_base_encoded_bytes <= 0 or cfg.knowledge.latent_bytes_per_value <= 0:
        raise ValueError("latent encoded byte parameters must be positive")
    _probability(
        "knowledge.latent_length_mutation_probability",
        cfg.knowledge.latent_length_mutation_probability,
    )
    if (
        not math.isfinite(cfg.knowledge.latent_max_abs_logit_residual)
        or cfg.knowledge.latent_max_abs_logit_residual <= 0.0
    ):
        raise ValueError("knowledge.latent_max_abs_logit_residual must be positive and finite")

    if not isinstance(cfg.knowledge.candidate_tracking_enabled, bool):
        raise ValueError("knowledge.candidate_tracking_enabled must be a boolean")
    if cfg.knowledge.candidate_schema != "knowledge-subject-candidate-v1":
        raise ValueError("knowledge.candidate_schema must be 'knowledge-subject-candidate-v1'")
    if cfg.knowledge.candidate_graph_schema != "candidate-subject-graph-v1":
        raise ValueError("knowledge.candidate_graph_schema must be 'candidate-subject-graph-v1'")
    if cfg.knowledge.candidate_update_period <= 0:
        raise ValueError("knowledge.candidate_update_period must be positive")
    if cfg.knowledge.candidate_region_grid_x <= 0 or cfg.knowledge.candidate_region_grid_y <= 0:
        raise ValueError("knowledge candidate region grid dimensions must be positive")
    if cfg.knowledge.candidate_tracking_enabled:
        if not cfg.knowledge.enabled or not cfg.knowledge.learning_enabled:
            raise ValueError("K4 candidate tracking requires enabled K2 learning")
        if cfg.knowledge.schema not in {"dynamic-knowledge-k4-v1", "dynamic-knowledge-latent-v1"}:
            raise ValueError("K4 candidate tracking requires K4 or latent knowledge schema")
        if not cfg.knowledge.policy_influence_enabled:
            raise ValueError("K4 candidate tracking requires K3 policy influence")
    if cfg.policy.schema not in {
        "inherited-linear-policy-v1",
        "inherited-linear-policy-knowledge-residual-v1",
        "inherited-variable-latent-router-v1",
        "inherited-variable-latent-router-mlp-v1",
    }:
        raise ValueError("unknown policy.schema")
    if cfg.knowledge.policy_influence_enabled:
        if not cfg.knowledge.enabled or not cfg.knowledge.learning_enabled:
            raise ValueError("knowledge policy influence requires enabled local learning")
        if cfg.knowledge.latent_policy_enabled:
            if cfg.knowledge.schema != "dynamic-knowledge-latent-v1":
                raise ValueError("latent policy requires dynamic-knowledge-latent-v1")
            if cfg.knowledge.latent_router_schema == "quantized-linear-latent-router-v1":
                if cfg.knowledge.policy_residual_schema != "quantized-variable-latent-residual-v1":
                    raise ValueError("linear latent policy requires its residual schema")
                if cfg.policy.schema != "inherited-variable-latent-router-v1":
                    raise ValueError("linear latent policy requires inherited-variable-latent-router-v1")
            else:
                if cfg.knowledge.policy_residual_schema != "quantized-variable-latent-mlp-residual-v1":
                    raise ValueError("MLP latent policy requires its residual schema")
                if cfg.policy.schema != "inherited-variable-latent-router-mlp-v1":
                    raise ValueError(
                        "MLP latent policy requires inherited-variable-latent-router-mlp-v1"
                    )
        else:
            if cfg.knowledge.schema not in {"dynamic-knowledge-k3-v1", "dynamic-knowledge-k4-v1"}:
                raise ValueError("K3 policy influence requires dynamic-knowledge-k3-v1 or dynamic-knowledge-k4-v1")
            if cfg.knowledge.policy_residual_schema != "sparse-local-outcome-residual-v1":
                raise ValueError("K3 policy influence requires sparse-local-outcome-residual-v1")
            if cfg.policy.schema != "inherited-linear-policy-knowledge-residual-v1":
                raise ValueError("K3 policy influence requires the K3 policy schema")
    elif cfg.policy.schema != "inherited-linear-policy-v1":
        raise ValueError("knowledge policy schema requires policy influence")
    if cfg.knowledge.latent_policy_enabled and not cfg.knowledge.policy_influence_enabled:
        raise ValueError("knowledge.latent_policy_enabled requires policy influence")
    _probability("trust_group_threshold", cfg.social.trust_group_threshold)
    if not isinstance(cfg.control.heuristic_social_guidance, bool):
        raise ValueError("control.heuristic_social_guidance must be a boolean")
    _probability("control.heuristic_social_guidance_weight", cfg.control.heuristic_social_guidance_weight)
    _probability("control.autonomy_recovery_fraction", cfg.control.autonomy_recovery_fraction)
    _probability(
        "control.autonomy_activation_energy_fraction",
        cfg.control.autonomy_activation_energy_fraction,
    )
    if cfg.control.autonomy_harvest_threshold < 0:
        raise ValueError("control.autonomy_harvest_threshold cannot be negative")
    if cfg.policy.temperature <= 0:
        raise ValueError("policy.temperature must be positive")
    _probability("policy.mutation_probability", cfg.policy.mutation_probability)
    if cfg.entities.relation_slots <= 0:
        raise ValueError("relation_slots must be positive")
    if cfg.entities.reproduction_capacity_arbitration not in {
        "stable-id-v1",
        "stateless-random-v1",
    }:
        raise ValueError(
            "entities.reproduction_capacity_arbitration must be one of: "
            "'stable-id-v1', 'stateless-random-v1'"
        )
