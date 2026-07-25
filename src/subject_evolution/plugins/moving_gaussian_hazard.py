"""Legacy synthetic moving Gaussian scalar-field extension.

This is intentionally an abiotic field process, not an entity type. It has no
birth, death, policy, relation, memory, lineage or knowledge state. The module
is retained for v0.22 replay compatibility and optional observation/game use;
it is disabled in the scientific baseline configurations.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from ..environment_process import (
    EnvironmentProcessDescriptor,
    LEGACY_MOVING_GAUSSIAN_SCHEMA,
    register_environment_process,
)


DESCRIPTOR = EnvironmentProcessDescriptor(
    schema=LEGACY_MOVING_GAUSSIAN_SCHEMA,
    mechanism_class="abiotic-additive-scalar-field",
    interpretation="synthetic-observation-or-entertainment-extension",
    description=(
        "Periodic moving Gaussian hazard pulses with no biological identity or "
        "world-control hooks; retained as a disabled compatibility plugin."
    ),
    default_enabled=False,
)


def _finite_float(parameters: Mapping[str, Any], name: str, default: float) -> float:
    value = float(parameters.get(name, default))
    if not math.isfinite(value):
        raise ValueError(f"environment process parameter {name!r} must be finite")
    return value


@dataclass(frozen=True, slots=True)
class MovingGaussianHazardProcess:
    source_count: int
    amplitude: float
    radius: float
    speed: float
    phase_offset: float
    descriptor: EnvironmentProcessDescriptor = DESCRIPTOR

    def hazard_delta(
        self,
        *,
        tick: int,
        xnorm: Any,
        ynorm: Any,
        xp: Any,
    ) -> Any:
        moving = xp.zeros_like(xnorm, dtype=xp.float64)
        for source in range(self.source_count):
            angle = self.phase_offset + 2.0 * xp.pi * source / self.source_count
            direction = angle + 0.5 * xp.pi + 0.37 * source
            center_x = (
                0.5
                + 0.28 * xp.cos(angle)
                + self.speed * tick * xp.cos(direction)
            ) % 1.0
            center_y = (
                0.5
                + 0.28 * xp.sin(angle)
                + self.speed * tick * xp.sin(direction)
            ) % 1.0
            dx = xp.abs(xnorm - center_x)
            dy = xp.abs(ynorm - center_y)
            dx = xp.minimum(dx, 1.0 - dx)
            dy = xp.minimum(dy, 1.0 - dy)
            moving += xp.exp(
                -0.5 * (dx * dx + dy * dy) / (self.radius * self.radius)
            )
        return (self.amplitude / self.source_count) * moving


def build(parameters: Mapping[str, Any]) -> MovingGaussianHazardProcess:
    allowed = {"source_count", "amplitude", "radius", "speed", "phase_offset"}
    unknown = sorted(set(parameters) - allowed)
    if unknown:
        raise ValueError(
            "unknown moving Gaussian environment-process parameters: "
            + ", ".join(unknown)
        )
    source_count = int(parameters.get("source_count", 0))
    amplitude = _finite_float(parameters, "amplitude", 0.0)
    radius = _finite_float(parameters, "radius", 0.12)
    speed = _finite_float(parameters, "speed", 0.0)
    phase_offset = _finite_float(parameters, "phase_offset", 0.0)
    if source_count <= 0:
        raise ValueError("moving Gaussian source_count must be positive")
    if amplitude <= 0.0:
        raise ValueError("moving Gaussian amplitude must be positive")
    if not 0.0 < radius <= 0.5:
        raise ValueError("moving Gaussian radius must be in (0, 0.5]")
    if speed < 0.0:
        raise ValueError("moving Gaussian speed cannot be negative")
    return MovingGaussianHazardProcess(
        source_count=source_count,
        amplitude=amplitude,
        radius=radius,
        speed=speed,
        phase_offset=phase_offset,
    )


def register_plugin() -> None:
    try:
        register_environment_process(DESCRIPTOR, build)
    except ValueError as exc:
        if "already registered" not in str(exc):
            raise


__all__ = ["DESCRIPTOR", "MovingGaussianHazardProcess", "build", "register_plugin"]
