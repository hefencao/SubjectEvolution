"""Physical signal observations and terrain-aware direct-message transport."""
from __future__ import annotations

from typing import Any

import numpy as np

POST_HARVEST_RESOURCE_SCHEMA = "post-harvest-current-v2"
TERRAIN_DIRECT_SCHEMA = "terrain-distance-attenuated-v1"
OPENNESS_DIRECT_SCHEMA = "openness-distance-attenuated-v2"


def current_signal_resources(
    simulation: Any,
    cell_ids: np.ndarray,
    pre_action_values: np.ndarray,
) -> np.ndarray:
    """Return the configured resource state reported by a SIGNAL action."""

    if (
        simulation.cfg.information.resource_signal_observation_schema
        != POST_HARVEST_RESOURCE_SCHEMA
    ):
        return np.asarray(pre_action_values, dtype=np.float32)
    cells = np.asarray(cell_ids, dtype=np.int64)
    if getattr(simulation, "gpu_runtime", None) is None:
        return np.asarray(simulation.environment.cell_values(cells), dtype=np.float32)
    return np.asarray(
        simulation.gpu_runtime.resource_values_for_cells(cells), dtype=np.float32
    )


def _periodic_delta(delta: float, extent: int) -> float:
    half = float(extent) * 0.5
    return (float(delta) + half) % float(extent) - half


def _terrain_path_mean(
    terrain: np.ndarray,
    source_cell: int,
    target_cell: int,
    *,
    grid_x: int,
    grid_y: int,
    periodic: bool,
) -> tuple[float, float]:
    sx = int(source_cell % grid_x)
    sy = int(source_cell // grid_x)
    tx = int(target_cell % grid_x)
    ty = int(target_cell // grid_x)
    dx = float(tx - sx)
    dy = float(ty - sy)
    if periodic:
        dx = _periodic_delta(dx, grid_x)
        dy = _periodic_delta(dy, grid_y)
    distance = float(np.hypot(dx, dy))
    steps = max(int(np.ceil(max(abs(dx), abs(dy)))), 1)
    samples: list[float] = []
    for step in range(steps + 1):
        fraction = step / steps
        x = int(np.floor(sx + dx * fraction + 0.5))
        y = int(np.floor(sy + dy * fraction + 0.5))
        if periodic:
            x %= grid_x
            y %= grid_y
        else:
            x = min(max(x, 0), grid_x - 1)
            y = min(max(y, 0), grid_y - 1)
        samples.append(float(terrain[y, x]))
    return float(np.mean(samples, dtype=np.float64)), distance


def direct_message_transport(
    simulation: Any,
    actors: np.ndarray,
    target_indices: np.ndarray,
) -> np.ndarray:
    """Return per-message transport multipliers in ``[0, 1]``.

    The opt-in schema attenuates payload strength along the shortest periodic
    grid path.  It does not prefer groups, genes, roles, or message semantics.
    """

    actor_rows = np.asarray(actors, dtype=np.int32)
    targets = np.asarray(target_indices, dtype=np.int32)
    if actor_rows.shape != targets.shape:
        raise ValueError("signal actors and targets must align")
    schema = simulation.cfg.information.direct_message_propagation_schema
    if schema not in {TERRAIN_DIRECT_SCHEMA, OPENNESS_DIRECT_SCHEMA}:
        return np.ones(actor_rows.size, dtype=np.float32)
    ent = simulation.entities
    valid = (targets >= 0) & ent.alive[np.where(targets >= 0, targets, 0)]
    multipliers = np.zeros(actor_rows.size, dtype=np.float32)
    if not np.any(valid):
        return multipliers
    source_cells = simulation.spatial.cell_ids(ent.x[actor_rows], ent.y[actor_rows])
    safe_targets = np.where(valid, targets, 0)
    target_cells = simulation.spatial.cell_ids(
        ent.x[safe_targets], ent.y[safe_targets]
    )
    if getattr(simulation, "gpu_runtime", None) is None:
        terrain = np.asarray(simulation.environment.terrain, dtype=np.float32)
        openness = np.asarray(
            getattr(
                simulation.environment,
                "signal_openness",
                np.ones_like(terrain, dtype=np.float32),
            ),
            dtype=np.float32,
        )
    else:
        terrain, openness = simulation.gpu_runtime.transport_fields_to_host()
    distance_decay = float(
        simulation.cfg.information.direct_message_distance_decay_per_cell
    )
    for index in np.flatnonzero(valid).tolist():
        if schema == TERRAIN_DIRECT_SCHEMA:
            path_value, distance = _terrain_path_mean(
                terrain,
                int(source_cells[index]),
                int(target_cells[index]),
                grid_x=simulation.cfg.world.grid_x,
                grid_y=simulation.cfg.world.grid_y,
                periodic=simulation.cfg.world.periodic,
            )
            medium_factor = max(
                1.0
                - float(
                    simulation.cfg.information.direct_message_terrain_resistance_fraction
                )
                * path_value,
                0.05,
            )
        else:
            path_value, distance = _terrain_path_mean(
                openness,
                int(source_cells[index]),
                int(target_cells[index]),
                grid_x=simulation.cfg.world.grid_x,
                grid_y=simulation.cfg.world.grid_y,
                periodic=simulation.cfg.world.periodic,
            )
            resistance = float(
                simulation.cfg.information.direct_message_medium_resistance_fraction
            )
            medium_factor = max(1.0 - resistance * (1.0 - path_value), 0.05)
        multipliers[index] = np.float32(
            medium_factor * np.exp(-distance_decay * distance)
        )
    return np.clip(multipliers, 0.0, 1.0).astype(np.float32)


__all__ = [
    "OPENNESS_DIRECT_SCHEMA",
    "POST_HARVEST_RESOURCE_SCHEMA",
    "TERRAIN_DIRECT_SCHEMA",
    "current_signal_resources",
    "direct_message_transport",
]
