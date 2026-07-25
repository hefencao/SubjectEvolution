from __future__ import annotations

from typing import Any
import numpy as np

from .config import SimulationConfig

DANGER_EVIDENCE_GENE_INDEX = 6
DANGER_EVIDENCE_SCALE = 4096
DANGER_EVIDENCE_TOTAL = 2 * DANGER_EVIDENCE_SCALE


def danger_evidence_enabled(cfg: SimulationConfig) -> bool:
    return (
        cfg.entities.danger_evidence_schema
        == "inherited-direct-trace-mixture-v1"
    )


def danger_evidence_quantized(genotype: Any, cfg: SimulationConfig) -> np.ndarray:
    """Return fixed-budget inherited weights for direct hazard and mortality trace.

    The neutral vector is ``[1, 1]``.  When enabled, morphology gene 6 shifts a
    fixed total evidence budget between immediate physical hazard and the local
    decaying death trace.  Increasing one source necessarily decreases the
    other, so the trait cannot create a free all-positive sensory advantage.
    """

    values = np.asarray(genotype, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] <= DANGER_EVIDENCE_GENE_INDEX:
        raise ValueError("genotype does not contain the danger-evidence trait")
    rows = values.shape[0]
    if not danger_evidence_enabled(cfg):
        return np.full(
            (rows, 2), DANGER_EVIDENCE_SCALE, dtype=np.int32
        )
    trait = np.clip(
        values[:, DANGER_EVIDENCE_GENE_INDEX], -1.0, 1.0
    ).astype(np.float64, copy=False)
    direct = np.rint(
        DANGER_EVIDENCE_SCALE
        * (1.0 + float(cfg.entities.danger_evidence_strength) * trait)
    ).astype(np.int64)
    minimum = int(
        round(
            DANGER_EVIDENCE_SCALE
            * float(cfg.entities.danger_evidence_min_efficiency)
        )
    )
    maximum = int(
        round(
            DANGER_EVIDENCE_SCALE
            * float(cfg.entities.danger_evidence_max_efficiency)
        )
    )
    direct = np.clip(direct, minimum, maximum)
    trace = DANGER_EVIDENCE_TOTAL - direct
    if np.any(trace <= 0):
        raise RuntimeError("danger evidence normalization produced a non-positive weight")
    return np.stack((direct, trace), axis=1).astype(np.int32, copy=False)


def mix_danger_components(
    direct_hazard: Any,
    weighted_mortality_trace: Any,
    evidence_q: Any,
) -> np.ndarray:
    direct = np.asarray(direct_hazard, dtype=np.float32)
    trace = np.asarray(weighted_mortality_trace, dtype=np.float32)
    weights = np.asarray(evidence_q, dtype=np.int32)
    if direct.shape != trace.shape:
        raise ValueError("direct hazard and mortality trace must align")
    if weights.shape != (direct.size, 2):
        raise ValueError("danger evidence weights must be shaped [N, 2]")
    mixed = (
        direct.astype(np.float64) * weights[:, 0]
        + trace.astype(np.float64) * weights[:, 1]
    ) / DANGER_EVIDENCE_SCALE
    return mixed.astype(np.float32)


def danger_evidence_diagnostics(
    alive: Any,
    genotype: Any,
    cfg: SimulationConfig,
) -> dict[str, Any]:
    active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
    if active.size == 0:
        return {
            "danger_evidence_schema": cfg.entities.danger_evidence_schema,
            "danger_direct_weight_mean": 1.0,
            "danger_direct_weight_std": 0.0,
            "danger_trace_weight_mean": 1.0,
            "danger_trace_weight_std": 0.0,
            "danger_evidence_effective_dimensions": 0.0,
        }
    weights = danger_evidence_quantized(
        np.asarray(genotype, dtype=np.float32)[active], cfg
    ).astype(np.float64) / DANGER_EVIDENCE_SCALE
    centered = weights - weights.mean(axis=0, keepdims=True)
    if active.size > 1 and np.any(centered):
        singular = np.linalg.svd(centered, compute_uv=False)
        spectrum = singular * singular
        effective = float(
            spectrum.sum() ** 2 / max(float(np.dot(spectrum, spectrum)), 1e-30)
        )
    else:
        effective = 0.0
    return {
        "danger_evidence_schema": cfg.entities.danger_evidence_schema,
        "danger_direct_weight_mean": float(weights[:, 0].mean()),
        "danger_direct_weight_std": float(weights[:, 0].std()),
        "danger_trace_weight_mean": float(weights[:, 1].mean()),
        "danger_trace_weight_std": float(weights[:, 1].std()),
        "danger_evidence_effective_dimensions": effective,
    }
