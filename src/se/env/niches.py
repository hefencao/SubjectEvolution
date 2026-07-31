from __future__ import annotations

from typing import Any
import numpy as np

from ..cfg import SimulationConfig
from .resource_sensing import RESOURCE_SENSING_GENE_INDEX, resource_sensing_enabled

RESOURCE_CHANNELS = 4
BODY_OUTCOME_WIDTH = 5
AFFINITY_GENE_START = 1
AFFINITY_GENE_STOP = AFFINITY_GENE_START + RESOURCE_CHANNELS
AFFINITY_SCALE = 4096
UNIFORM_HARVEST_SCHEMA = "uniform-channel-rates-v1"
SELECTIVE_HARVEST_SCHEMA = "affinity-sampled-exclusive-harvest-v1"




def selective_harvest_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.harvest_allocation_schema == SELECTIVE_HARVEST_SCHEMA


def harvest_request_rates(
    resource_affinity_q: Any | None,
    cfg: SimulationConfig,
    *,
    rows: int | None = None,
    channel_draws: Any | None = None,
) -> np.ndarray:
    """Return deterministic per-entity four-channel extraction requests.

    The uniform path is byte-for-byte equivalent to the historical fixed
    channel rates.  The selective path spends the same total raw extraction
    budget on exactly one channel sampled from the inherited affinity budget.
    Draws are supplied by the resolver's state-free keyed random stream, so
    generalists can use several channels while specialists increasingly choose
    one; every action still excludes the other three channels.
    """

    base = float(cfg.entities.harvest_rate)
    if cfg.environment.schema == "legacy-four-channel-v1":
        neutral = np.asarray(
            [base, base * 0.45, base * 0.25, base * 0.18], dtype=np.float32
        )
    else:
        multipliers = np.asarray(
            cfg.environment.harvest_channel_multipliers, dtype=np.float32
        )
        neutral = (np.float32(base) * multipliers).astype(np.float32)
    if not selective_harvest_enabled(cfg):
        count = int(
            rows
            if rows is not None
            else (0 if resource_affinity_q is None else np.asarray(resource_affinity_q).shape[0])
        )
        return np.broadcast_to(neutral, (count, RESOURCE_CHANNELS)).copy()
    if resource_affinity_q is None or channel_draws is None:
        raise ValueError("selective harvest requires resource affinity and channel draws")
    affinity = np.asarray(resource_affinity_q, dtype=np.int64)
    draws = np.asarray(channel_draws, dtype=np.float64)
    if affinity.ndim != 2 or affinity.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("resource affinity must be shaped [N, 4]")
    if draws.shape != (affinity.shape[0],):
        raise ValueError("harvest channel draws must align with resource affinity")
    if rows is not None and affinity.shape[0] != int(rows):
        raise ValueError("resource affinity row count does not match harvest requests")
    multiplier_q = np.rint(
        np.asarray(cfg.environment.harvest_channel_multipliers, dtype=np.float64)
        * AFFINITY_SCALE
    ).astype(np.int64)
    weights = affinity * multiplier_q[None, :]
    denominator = weights.sum(axis=1, dtype=np.int64)
    if np.any(denominator <= 0):
        raise ValueError("selective harvest produced a zero channel budget")
    cumulative = np.cumsum(weights, axis=1, dtype=np.int64)
    thresholds = np.clip(draws, 0.0, np.nextafter(1.0, 0.0)) * denominator
    selected = np.sum(thresholds[:, None] >= cumulative, axis=1)
    selected = np.clip(selected, 0, RESOURCE_CHANNELS - 1).astype(np.int32)
    total_budget = np.float32(neutral.sum(dtype=np.float32))
    rates = np.zeros((affinity.shape[0], RESOURCE_CHANNELS), dtype=np.float32)
    rates[np.arange(rates.shape[0]), selected] = total_budget
    return rates


def constrain_harvest_request_rates(
    rates: Any,
    raw_storage_room: Any | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Cap raw extraction requests by pre-harvest assimilable storage room.

    Returns ``(admitted, rejected)`` in raw environmental units.  A ``None``
    room preserves the archived post-harvest overflow contract exactly.
    """

    requested = np.asarray(rates, dtype=np.float32)
    if raw_storage_room is None:
        return requested, np.zeros_like(requested)
    room = np.asarray(raw_storage_room, dtype=np.float32)
    if room.shape != requested.shape:
        raise ValueError("raw storage room must match harvest request rates")
    if not np.all(np.isfinite(room)) or np.any(room < 0.0):
        raise ValueError("raw storage room must be finite and non-negative")
    admitted = np.minimum(np.maximum(requested, 0.0), room).astype(np.float32)
    rejected = np.maximum(requested - admitted, 0.0).astype(np.float32)
    return admitted, rejected


def resource_affinity_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.resource_affinity_schema == "normalized-four-resource-affinity-v1"


def active_morphology_traits(cfg: SimulationConfig) -> tuple[tuple[int, ...], tuple[str, ...]]:
    indices: list[int] = [0]
    names: list[str] = ["sensor_quality"]
    if resource_affinity_enabled(cfg):
        indices.extend((1, 2, 3, 4))
        names.extend(f"resource_affinity_{index}" for index in range(RESOURCE_CHANNELS))
    indices.append(5)
    names.append("movement_speed")
    if cfg.entities.danger_evidence_schema == "inherited-direct-trace-mixture-v1":
        indices.append(6)
        names.append("danger_direct_trace_mixture")
    elif (
        cfg.entities.reproduction_schema
        == "inherited-conservative-offspring-investment-v2"
    ):
        indices.append(6)
        names.append("reproduction_investment")
    if resource_sensing_enabled(cfg):
        indices.append(RESOURCE_SENSING_GENE_INDEX)
        names.append("resource_sensing_radius")
    return tuple(indices), tuple(names)


def resource_affinity_quantized(genotype: Any, cfg: SimulationConfig) -> np.ndarray:
    """Return a fixed-budget four-channel inherited affinity vector.

    The four morphology genes at indices 1..4 are inert in legacy schemas.  In
    the heterogeneous niche schema they allocate a fixed assimilation budget
    across resource channels.  The vector always sums to ``4 * AFFINITY_SCALE``
    per entity, so increasing one channel necessarily reduces others instead
    of creating a free all-positive advantage.
    """

    values = np.asarray(genotype, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] < AFFINITY_GENE_STOP:
        raise ValueError("genotype does not contain the four resource-affinity traits")
    rows = values.shape[0]
    if not resource_affinity_enabled(cfg):
        return np.full((rows, RESOURCE_CHANNELS), AFFINITY_SCALE, dtype=np.int32)

    traits = np.clip(
        values[:, AFFINITY_GENE_START:AFFINITY_GENE_STOP], -1.0, 1.0
    ).astype(np.float64, copy=False)
    raw = np.rint(
        AFFINITY_SCALE * (1.0 + float(cfg.entities.resource_affinity_strength) * traits)
    ).astype(np.int64)
    minimum = int(round(AFFINITY_SCALE * cfg.entities.resource_affinity_min_efficiency))
    maximum = int(round(AFFINITY_SCALE * cfg.entities.resource_affinity_max_efficiency))
    raw = np.clip(raw, minimum, maximum)
    denominator = raw.sum(axis=1, dtype=np.int64)
    numerator = raw * (RESOURCE_CHANNELS * AFFINITY_SCALE)
    affinity = ((numerator + denominator[:, None] // 2) // denominator[:, None]).astype(
        np.int64
    )
    # Enforce an exact fixed total after integer rounding.  Assign the at-most
    # few-unit residual to the strongest channel, with stable low-index tie
    # resolution from argmax.
    residual = RESOURCE_CHANNELS * AFFINITY_SCALE - affinity.sum(axis=1)
    strongest = np.argmax(raw, axis=1)
    affinity[np.arange(rows), strongest] += residual
    if np.any(affinity <= 0):
        raise RuntimeError("resource affinity normalization produced a non-positive channel")
    return affinity.astype(np.int32, copy=False)


def resource_affinity_float(genotype: Any, cfg: SimulationConfig) -> np.ndarray:
    return (
        resource_affinity_quantized(genotype, cfg).astype(np.float32)
        / np.float32(AFFINITY_SCALE)
    )


def policy_resource_view(
    local_resources: Any,
    genotype: Any,
    cfg: SimulationConfig,
    *,
    resource_affinity_q: Any | None = None,
    storage_room_fraction: Any | None = None,
) -> np.ndarray:
    """Return raw resources with column zero replaced by entity utility.

    Existing policy, knowledge-context and router interfaces consume a single
    scalar resource coordinate.  The heterogeneous schema supplies a neutral
    affinity-weighted mean of normalized channel availability, rescaled to the
    legacy energy-channel capacity.  Raw resource fields remain authoritative
    and are returned unchanged in all other columns.
    """

    local = np.asarray(local_resources, dtype=np.float32)
    if local.ndim != 2 or local.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("local resources must be shaped [N, 4]")
    if cfg.environment.schema == "legacy-four-channel-v1":
        return local
    affinity = (
        resource_affinity_quantized(genotype, cfg)
        if resource_affinity_q is None
        else np.asarray(resource_affinity_q, dtype=np.int32)
    ).astype(np.float64)
    if affinity.shape != (local.shape[0], RESOURCE_CHANNELS):
        raise ValueError("resource affinity must be shaped [N, 4]")
    capacities = np.asarray(cfg.environment.resource_capacity, dtype=np.float64)
    fractions = np.clip(local.astype(np.float64) / capacities[None, :], 0.0, 1.5)
    if storage_room_fraction is not None:
        room = np.asarray(storage_room_fraction, dtype=np.float64)
        if room.shape != fractions.shape:
            raise ValueError("storage room fraction must be shaped [N, 4]")
        if not np.all(np.isfinite(room)) or np.any(room < 0.0):
            raise ValueError("storage room fraction must be finite and non-negative")
        fractions = fractions * np.clip(room, 0.0, 1.0)
    utility = np.sum(fractions * affinity, axis=1) / (
        RESOURCE_CHANNELS * AFFINITY_SCALE
    )
    result = local.copy()
    result[:, 0] = (
        utility * float(cfg.environment.resource_capacity[0])
    ).astype(np.float32)
    return result


def public_resource_signal(local_resources: Any, cfg: SimulationConfig) -> np.ndarray:
    local = np.asarray(local_resources, dtype=np.float32)
    if cfg.environment.schema == "legacy-four-channel-v1":
        return local[:, 0].astype(np.float32, copy=False)
    capacities = np.asarray(cfg.environment.resource_capacity, dtype=np.float64)
    normalized = np.clip(local.astype(np.float64) / capacities[None, :], 0.0, 1.5)
    return normalized.mean(axis=1).astype(np.float32)


def apply_harvest_effects(
    gathered: Any,
    genotype: Any,
    cfg: SimulationConfig,
    *,
    resource_affinity_q: Any | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Map raw resource extraction to assimilated channel and body outcomes.

    Returns ``(assimilated_channels, body_delta)`` where body columns are
    energy, integrity, material, information, and fertility.  Legacy callers
    should retain their historical direct mapping to guarantee archived-run
    compatibility.
    """

    raw = np.asarray(gathered, dtype=np.float32)
    if raw.ndim != 2 or raw.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("gathered resources must be shaped [N, 4]")
    affinity = (
        resource_affinity_quantized(genotype, cfg)
        if resource_affinity_q is None
        else np.asarray(resource_affinity_q, dtype=np.int32)
    ).astype(np.float64)
    if affinity.shape != raw.shape:
        raise ValueError("resource affinity must match gathered resources")
    assimilated = raw.astype(np.float64) * affinity / AFFINITY_SCALE
    effects = np.asarray(cfg.environment.resource_effect_matrix, dtype=np.float64)
    if effects.shape != (RESOURCE_CHANNELS, BODY_OUTCOME_WIDTH):
        raise ValueError("resource effect matrix must be shaped [4, 5]")
    body = assimilated @ effects
    return assimilated.astype(np.float32), body.astype(np.float32)


def resource_affinity_diagnostics(
    alive: Any,
    genotype: Any,
    cfg: SimulationConfig,
) -> dict[str, Any]:
    active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
    active_trait_indices, active_trait_names_tuple = active_morphology_traits(cfg)
    active_trait_names = list(active_trait_names_tuple)
    if active.size == 0:
        return {
            "resource_affinity_schema": cfg.entities.resource_affinity_schema,
            "resource_affinity_mean": [1.0] * RESOURCE_CHANNELS,
            "resource_affinity_std": [0.0] * RESOURCE_CHANNELS,
            "resource_affinity_specialization_mean": 0.0,
            "resource_affinity_effective_dimensions": 0.0,
            "active_morphology_trait_names": active_trait_names,
            "active_morphology_gene_count": len(active_trait_indices),
            "active_morphology_gene_mean": [0.0] * len(active_trait_indices),
            "active_morphology_gene_std": [0.0] * len(active_trait_indices),
            "active_morphology_effective_dimensions": 0.0,
        }
    genotype_values = np.asarray(genotype, dtype=np.float32)[active]
    affinity = resource_affinity_float(genotype_values, cfg).astype(np.float64)
    centered = affinity - affinity.mean(axis=0, keepdims=True)
    if active.size > 1 and np.any(centered):
        singular = np.linalg.svd(centered, compute_uv=False)
        spectrum = singular * singular
        effective = float(
            spectrum.sum() ** 2 / max(float(np.dot(spectrum, spectrum)), 1e-30)
        )
    else:
        effective = 0.0
    morphology = genotype_values[:, active_trait_indices].astype(np.float64)
    morphology_centered = morphology - morphology.mean(axis=0, keepdims=True)
    if active.size > 1 and np.any(morphology_centered):
        singular = np.linalg.svd(morphology_centered, compute_uv=False)
        spectrum = singular * singular
        morphology_effective = float(
            spectrum.sum() ** 2 / max(float(np.dot(spectrum, spectrum)), 1e-30)
        )
    else:
        morphology_effective = 0.0
    return {
        "resource_affinity_schema": cfg.entities.resource_affinity_schema,
        "resource_affinity_mean": affinity.mean(axis=0).tolist(),
        "resource_affinity_std": affinity.std(axis=0).tolist(),
        "resource_affinity_specialization_mean": float(
            np.mean(np.std(affinity, axis=1))
        ),
        "resource_affinity_effective_dimensions": effective,
        "active_morphology_trait_names": active_trait_names,
        "active_morphology_gene_count": len(active_trait_indices),
        "active_morphology_gene_mean": morphology.mean(axis=0).tolist(),
        "active_morphology_gene_std": morphology.std(axis=0).tolist(),
        "active_morphology_effective_dimensions": morphology_effective,
    }


__all__ = [
    "AFFINITY_GENE_START",
    "AFFINITY_GENE_STOP",
    "AFFINITY_SCALE",
    "SELECTIVE_HARVEST_SCHEMA",
    "UNIFORM_HARVEST_SCHEMA",
    "BODY_OUTCOME_WIDTH",
    "RESOURCE_CHANNELS",
    "apply_harvest_effects",
    "harvest_request_rates",
    "active_morphology_traits",
    "policy_resource_view",
    "public_resource_signal",
    "resource_affinity_diagnostics",
    "resource_affinity_enabled",
    "resource_affinity_float",
    "resource_affinity_quantized",
    "selective_harvest_enabled",
]
