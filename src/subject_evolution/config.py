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
    group_influence: float


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
    """Optional controller experiments; all heuristic behaviour is opt-in."""

    heuristic_social_guidance: bool = False
    heuristic_social_guidance_weight: float = 0.25


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
    cfg = SimulationConfig(
        run=RunConfig(
            **{
                **_require(raw, "run"),
                "trajectory_subject_ids": tuple(_require(raw, "run").get("trajectory_subject_ids", ())),
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
        policy=PolicyConfig(**_require(raw, "policy")),
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
    if cfg.policy.temperature <= 0:
        raise ValueError("policy.temperature must be positive")
    if cfg.entities.relation_slots <= 0:
        raise ValueError("relation_slots must be positive")
