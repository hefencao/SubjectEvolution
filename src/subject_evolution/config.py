from __future__ import annotations

from dataclasses import dataclass
import json
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
class PolicyConfig:
    temperature: float
    partner_samples: int
    mutation_std: float
    # Per-gene mutation incidence.  Mutation magnitude is conditional on this
    # gate; separating incidence from magnitude prevents a 128-gene strategy
    # from receiving 128 independent perturbations at every birth.
    mutation_probability: float = 0.01


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
    if cfg.run.ticks <= 0:
        raise ValueError("ticks must be positive")
    if not isinstance(cfg.run.gpu_harvest_conflict_planner, bool):
        raise ValueError("run.gpu_harvest_conflict_planner must be a boolean")
    if cfg.run.experiment_mode not in {"scientific", "entertainment"}:
        raise ValueError("run.experiment_mode must be 'scientific' or 'entertainment'")
    if cfg.run.evolution_evaluation_period <= 0:
        raise ValueError("run.evolution_evaluation_period must be positive")
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
