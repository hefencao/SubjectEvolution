"""D2 contextual harvest modules and D2-B contribution diagnostics.

The modules do not choose actions and do not create new world physics. They
only map bounded internal/environmental inputs to a zero-sum residual over the
four already-existing harvest-channel ports. The inherited static affinity
continues to control assimilation and resource-gradient utility.

D2-B adds no new world capability. It exposes the exact per-module signals,
leave-one-module contributions, cancellation, and partial-expression ablation
needed to decide whether the existing fixed modules have causal function before
any duplication or routing expansion is considered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from ..cfg import SimulationConfig
from ..env.niches import AFFINITY_SCALE, RESOURCE_CHANNELS

FUNCTIONAL_MODULE_SCHEMA = "expression-gated-contextual-harvest-v1"
INPUT_SCHEMA = "internal-needs-local-resources-v1"
OUTPUT_SCHEMA = "harvest-channel-zero-sum-residual-v1"
CONTRIBUTION_DIAGNOSTIC_SCHEMA = "functional-module-contribution-audit-v1"
INPUT_COUNT = 10
OUTPUT_COUNT = RESOURCE_CHANNELS
GENES_PER_MODULE = 1 + INPUT_COUNT + 1 + OUTPUT_COUNT
Q = 4096


@dataclass(frozen=True)
class FunctionalModuleEvaluation:
    """Exact D2-A output plus D2-B diagnostic intermediates.

    ``module_residual_q`` contains one independently rounded residual per
    module. The final preference still uses the archived D2-A operation order:
    sum raw routed values first, then round once. Consequently summing the
    independent diagnostic residuals is not used to drive the world.
    """

    preference_q: np.ndarray
    gates_q: np.ndarray
    activation_q: np.ndarray
    signal_q: np.ndarray
    module_residual_q: np.ndarray
    full_residual_q: np.ndarray
    ablation_mask: np.ndarray


def functional_modules_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        cfg.functional_modules.enabled
        and cfg.functional_modules.schema == FUNCTIONAL_MODULE_SCHEMA
    )


def functional_module_gene_count(cfg: SimulationConfig) -> int:
    if not functional_modules_enabled(cfg):
        return 0
    return int(cfg.functional_modules.module_count) * GENES_PER_MODULE


def _blocks(genotype: np.ndarray, cfg: SimulationConfig, gene_start: int):
    values = np.asarray(genotype, dtype=np.float32)
    count = int(cfg.functional_modules.module_count)
    expected = count * GENES_PER_MODULE
    block = values[:, gene_start : gene_start + expected]
    if block.shape != (values.shape[0], expected):
        raise ValueError("genotype does not contain the configured functional modules")
    block = block.reshape(values.shape[0], count, GENES_PER_MODULE)
    gate = block[:, :, 0]
    inputs = block[:, :, 1 : 1 + INPUT_COUNT]
    bias = block[:, :, 1 + INPUT_COUNT]
    outputs = block[:, :, 2 + INPUT_COUNT :]
    return gate, inputs, bias, outputs


def _ablation_mask(
    cfg: SimulationConfig,
    *,
    ablated: bool = False,
    ablated_modules: Any | None = None,
) -> np.ndarray:
    count = int(cfg.functional_modules.module_count)
    if ablated:
        return np.ones(count, dtype=bool)
    if ablated_modules is None:
        return np.zeros(count, dtype=bool)
    mask = np.asarray(ablated_modules, dtype=bool)
    if mask.shape != (count,):
        raise ValueError(f"functional module ablation mask must have shape ({count},)")
    return mask.copy()


def expression_gates_q(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
    ablated: bool = False,
    ablated_modules: Any | None = None,
) -> np.ndarray:
    values = np.asarray(genotype, dtype=np.float32)
    if not functional_modules_enabled(cfg):
        return np.zeros((values.shape[0], 0), dtype=np.int32)
    gate, _, _, _ = _blocks(values, cfg, gene_start)
    threshold = float(cfg.functional_modules.expression_threshold)
    denominator = max(1.0 - threshold, 1e-9)
    expressed = np.clip((gate.astype(np.float64) - threshold) / denominator, 0.0, 1.0)
    result = np.rint(expressed * Q).astype(np.int32)
    mask = _ablation_mask(
        cfg, ablated=ablated, ablated_modules=ablated_modules
    )
    if np.any(mask):
        result[:, mask] = 0
    return result


def contextual_inputs_q(
    *,
    energy: Any,
    integrity: Any,
    material: Any,
    information_store: Any,
    fertility: Any,
    local_resources: Any,
    cfg: SimulationConfig,
) -> np.ndarray:
    local = np.asarray(local_resources, dtype=np.float64)
    if local.ndim != 2 or local.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("local_resources must be shaped [N, 4]")
    rows = local.shape[0]
    capacities = np.asarray(cfg.environment.resource_capacity, dtype=np.float64)
    normalized_local = np.clip(local / capacities[None, :], 0.0, 1.0)
    features = np.column_stack(
        (
            np.ones(rows, dtype=np.float64),
            1.0
            - np.clip(
                np.asarray(energy, dtype=np.float64) / cfg.entities.max_energy,
                0.0,
                1.0,
            ),
            1.0 - np.clip(np.asarray(integrity, dtype=np.float64), 0.0, 1.0),
            1.0 - np.clip(np.asarray(material, dtype=np.float64), 0.0, 1.0),
            1.0
            - np.clip(
                np.asarray(information_store, dtype=np.float64) / 3.0, 0.0, 1.0
            ),
            1.0
            - np.clip(np.asarray(fertility, dtype=np.float64) / 3.0, 0.0, 1.0),
            normalized_local,
        )
    )
    if features.shape != (rows, INPUT_COUNT):
        raise RuntimeError("functional-module input layout drifted")
    return np.rint(features * Q).astype(np.int32)


def _renormalize_fixed_budget(raw: np.ndarray) -> np.ndarray:
    values = np.maximum(np.asarray(raw, dtype=np.int64), 1)
    total = RESOURCE_CHANNELS * AFFINITY_SCALE
    denominator = values.sum(axis=1, dtype=np.int64)
    result = (
        (values * total + denominator[:, None] // 2) // denominator[:, None]
    ).astype(np.int64)
    residual = total - result.sum(axis=1, dtype=np.int64)
    strongest = np.argmax(values, axis=1)
    result[np.arange(result.shape[0]), strongest] += residual
    if np.any(result <= 0) or np.any(result.sum(axis=1) != total):
        raise RuntimeError("functional harvest preference normalization failed")
    return result.astype(np.int32)


def evaluate_contextual_harvest_modules_q(
    genotype: Any,
    base_affinity_q: Any,
    *,
    energy: Any,
    integrity: Any,
    material: Any,
    information_store: Any,
    fertility: Any,
    local_resources: Any,
    cfg: SimulationConfig,
    gene_start: int,
    ablated: bool = False,
    ablated_modules: Any | None = None,
) -> FunctionalModuleEvaluation:
    """Evaluate the unchanged D2-A world output and D2-B intermediates."""

    base = np.asarray(base_affinity_q, dtype=np.int32)
    if base.ndim != 2 or base.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("base affinity must be shaped [N, 4]")
    count = int(cfg.functional_modules.module_count)
    mask = _ablation_mask(
        cfg, ablated=ablated, ablated_modules=ablated_modules
    )
    empty_module = np.zeros((base.shape[0], count), dtype=np.int32)
    empty_residual = np.zeros(
        (base.shape[0], count, RESOURCE_CHANNELS), dtype=np.int32
    )
    if not functional_modules_enabled(cfg) or np.all(mask):
        return FunctionalModuleEvaluation(
            preference_q=base.copy(),
            gates_q=empty_module,
            activation_q=empty_module.copy(),
            signal_q=empty_module.copy(),
            module_residual_q=empty_residual,
            full_residual_q=np.zeros_like(base, dtype=np.int32),
            ablation_mask=mask,
        )

    _, input_gene, bias_gene, output_gene = _blocks(
        np.asarray(genotype, dtype=np.float32), cfg, gene_start
    )
    gates = expression_gates_q(
        genotype,
        cfg,
        gene_start=gene_start,
        ablated_modules=mask,
    ).astype(np.int64)
    features = contextual_inputs_q(
        energy=energy,
        integrity=integrity,
        material=material,
        information_store=information_store,
        fertility=fertility,
        local_resources=local_resources,
        cfg=cfg,
    ).astype(np.int64)
    input_q = np.rint(np.tanh(input_gene.astype(np.float64)) * Q).astype(np.int64)
    bias_q = np.rint(np.tanh(bias_gene.astype(np.float64)) * Q).astype(np.int64)
    activation = (
        np.einsum("ni,nmi->nm", features, input_q, dtype=np.int64) // Q
        + bias_q
    )
    activation = np.clip(activation, -Q, Q)
    signal = (gates * activation) // Q

    output_q = np.rint(np.tanh(output_gene.astype(np.float64)) * Q).astype(np.int64)
    centered4 = 4 * output_q - output_q.sum(
        axis=2, keepdims=True, dtype=np.int64
    )
    routed = (signal[:, :, None] * centered4) // (4 * Q)
    summed = routed.sum(axis=1, dtype=np.int64)
    strength_q = int(
        round(float(cfg.functional_modules.max_residual_fraction) * AFFINITY_SCALE)
    )
    denominator = max(int(cfg.functional_modules.module_count) * 2 * Q, 1)

    # Preserve the D2-A operation order exactly for the authoritative output.
    full_residual = np.rint(
        summed.astype(np.float64) * strength_q / denominator
    ).astype(np.int64)
    full_residual = np.clip(full_residual, -strength_q, strength_q)
    preference = _renormalize_fixed_budget(base.astype(np.int64) + full_residual)

    # Per-module rounding is diagnostic only and never feeds the world.
    module_residual = np.rint(
        routed.astype(np.float64) * strength_q / denominator
    ).astype(np.int64)
    module_residual = np.clip(module_residual, -strength_q, strength_q)
    return FunctionalModuleEvaluation(
        preference_q=preference,
        gates_q=gates.astype(np.int32),
        activation_q=activation.astype(np.int32),
        signal_q=signal.astype(np.int32),
        module_residual_q=module_residual.astype(np.int32),
        full_residual_q=full_residual.astype(np.int32),
        ablation_mask=mask,
    )


def contextual_harvest_preference_q(
    genotype: Any,
    base_affinity_q: Any,
    *,
    energy: Any,
    integrity: Any,
    material: Any,
    information_store: Any,
    fertility: Any,
    local_resources: Any,
    cfg: SimulationConfig,
    gene_start: int,
    ablated: bool = False,
    ablated_modules: Any | None = None,
) -> np.ndarray:
    return evaluate_contextual_harvest_modules_q(
        genotype,
        base_affinity_q,
        energy=energy,
        integrity=integrity,
        material=material,
        information_store=information_store,
        fertility=fertility,
        local_resources=local_resources,
        cfg=cfg,
        gene_start=gene_start,
        ablated=ablated,
        ablated_modules=ablated_modules,
    ).preference_q


def functional_module_energy(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
    development: bool = False,
    ablated: bool = False,
    ablated_modules: Any | None = None,
) -> np.ndarray:
    values = np.asarray(genotype, dtype=np.float32)
    if not functional_modules_enabled(cfg):
        return np.zeros(values.shape[0], dtype=np.float64)
    gates = expression_gates_q(
        values,
        cfg,
        gene_start=gene_start,
        ablated=ablated,
        ablated_modules=ablated_modules,
    ).astype(np.float64) / Q
    rate = (
        cfg.functional_modules.development_energy_per_expression
        if development
        else cfg.functional_modules.maintenance_energy_per_expression
    )
    return gates.sum(axis=1) * float(rate)


def _effective_dimensions(matrix: np.ndarray) -> float:
    values = np.asarray(matrix, dtype=np.float64)
    if values.shape[0] < 2 or values.shape[1] == 0:
        return 0.0
    centered = values - values.mean(axis=0, keepdims=True)
    covariance = centered.T @ centered / max(values.shape[0] - 1, 1)
    eigenvalues = np.clip(np.linalg.eigvalsh(covariance), 0.0, None)
    total = float(eigenvalues.sum())
    squared = float(np.square(eigenvalues).sum())
    return total * total / squared if squared > 0.0 else 0.0


def _effective_count(weights: np.ndarray) -> float:
    values = np.asarray(weights, dtype=np.float64)
    total = float(values.sum())
    if total <= 0.0:
        return 0.0
    share = values / total
    squared = float(np.square(share).sum())
    return 1.0 / squared if squared > 0.0 else 0.0


def functional_module_diagnostics(
    genotype: Any,
    contextual_preference_q: Any,
    base_affinity_q: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
    evaluation: FunctionalModuleEvaluation | None = None,
) -> dict[str, Any]:
    values = np.asarray(genotype, dtype=np.float32)
    preference = np.asarray(contextual_preference_q, dtype=np.float64)
    base = np.asarray(base_affinity_q, dtype=np.float64)
    if preference.shape != base.shape:
        raise ValueError(
            "contextual preference and base affinity must have matching shapes"
        )
    count = int(cfg.functional_modules.module_count)
    zero_by_module = [0.0] * count
    if not functional_modules_enabled(cfg) or values.shape[0] == 0:
        return {
            "functional_module_schema": cfg.functional_modules.schema,
            "functional_module_contribution_diagnostic_schema": (
                CONTRIBUTION_DIAGNOSTIC_SCHEMA
            ),
            "functional_module_active_entities": int(values.shape[0]),
            "functional_module_expressed_mean": 0.0,
            "functional_module_expressed_fraction": 0.0,
            "functional_module_gate_effective_dimensions": 0.0,
            "functional_harvest_preference_effective_dimensions": 0.0,
            "functional_module_residual_effective_dimensions": 0.0,
            "functional_module_residual_abs_mean": 0.0,
            "functional_module_residual_abs_max": 0.0,
            "functional_module_changed_entity_fraction": 0.0,
            "functional_module_input_weight_effective_dimensions": 0.0,
            "functional_module_output_router_effective_dimensions": 0.0,
            "functional_module_dominant_input_counts": [0] * INPUT_COUNT,
            "functional_module_dominant_output_counts": [0] * OUTPUT_COUNT,
            "functional_module_ablation_mask": [False] * count,
            "functional_module_gate_mean_by_module": zero_by_module,
            "functional_module_expressed_fraction_by_module": zero_by_module,
            "functional_module_activation_abs_mean_by_module": zero_by_module,
            "functional_module_signal_abs_mean_by_module": zero_by_module,
            "functional_module_isolated_residual_abs_mean_by_module": zero_by_module,
            "functional_module_nonzero_entity_fraction_by_module": zero_by_module,
            "functional_module_silent_expressed_fraction_by_module": zero_by_module,
            "functional_module_contribution_share": zero_by_module,
            "functional_module_contribution_effective_count": 0.0,
            "functional_module_contribution_dominance": 0.0,
            "functional_module_cancellation_fraction": 0.0,
        }
    _, input_gene, _, output_gene = _blocks(values, cfg, gene_start)
    if evaluation is None:
        gates_q = expression_gates_q(values, cfg, gene_start=gene_start)
        evaluation = FunctionalModuleEvaluation(
            preference_q=np.asarray(contextual_preference_q, dtype=np.int32),
            gates_q=gates_q,
            activation_q=np.zeros_like(gates_q),
            signal_q=np.zeros_like(gates_q),
            module_residual_q=np.zeros(
                (values.shape[0], count, RESOURCE_CHANNELS), dtype=np.int32
            ),
            full_residual_q=np.asarray(
                contextual_preference_q, dtype=np.int32
            )
            - np.asarray(base_affinity_q, dtype=np.int32),
            ablation_mask=np.zeros(count, dtype=bool),
        )
    gates = evaluation.gates_q.astype(np.float64) / Q
    expressed = gates > 0.0
    shares = preference / preference.sum(axis=1, keepdims=True)
    base_shares = base / base.sum(axis=1, keepdims=True)
    residual_shares = shares - base_shares
    residual_abs = np.abs(residual_shares)
    expressed_inputs = np.tanh(input_gene.astype(np.float64))[expressed]
    expressed_outputs = np.tanh(output_gene.astype(np.float64))[expressed]
    if expressed_inputs.size:
        dominant_inputs = np.bincount(
            np.argmax(np.abs(expressed_inputs), axis=1), minlength=INPUT_COUNT
        )
        centered_outputs = expressed_outputs - expressed_outputs.mean(
            axis=1, keepdims=True
        )
        dominant_outputs = np.bincount(
            np.argmax(centered_outputs, axis=1), minlength=OUTPUT_COUNT
        )
        input_dimensions = _effective_dimensions(expressed_inputs)
        output_dimensions = _effective_dimensions(centered_outputs)
    else:
        dominant_inputs = np.zeros(INPUT_COUNT, dtype=np.int64)
        dominant_outputs = np.zeros(OUTPUT_COUNT, dtype=np.int64)
        input_dimensions = 0.0
        output_dimensions = 0.0

    module_residual = np.asarray(evaluation.module_residual_q, dtype=np.int64)
    isolated_abs_mean = np.zeros(count, dtype=np.float64)
    nonzero_fraction = np.zeros(count, dtype=np.float64)
    silent_fraction = np.zeros(count, dtype=np.float64)
    contribution_magnitude = np.zeros(count, dtype=np.float64)
    for module_index in range(count):
        isolated = _renormalize_fixed_budget(
            base.astype(np.int64) + module_residual[:, module_index, :]
        ).astype(np.float64)
        isolated_share = isolated / isolated.sum(axis=1, keepdims=True)
        isolated_delta = isolated_share - base_shares
        isolated_abs_mean[module_index] = float(np.abs(isolated_delta).mean())
        changed = np.any(isolated != base, axis=1)
        nonzero_fraction[module_index] = float(changed.mean())
        expressed_module = expressed[:, module_index]
        expressed_count = int(np.count_nonzero(expressed_module))
        if expressed_count:
            silent_fraction[module_index] = float(
                np.count_nonzero(expressed_module & ~changed) / expressed_count
            )
        contribution_magnitude[module_index] = float(np.abs(isolated_delta).sum())

    contribution_total = float(contribution_magnitude.sum())
    contribution_share = (
        contribution_magnitude / contribution_total
        if contribution_total > 0.0
        else np.zeros(count, dtype=np.float64)
    )
    raw_individual_abs = float(np.abs(module_residual).sum())
    raw_combined_abs = float(np.abs(module_residual.sum(axis=1)).sum())
    cancellation = (
        1.0 - raw_combined_abs / raw_individual_abs
        if raw_individual_abs > 0.0
        else 0.0
    )
    return {
        "functional_module_schema": cfg.functional_modules.schema,
        "functional_module_contribution_diagnostic_schema": (
            CONTRIBUTION_DIAGNOSTIC_SCHEMA
        ),
        "functional_module_active_entities": int(values.shape[0]),
        "functional_module_expressed_mean": float(expressed.sum(axis=1).mean()),
        "functional_module_expressed_fraction": float(expressed.mean()),
        "functional_module_gate_mean": float(gates.mean()),
        "functional_module_gate_std": float(gates.std()),
        "functional_module_gate_effective_dimensions": _effective_dimensions(gates),
        "functional_harvest_preference_effective_dimensions": _effective_dimensions(
            shares
        ),
        "functional_harvest_preference_mean": shares.mean(axis=0).tolist(),
        "functional_harvest_preference_std": shares.std(axis=0).tolist(),
        "functional_module_residual_effective_dimensions": _effective_dimensions(
            residual_shares
        ),
        "functional_module_residual_abs_mean": float(residual_abs.mean()),
        "functional_module_residual_abs_max": float(residual_abs.max()),
        "functional_module_changed_entity_fraction": float(
            np.any(preference != base, axis=1).mean()
        ),
        "functional_module_input_weight_effective_dimensions": float(
            input_dimensions
        ),
        "functional_module_output_router_effective_dimensions": float(
            output_dimensions
        ),
        "functional_module_dominant_input_counts": dominant_inputs.tolist(),
        "functional_module_dominant_output_counts": dominant_outputs.tolist(),
        "functional_module_ablation_mask": evaluation.ablation_mask.astype(bool).tolist(),
        "functional_module_gate_mean_by_module": gates.mean(axis=0).tolist(),
        "functional_module_expressed_fraction_by_module": expressed.mean(axis=0).tolist(),
        "functional_module_activation_abs_mean_by_module": (
            np.abs(evaluation.activation_q.astype(np.float64) / Q)
            .mean(axis=0)
            .tolist()
        ),
        "functional_module_signal_abs_mean_by_module": (
            np.abs(evaluation.signal_q.astype(np.float64) / Q).mean(axis=0).tolist()
        ),
        "functional_module_isolated_residual_abs_mean_by_module": (
            isolated_abs_mean.tolist()
        ),
        "functional_module_nonzero_entity_fraction_by_module": (
            nonzero_fraction.tolist()
        ),
        "functional_module_silent_expressed_fraction_by_module": (
            silent_fraction.tolist()
        ),
        "functional_module_contribution_share": contribution_share.tolist(),
        "functional_module_contribution_effective_count": float(
            _effective_count(contribution_magnitude)
        ),
        "functional_module_contribution_dominance": float(
            contribution_share.max() if contribution_share.size else 0.0
        ),
        "functional_module_cancellation_fraction": float(
            np.clip(cancellation, 0.0, 1.0)
        ),
    }


__all__ = [
    "CONTRIBUTION_DIAGNOSTIC_SCHEMA",
    "FUNCTIONAL_MODULE_SCHEMA",
    "FunctionalModuleEvaluation",
    "GENES_PER_MODULE",
    "INPUT_COUNT",
    "INPUT_SCHEMA",
    "OUTPUT_SCHEMA",
    "contextual_harvest_preference_q",
    "evaluate_contextual_harvest_modules_q",
    "expression_gates_q",
    "functional_module_diagnostics",
    "functional_module_energy",
    "functional_module_gene_count",
    "functional_modules_enabled",
]
