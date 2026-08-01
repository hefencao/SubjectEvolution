"""Role-neutral signal propagation through heterogeneous terrain.

The legacy path remains an exact uniform isotropic diffusion update.  The
terrain-aware path changes only transport conductance between neighboring grid
cells; it does not create, classify, reward, or route message content.
"""
from __future__ import annotations

from typing import Any


UNIFORM_SIGNAL_SCHEMA = "uniform-isotropic-v1"
TERRAIN_SIGNAL_SCHEMA = "terrain-resisted-diffusion-v1"
OPENNESS_SIGNAL_SCHEMA = "independent-openness-diffusion-v2"


def propagate_signal_field(
    field: Any,
    source: Any,
    *,
    decay: float,
    diffusion: float,
    schema: str,
    terrain: Any | None = None,
    terrain_resistance_fraction: float = 0.0,
    signal_openness: Any | None = None,
    medium_conductance_fraction: float = 0.0,
    xp: Any,
) -> Any:
    """Advance a non-negative multi-channel signal field by one tick.

    ``terrain`` is a normalized resistance field in ``[0, 1]``.  Under the
    terrain-aware schema, each cardinal edge receives the arithmetic mean of
    its two endpoint permeabilities.  This preserves a role-neutral physical
    boundary: terrain changes transport, not signal semantics.
    """

    center = field
    if schema == UNIFORM_SIGNAL_SCHEMA:
        neighbor_mean = (
            xp.roll(center, 1, axis=1)
            + xp.roll(center, -1, axis=1)
            + xp.roll(center, 1, axis=2)
            + xp.roll(center, -1, axis=2)
        ) * 0.25
        return xp.maximum(
            (1.0 - decay - diffusion) * center
            + diffusion * neighbor_mean
            + source,
            0.0,
        ).astype(xp.float32)

    if schema == TERRAIN_SIGNAL_SCHEMA:
        if terrain is None:
            raise ValueError("terrain-aware signal propagation requires terrain")
        terrain_values = xp.clip(xp.asarray(terrain, dtype=xp.float32), 0.0, 1.0)
        permeability = xp.clip(
            1.0 - float(terrain_resistance_fraction) * terrain_values,
            0.05,
            1.0,
        )
    elif schema == OPENNESS_SIGNAL_SCHEMA:
        if signal_openness is None:
            raise ValueError("independent signal propagation requires signal openness")
        openness = xp.clip(
            xp.asarray(signal_openness, dtype=xp.float32), 0.0, 1.0
        )
        coupling = float(medium_conductance_fraction)
        permeability = xp.clip((1.0 - coupling) + coupling * openness, 0.05, 1.0)
    else:
        raise ValueError(f"unsupported signal propagation schema: {schema}")
    flux = xp.zeros_like(center)
    for axis, shift in ((1, 1), (1, -1), (2, 1), (2, -1)):
        neighbor = xp.roll(center, shift, axis=axis)
        neighbor_permeability = xp.roll(permeability, shift, axis=axis - 1)
        edge = 0.5 * (permeability + neighbor_permeability)
        flux += edge[None, :, :] * (neighbor - center)
    return xp.maximum(
        (1.0 - decay) * center + 0.25 * diffusion * flux + source,
        0.0,
    ).astype(xp.float32)


__all__ = [
    "OPENNESS_SIGNAL_SCHEMA",
    "TERRAIN_SIGNAL_SCHEMA",
    "UNIFORM_SIGNAL_SCHEMA",
    "propagate_signal_field",
]
