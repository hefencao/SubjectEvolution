"""Bounded contextual, compositional, and embodied functional modules.

The archived v1 architecture maps each fixed slot independently from bounded
internal/environmental inputs to a zero-sum residual over the four harvest
ports.  The opt-in v2 architecture adds six inherited lower-slot-to-higher-slot
signal couplings while retaining that single output vocabulary.

The v3 architecture keeps the same fixed four-slot acyclic signal graph but
adds three versioned embodied output primitives: locomotion power, field-signal
power, and material-to-integrity repair drive.  These are existing or explicit
world interfaces with conservation/cost semantics, not named ecological roles.
The extension lets one inherited module combination control several physically
different consequences instead of only rearranging one harvest preference
vector.  Embodied output can be neutralized while genes, coupling, expression,
and structural costs remain present.

The archived opt-in v4 architecture moves these high-level effects below the
module boundary with four coarse body drives.  The v5 architecture replaces
those coarse drives with neural/regulatory requests: oxygen-uptake stimulation,
a mobilization-bus drive, a maintenance-bus drive, and sensory attention.
Actual locomotion, sensing, signaling, fatigue clearance, and repair are then
computed by the inherited physiology substrate and local abiotic conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from ..cfg import SimulationConfig
from ..env.niches import AFFINITY_SCALE, RESOURCE_CHANNELS

FUNCTIONAL_MODULE_SCHEMA = "expression-gated-contextual-harvest-v1"
COMPOSITIONAL_FUNCTIONAL_MODULE_SCHEMA = (
    "expression-gated-compositional-harvest-v2"
)
EMBODIED_FUNCTIONAL_MODULE_SCHEMA = (
    "expression-gated-compositional-embodied-v3"
)
PHYSIOLOGICAL_FUNCTIONAL_MODULE_SCHEMA = (
    "expression-gated-compositional-physiological-v4"
)
REGULATORY_FUNCTIONAL_MODULE_SCHEMA = (
    "expression-gated-regulatory-physiology-v5"
)
INPUT_SCHEMA = "internal-needs-local-resources-v1"
COMPOSITIONAL_INPUT_SCHEMA = "internal-needs-local-resources-feedforward-v2"
PHYSIOLOGICAL_INPUT_SCHEMA = (
    "internal-physiology-local-resources-abiotic-feedforward-v3"
)
REGULATORY_INPUT_SCHEMA = (
    "internal-homeostasis-local-resources-abiotic-feedforward-v4"
)
OUTPUT_SCHEMA = "harvest-channel-zero-sum-residual-v1"
EMBODIED_OUTPUT_SCHEMA = "harvest-locomotion-signal-repair-v1"
PHYSIOLOGICAL_OUTPUT_SCHEMA = "harvest-physiology-drive-v1"
REGULATORY_OUTPUT_SCHEMA = "harvest-regulatory-drive-v2"
COUPLING_SCHEMA = "lower-slot-signal-modulation-v1"
CONTRIBUTION_DIAGNOSTIC_SCHEMA = "functional-module-contribution-audit-v2"
EMBODIED_CONTRIBUTION_DIAGNOSTIC_SCHEMA = "functional-module-contribution-audit-v3"
PHYSIOLOGICAL_CONTRIBUTION_DIAGNOSTIC_SCHEMA = (
    "functional-module-contribution-audit-v4"
)
REGULATORY_CONTRIBUTION_DIAGNOSTIC_SCHEMA = (
    "functional-module-contribution-audit-v5"
)
INPUT_COUNT = 10
PHYSIOLOGICAL_INPUT_COUNT = 16
REGULATORY_INPUT_COUNT = 20
OUTPUT_COUNT = RESOURCE_CHANNELS
EMBODIED_OUTPUT_NAMES = ("locomotion_power", "signal_power", "repair_drive")
EMBODIED_OUTPUT_COUNT = len(EMBODIED_OUTPUT_NAMES)
PHYSIOLOGICAL_OUTPUT_NAMES = (
    "perfusion_drive",
    "contractile_drive",
    "sensory_drive",
    "repair_drive",
)
REGULATORY_OUTPUT_NAMES = (
    "oxygen_uptake_drive",
    "mobilization_drive",
    "maintenance_drive",
    "sensory_attention_drive",
)
PHYSIOLOGICAL_OUTPUT_COUNT = len(PHYSIOLOGICAL_OUTPUT_NAMES)
REGULATORY_OUTPUT_COUNT = len(REGULATORY_OUTPUT_NAMES)
# Historical constant retained for readers/tests of the v1/v2 layout.
GENES_PER_MODULE = 1 + INPUT_COUNT + 1 + OUTPUT_COUNT
EMBODIED_GENES_PER_MODULE = GENES_PER_MODULE + EMBODIED_OUTPUT_COUNT
PHYSIOLOGICAL_GENES_PER_MODULE = (
    1 + PHYSIOLOGICAL_INPUT_COUNT + 1 + OUTPUT_COUNT + PHYSIOLOGICAL_OUTPUT_COUNT
)
REGULATORY_GENES_PER_MODULE = (
    1 + REGULATORY_INPUT_COUNT + 1 + OUTPUT_COUNT + REGULATORY_OUTPUT_COUNT
)
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
    context_activation_q: np.ndarray | None = None
    modulation_q: np.ndarray | None = None
    coupling_q: np.ndarray | None = None
    coupling_ablation_enabled: bool = False
    embodied_output_q: np.ndarray | None = None
    module_embodied_output_q: np.ndarray | None = None
    embodied_output_ablation_enabled: bool = False
    physiology_output_q: np.ndarray | None = None
    module_physiology_output_q: np.ndarray | None = None
    physiology_output_ablation_enabled: bool = False
    computation_load: np.ndarray | None = None


def functional_modules_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        cfg.functional_modules.enabled
        and cfg.functional_modules.schema
        in {
            FUNCTIONAL_MODULE_SCHEMA,
            COMPOSITIONAL_FUNCTIONAL_MODULE_SCHEMA,
            EMBODIED_FUNCTIONAL_MODULE_SCHEMA,
            PHYSIOLOGICAL_FUNCTIONAL_MODULE_SCHEMA,
            REGULATORY_FUNCTIONAL_MODULE_SCHEMA,
        }
    )


def compositional_modules_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        functional_modules_enabled(cfg)
        and cfg.functional_modules.schema
        in {
            COMPOSITIONAL_FUNCTIONAL_MODULE_SCHEMA,
            EMBODIED_FUNCTIONAL_MODULE_SCHEMA,
            PHYSIOLOGICAL_FUNCTIONAL_MODULE_SCHEMA,
            REGULATORY_FUNCTIONAL_MODULE_SCHEMA,
        }
        and cfg.functional_modules.coupling_schema == COUPLING_SCHEMA
    )



def embodied_outputs_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        compositional_modules_enabled(cfg)
        and cfg.functional_modules.schema == EMBODIED_FUNCTIONAL_MODULE_SCHEMA
        and cfg.functional_modules.output_schema == EMBODIED_OUTPUT_SCHEMA
    )


def physiological_outputs_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        compositional_modules_enabled(cfg)
        and cfg.functional_modules.schema == PHYSIOLOGICAL_FUNCTIONAL_MODULE_SCHEMA
        and cfg.functional_modules.output_schema == PHYSIOLOGICAL_OUTPUT_SCHEMA
        and cfg.physiology.enabled
    )


def regulatory_outputs_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        compositional_modules_enabled(cfg)
        and cfg.functional_modules.schema == REGULATORY_FUNCTIONAL_MODULE_SCHEMA
        and cfg.functional_modules.output_schema == REGULATORY_OUTPUT_SCHEMA
        and cfg.physiology.enabled
    )


def functional_module_input_count(cfg: SimulationConfig) -> int:
    if regulatory_outputs_enabled(cfg):
        return REGULATORY_INPUT_COUNT
    return PHYSIOLOGICAL_INPUT_COUNT if physiological_outputs_enabled(cfg) else INPUT_COUNT


def functional_module_auxiliary_output_count(cfg: SimulationConfig) -> int:
    if regulatory_outputs_enabled(cfg):
        return REGULATORY_OUTPUT_COUNT
    if physiological_outputs_enabled(cfg):
        return PHYSIOLOGICAL_OUTPUT_COUNT
    if embodied_outputs_enabled(cfg):
        return EMBODIED_OUTPUT_COUNT
    return 0


def functional_module_genes_per_module(cfg: SimulationConfig) -> int:
    if regulatory_outputs_enabled(cfg):
        return REGULATORY_GENES_PER_MODULE
    if physiological_outputs_enabled(cfg):
        return PHYSIOLOGICAL_GENES_PER_MODULE
    return EMBODIED_GENES_PER_MODULE if embodied_outputs_enabled(cfg) else GENES_PER_MODULE


def functional_module_coupling_count(cfg: SimulationConfig) -> int:
    if not compositional_modules_enabled(cfg):
        return 0
    count = int(cfg.functional_modules.module_count)
    return count * (count - 1) // 2


def functional_module_gene_count(cfg: SimulationConfig) -> int:
    if not functional_modules_enabled(cfg):
        return 0
    return (
        int(cfg.functional_modules.module_count) * functional_module_genes_per_module(cfg)
        + functional_module_coupling_count(cfg)
    )


def _blocks(genotype: np.ndarray, cfg: SimulationConfig, gene_start: int):
    values = np.asarray(genotype, dtype=np.float32)
    count = int(cfg.functional_modules.module_count)
    genes_per_module = functional_module_genes_per_module(cfg)
    input_count = functional_module_input_count(cfg)
    auxiliary_count = functional_module_auxiliary_output_count(cfg)
    base_count = count * genes_per_module
    expected = base_count + functional_module_coupling_count(cfg)
    block = values[:, gene_start : gene_start + expected]
    if block.shape != (values.shape[0], expected):
        raise ValueError("genotype does not contain the configured functional modules")
    modules = block[:, :base_count].reshape(values.shape[0], count, genes_per_module)
    gate = modules[:, :, 0]
    inputs = modules[:, :, 1 : 1 + input_count]
    bias = modules[:, :, 1 + input_count]
    output_start = 2 + input_count
    harvest_outputs = modules[:, :, output_start : output_start + OUTPUT_COUNT]
    auxiliary_outputs = np.zeros(
        (values.shape[0], count, auxiliary_count), dtype=np.float32
    )
    if auxiliary_count:
        auxiliary_outputs = modules[
            :,
            :,
            output_start + OUTPUT_COUNT : output_start + OUTPUT_COUNT + auxiliary_count,
        ]
    coupling = np.zeros((values.shape[0], count, count), dtype=np.float32)
    if compositional_modules_enabled(cfg):
        cursor = base_count
        for target in range(1, count):
            width = target
            coupling[:, target, :target] = block[:, cursor : cursor + width]
            cursor += width
        if cursor != expected:
            raise RuntimeError("functional module coupling layout drifted")
    return gate, inputs, bias, harvest_outputs, auxiliary_outputs, coupling


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


def _row_ablation_mask(
    rows: int,
    count: int,
    row_ablated_modules: Any | None,
) -> np.ndarray | None:
    if row_ablated_modules is None:
        return None
    mask = np.asarray(row_ablated_modules, dtype=bool)
    if mask.shape != (rows, count):
        raise ValueError(
            "functional module row ablation mask must have shape "
            f"({rows}, {count})"
        )
    return mask.copy()


def expression_gates_q(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
    ablated: bool = False,
    ablated_modules: Any | None = None,
    row_ablated_modules: Any | None = None,
) -> np.ndarray:
    values = np.asarray(genotype, dtype=np.float32)
    if not functional_modules_enabled(cfg):
        return np.zeros((values.shape[0], 0), dtype=np.int32)
    gate, _, _, _, _, _ = _blocks(values, cfg, gene_start)
    threshold = float(cfg.functional_modules.expression_threshold)
    denominator = max(1.0 - threshold, 1e-9)
    expressed = np.clip((gate.astype(np.float64) - threshold) / denominator, 0.0, 1.0)
    result = np.rint(expressed * Q).astype(np.int32)
    mask = _ablation_mask(
        cfg, ablated=ablated, ablated_modules=ablated_modules
    )
    row_mask = _row_ablation_mask(values.shape[0], result.shape[1], row_ablated_modules)
    if np.any(mask):
        result[:, mask] = 0
    if row_mask is not None and np.any(row_mask):
        result[row_mask] = 0
    return result


def contextual_inputs_q(
    *,
    energy: Any,
    integrity: Any,
    material: Any,
    information_store: Any,
    fertility: Any,
    local_resources: Any,
    oxygenation: Any | None = None,
    tissue_condition: Any | None = None,
    structure_condition: Any | None = None,
    metabolic_fatigue: Any | None = None,
    mobilization_messenger: Any | None = None,
    maintenance_messenger: Any | None = None,
    messenger_precursor: Any | None = None,
    local_oxygen: Any | None = None,
    local_terrain: Any | None = None,
    local_wear: Any | None = None,
    cfg: SimulationConfig,
) -> np.ndarray:
    local = np.asarray(local_resources, dtype=np.float64)
    if local.ndim != 2 or local.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("local_resources must be shaped [N, 4]")
    rows = local.shape[0]
    capacities = np.asarray(cfg.environment.resource_capacity, dtype=np.float64)
    normalized_local = np.clip(local / capacities[None, :], 0.0, 1.0)
    base_features = np.column_stack(
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
    if base_features.shape != (rows, INPUT_COUNT):
        raise RuntimeError("functional-module input layout drifted")
    if physiological_outputs_enabled(cfg) or regulatory_outputs_enabled(cfg):
        required = (
            oxygenation,
            tissue_condition,
            structure_condition,
            local_oxygen,
            local_terrain,
            local_wear,
        )
        if regulatory_outputs_enabled(cfg):
            required = required + (
                metabolic_fatigue,
                mobilization_messenger,
                maintenance_messenger,
                messenger_precursor,
            )
        if any(value is None for value in required):
            version = "v5 regulatory" if regulatory_outputs_enabled(cfg) else "v4 physiological"
            raise ValueError(f"{version} modules require body and abiotic inputs")
        body_features = [
            1.0 - np.clip(np.asarray(oxygenation, dtype=np.float64), 0.0, 1.0),
            1.0 - np.clip(np.asarray(tissue_condition, dtype=np.float64), 0.0, 1.0),
            1.0 - np.clip(np.asarray(structure_condition, dtype=np.float64), 0.0, 1.0),
        ]
        if regulatory_outputs_enabled(cfg):
            body_features.extend(
                [
                    np.clip(np.asarray(metabolic_fatigue, dtype=np.float64), 0.0, 1.0),
                    np.clip(np.asarray(mobilization_messenger, dtype=np.float64), 0.0, 1.0),
                    np.clip(np.asarray(maintenance_messenger, dtype=np.float64), 0.0, 1.0),
                    np.clip(np.asarray(messenger_precursor, dtype=np.float64), 0.0, 1.0),
                ]
            )
        body_features.extend(
            [
                np.clip(np.asarray(local_oxygen, dtype=np.float64), 0.0, 1.0),
                np.clip(np.asarray(local_terrain, dtype=np.float64), 0.0, 1.0),
                np.clip(np.asarray(local_wear, dtype=np.float64), 0.0, 1.0),
            ]
        )
        physiology_features = np.column_stack(body_features)
        features = np.concatenate((base_features, physiology_features), axis=1)
    else:
        features = base_features
    expected = functional_module_input_count(cfg)
    if features.shape != (rows, expected):
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
    oxygenation: Any | None = None,
    tissue_condition: Any | None = None,
    structure_condition: Any | None = None,
    metabolic_fatigue: Any | None = None,
    mobilization_messenger: Any | None = None,
    maintenance_messenger: Any | None = None,
    messenger_precursor: Any | None = None,
    local_oxygen: Any | None = None,
    local_terrain: Any | None = None,
    local_wear: Any | None = None,
    cfg: SimulationConfig,
    gene_start: int,
    ablated: bool = False,
    ablated_modules: Any | None = None,
    row_ablated_modules: Any | None = None,
    coupling_ablated: bool = False,
    embodied_ablated: bool = False,
    physiology_ablated: bool = False,
) -> FunctionalModuleEvaluation:
    """Evaluate additive or feed-forward compositional module output."""

    base = np.asarray(base_affinity_q, dtype=np.int32)
    if base.ndim != 2 or base.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("base affinity must be shaped [N, 4]")
    count = int(cfg.functional_modules.module_count)
    mask = _ablation_mask(
        cfg, ablated=ablated, ablated_modules=ablated_modules
    )
    row_mask = _row_ablation_mask(base.shape[0], count, row_ablated_modules)
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
            context_activation_q=empty_module.copy(),
            modulation_q=empty_module.copy(),
            coupling_q=np.zeros((base.shape[0], count, count), dtype=np.int32),
            coupling_ablation_enabled=bool(coupling_ablated),
            embodied_output_q=np.zeros(
                (base.shape[0], EMBODIED_OUTPUT_COUNT), dtype=np.int32
            ),
            module_embodied_output_q=np.zeros(
                (base.shape[0], count, EMBODIED_OUTPUT_COUNT), dtype=np.int32
            ),
            embodied_output_ablation_enabled=bool(embodied_ablated),
            physiology_output_q=np.zeros(
                (base.shape[0], PHYSIOLOGICAL_OUTPUT_COUNT), dtype=np.int32
            ),
            module_physiology_output_q=np.zeros(
                (base.shape[0], count, PHYSIOLOGICAL_OUTPUT_COUNT), dtype=np.int32
            ),
            physiology_output_ablation_enabled=bool(physiology_ablated),
        )

    (
        _,
        input_gene,
        bias_gene,
        output_gene,
        auxiliary_output_gene,
        coupling_gene,
    ) = _blocks(np.asarray(genotype, dtype=np.float32), cfg, gene_start)
    gates = expression_gates_q(
        genotype,
        cfg,
        gene_start=gene_start,
        ablated_modules=mask,
        row_ablated_modules=row_mask,
    ).astype(np.int64)
    features = contextual_inputs_q(
        energy=energy,
        integrity=integrity,
        material=material,
        information_store=information_store,
        fertility=fertility,
        local_resources=local_resources,
        oxygenation=oxygenation,
        tissue_condition=tissue_condition,
        structure_condition=structure_condition,
        metabolic_fatigue=metabolic_fatigue,
        mobilization_messenger=mobilization_messenger,
        maintenance_messenger=maintenance_messenger,
        messenger_precursor=messenger_precursor,
        local_oxygen=local_oxygen,
        local_terrain=local_terrain,
        local_wear=local_wear,
        cfg=cfg,
    ).astype(np.int64)
    input_q = np.rint(np.tanh(input_gene.astype(np.float64)) * Q).astype(np.int64)
    bias_q = np.rint(np.tanh(bias_gene.astype(np.float64)) * Q).astype(np.int64)
    context_activation = (
        np.einsum("ni,nmi->nm", features, input_q, dtype=np.int64) // Q
        + bias_q
    )
    context_activation = np.clip(context_activation, -Q, Q)
    activation = context_activation.copy()
    signal = np.zeros_like(activation, dtype=np.int64)
    coupling_q = np.rint(
        np.tanh(coupling_gene.astype(np.float64)) * Q
    ).astype(np.int64)
    modulation = np.zeros_like(activation, dtype=np.int64)
    use_coupling = compositional_modules_enabled(cfg) and not coupling_ablated
    for module_index in range(count):
        if use_coupling and module_index > 0:
            upstream = (
                coupling_q[:, module_index, :module_index]
                * signal[:, :module_index]
            ).sum(axis=1, dtype=np.int64) // Q
            modulation[:, module_index] = np.clip(upstream, -Q, Q)
            scale_q = np.clip(Q + modulation[:, module_index], 0, 2 * Q)
            activation[:, module_index] = np.clip(
                (context_activation[:, module_index] * scale_q) // Q,
                -Q,
                Q,
            )
        signal[:, module_index] = (
            gates[:, module_index] * activation[:, module_index]
        ) // Q

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

    module_embodied = np.zeros(
        (base.shape[0], count, EMBODIED_OUTPUT_COUNT), dtype=np.int64
    )
    embodied_output = np.zeros(
        (base.shape[0], EMBODIED_OUTPUT_COUNT), dtype=np.int64
    )
    if embodied_outputs_enabled(cfg) and not embodied_ablated:
        embodied_router_q = np.rint(
            np.tanh(auxiliary_output_gene.astype(np.float64)) * Q
        ).astype(np.int64)
        module_embodied = (signal[:, :, None] * embodied_router_q) // Q
        embodied_output = np.rint(
            module_embodied.sum(axis=1, dtype=np.int64).astype(np.float64)
            / max(count, 1)
        ).astype(np.int64)
        embodied_output = np.clip(embodied_output, -Q, Q)

    module_physiology = np.zeros(
        (base.shape[0], count, PHYSIOLOGICAL_OUTPUT_COUNT), dtype=np.int64
    )
    physiology_output = np.zeros(
        (base.shape[0], PHYSIOLOGICAL_OUTPUT_COUNT), dtype=np.int64
    )
    if (physiological_outputs_enabled(cfg) or regulatory_outputs_enabled(cfg)) and not physiology_ablated:
        physiology_router_q = np.rint(
            np.tanh(auxiliary_output_gene.astype(np.float64)) * Q
        ).astype(np.int64)
        module_physiology = (signal[:, :, None] * physiology_router_q) // Q
        physiology_output = np.rint(
            module_physiology.sum(axis=1, dtype=np.int64).astype(np.float64)
            / max(count, 1)
        ).astype(np.int64)
        physiology_output = np.clip(physiology_output, -Q, Q)

    signal_load = np.mean(
        np.abs(signal.astype(np.float64)) / Q, axis=1
    )
    input_load = np.mean(
        np.abs(np.tanh(input_gene.astype(np.float64))), axis=(1, 2)
    )
    harvest_router_load = np.mean(
        np.abs(np.tanh(output_gene.astype(np.float64))), axis=(1, 2)
    )
    auxiliary_router_load = (
        np.mean(
            np.abs(np.tanh(auxiliary_output_gene.astype(np.float64))),
            axis=(1, 2),
        )
        if auxiliary_output_gene.shape[2]
        else np.zeros(base.shape[0], dtype=np.float64)
    )
    coupling_load = (
        np.mean(
            np.abs(np.tanh(coupling_gene.astype(np.float64))), axis=(1, 2)
        )
        if compositional_modules_enabled(cfg)
        else np.zeros(base.shape[0], dtype=np.float64)
    )
    computation_load = signal_load * (
        1.0 + input_load + harvest_router_load + auxiliary_router_load + coupling_load
    )

    return FunctionalModuleEvaluation(
        preference_q=preference,
        gates_q=gates.astype(np.int32),
        activation_q=activation.astype(np.int32),
        signal_q=signal.astype(np.int32),
        module_residual_q=module_residual.astype(np.int32),
        full_residual_q=full_residual.astype(np.int32),
        ablation_mask=mask,
        context_activation_q=context_activation.astype(np.int32),
        modulation_q=modulation.astype(np.int32),
        coupling_q=coupling_q.astype(np.int32),
        coupling_ablation_enabled=bool(coupling_ablated),
        embodied_output_q=embodied_output.astype(np.int32),
        module_embodied_output_q=module_embodied.astype(np.int32),
        embodied_output_ablation_enabled=bool(embodied_ablated),
        physiology_output_q=physiology_output.astype(np.int32),
        module_physiology_output_q=module_physiology.astype(np.int32),
        physiology_output_ablation_enabled=bool(physiology_ablated),
        computation_load=computation_load.astype(np.float32),
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
    oxygenation: Any | None = None,
    tissue_condition: Any | None = None,
    structure_condition: Any | None = None,
    metabolic_fatigue: Any | None = None,
    mobilization_messenger: Any | None = None,
    maintenance_messenger: Any | None = None,
    messenger_precursor: Any | None = None,
    local_oxygen: Any | None = None,
    local_terrain: Any | None = None,
    local_wear: Any | None = None,
    cfg: SimulationConfig,
    gene_start: int,
    ablated: bool = False,
    ablated_modules: Any | None = None,
    row_ablated_modules: Any | None = None,
    coupling_ablated: bool = False,
    embodied_ablated: bool = False,
    physiology_ablated: bool = False,
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
        oxygenation=oxygenation,
        tissue_condition=tissue_condition,
        structure_condition=structure_condition,
        metabolic_fatigue=metabolic_fatigue,
        mobilization_messenger=mobilization_messenger,
        maintenance_messenger=maintenance_messenger,
        messenger_precursor=messenger_precursor,
        local_oxygen=local_oxygen,
        local_terrain=local_terrain,
        local_wear=local_wear,
        cfg=cfg,
        gene_start=gene_start,
        ablated=ablated,
        ablated_modules=ablated_modules,
        row_ablated_modules=row_ablated_modules,
        coupling_ablated=coupling_ablated,
        embodied_ablated=embodied_ablated,
        physiology_ablated=physiology_ablated,
    ).preference_q


def functional_module_energy(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
    development: bool = False,
    ablated: bool = False,
    ablated_modules: Any | None = None,
    row_ablated_modules: Any | None = None,
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
        row_ablated_modules=row_ablated_modules,
    ).astype(np.float64) / Q
    expression_rate = (
        cfg.functional_modules.development_energy_per_expression
        if development
        else cfg.functional_modules.maintenance_energy_per_expression
    )
    energy = gates.sum(axis=1) * float(expression_rate)
    if compositional_modules_enabled(cfg):
        _, _, _, _, auxiliary_output_gene, coupling_gene = _blocks(
            values, cfg, gene_start
        )
        coupling_strength = np.abs(
            np.tanh(coupling_gene.astype(np.float64))
        )
        target_gate = gates[:, :, None]
        active_weight = coupling_strength * target_gate
        coupling_rate = (
            cfg.functional_modules.development_energy_per_coupling_weight
            if development
            else cfg.functional_modules.maintenance_energy_per_coupling_weight
        )
        energy = energy + active_weight.sum(axis=(1, 2)) * float(coupling_rate)
    if embodied_outputs_enabled(cfg):
        if "auxiliary_output_gene" not in locals():
            _, _, _, _, auxiliary_output_gene, _ = _blocks(values, cfg, gene_start)
        router_strength = np.abs(np.tanh(auxiliary_output_gene.astype(np.float64)))
        active_router = router_strength * gates[:, :, None]
        embodied_rate = (
            cfg.functional_modules.development_energy_per_embodied_weight
            if development
            else cfg.functional_modules.maintenance_energy_per_embodied_weight
        )
        energy = energy + active_router.sum(axis=(1, 2)) * float(embodied_rate)
    if physiological_outputs_enabled(cfg) or regulatory_outputs_enabled(cfg):
        if "auxiliary_output_gene" not in locals():
            _, _, _, _, auxiliary_output_gene, _ = _blocks(values, cfg, gene_start)
        router_strength = np.abs(np.tanh(auxiliary_output_gene.astype(np.float64)))
        active_router = router_strength * gates[:, :, None]
        physiology_rate = (
            cfg.functional_modules.development_energy_per_physiology_weight
            if development
            else cfg.functional_modules.maintenance_energy_per_physiology_weight
        )
        energy = energy + active_router.sum(axis=(1, 2)) * float(physiology_rate)
    return energy


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
    input_count = functional_module_input_count(cfg)
    auxiliary_names = (
        REGULATORY_OUTPUT_NAMES
        if regulatory_outputs_enabled(cfg)
        else PHYSIOLOGICAL_OUTPUT_NAMES
        if physiological_outputs_enabled(cfg)
        else EMBODIED_OUTPUT_NAMES
    )
    auxiliary_count = len(auxiliary_names)
    zero_by_module = [0.0] * count
    if not functional_modules_enabled(cfg) or values.shape[0] == 0:
        return {
            "functional_module_schema": cfg.functional_modules.schema,
            "functional_module_contribution_diagnostic_schema": (
                REGULATORY_CONTRIBUTION_DIAGNOSTIC_SCHEMA
                if regulatory_outputs_enabled(cfg)
                else PHYSIOLOGICAL_CONTRIBUTION_DIAGNOSTIC_SCHEMA
                if physiological_outputs_enabled(cfg)
                else EMBODIED_CONTRIBUTION_DIAGNOSTIC_SCHEMA
                if embodied_outputs_enabled(cfg)
                else CONTRIBUTION_DIAGNOSTIC_SCHEMA
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
            "functional_module_compositional_capable": bool(
                compositional_modules_enabled(cfg)
            ),
            "functional_module_embodied_capable": bool(
                embodied_outputs_enabled(cfg)
            ),
            "functional_module_physiological_capable": bool(
                physiological_outputs_enabled(cfg) or regulatory_outputs_enabled(cfg)
            ),
            "functional_module_regulatory_capable": bool(
                regulatory_outputs_enabled(cfg)
            ),
            "functional_module_embodied_output_schema": (
                cfg.functional_modules.output_schema
            ),
            "functional_embodied_output_effective_dimensions": 0.0,
            "functional_output_basis_effective_dimensions": 0.0,
            "functional_output_basis_active_port_count": 0,
            "functional_output_basis_std_by_port": [0.0] * (OUTPUT_COUNT + auxiliary_count),
            "functional_output_basis_port_names": [
                *[f"harvest_residual_{index}" for index in range(OUTPUT_COUNT)],
                *auxiliary_names,
            ],
            "functional_embodied_output_changed_entity_fraction": 0.0,
            "functional_embodied_output_mean": [0.0] * EMBODIED_OUTPUT_COUNT,
            "functional_embodied_output_std": [0.0] * EMBODIED_OUTPUT_COUNT,
            "functional_embodied_output_abs_mean_by_port": [0.0] * EMBODIED_OUTPUT_COUNT,
            "functional_embodied_output_names": list(EMBODIED_OUTPUT_NAMES),
            "functional_physiology_output_effective_dimensions": 0.0,
            "functional_physiology_output_changed_entity_fraction": 0.0,
            "functional_physiology_output_mean": [0.0] * PHYSIOLOGICAL_OUTPUT_COUNT,
            "functional_physiology_output_std": [0.0] * PHYSIOLOGICAL_OUTPUT_COUNT,
            "functional_physiology_output_abs_mean_by_port": [0.0]
            * PHYSIOLOGICAL_OUTPUT_COUNT,
            "functional_physiology_output_names": list(
                REGULATORY_OUTPUT_NAMES
                if regulatory_outputs_enabled(cfg)
                else PHYSIOLOGICAL_OUTPUT_NAMES
            ),
            "functional_module_hierarchy_depth_by_module": list(range(count)),
            "functional_module_coupling_link_count": int(
                functional_module_coupling_count(cfg)
            ),
            "functional_module_coupling_ablation_enabled": False,
            "functional_module_coupling_weight_abs_mean": 0.0,
            "functional_module_coupling_weight_effective_dimensions": 0.0,
            "functional_module_modulation_abs_mean": 0.0,
            "functional_module_modulation_abs_mean_by_module": zero_by_module,
            "functional_module_mediated_signal_abs_mean": 0.0,
            "functional_module_mediated_signal_abs_mean_by_module": zero_by_module,
            "functional_module_coupling_changed_entity_fraction": 0.0,
            "functional_module_coupling_amplification_fraction_by_module": zero_by_module,
            "functional_module_coupling_suppression_fraction_by_module": zero_by_module,
            "functional_module_dominant_input_counts": [0] * input_count,
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
    (
        _,
        input_gene,
        _,
        output_gene,
        auxiliary_output_gene,
        coupling_gene,
    ) = _blocks(values, cfg, gene_start)
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
            np.argmax(np.abs(expressed_inputs), axis=1), minlength=input_count
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
        dominant_inputs = np.zeros(input_count, dtype=np.int64)
        dominant_outputs = np.zeros(OUTPUT_COUNT, dtype=np.int64)
        input_dimensions = 0.0
        output_dimensions = 0.0

    context_activation_q = (
        np.asarray(evaluation.context_activation_q, dtype=np.int64)
        if evaluation.context_activation_q is not None
        else np.asarray(evaluation.activation_q, dtype=np.int64)
    )
    modulation_q = (
        np.asarray(evaluation.modulation_q, dtype=np.int64)
        if evaluation.modulation_q is not None
        else np.zeros_like(context_activation_q)
    )
    context_signal_q = (
        np.asarray(evaluation.gates_q, dtype=np.int64) * context_activation_q
    ) // Q
    mediated_signal_q = np.asarray(evaluation.signal_q, dtype=np.int64) - context_signal_q
    coupling_values = np.tanh(coupling_gene.astype(np.float64))
    valid_couplings = []
    for target in range(1, count):
        valid_couplings.append(coupling_values[:, target, :target])
    coupling_matrix = (
        np.concatenate(valid_couplings, axis=1)
        if valid_couplings
        else np.zeros((values.shape[0], 0), dtype=np.float64)
    )
    base_abs = np.abs(context_signal_q)
    final_abs = np.abs(np.asarray(evaluation.signal_q, dtype=np.int64))
    amplification_fraction = np.zeros(count, dtype=np.float64)
    suppression_fraction = np.zeros(count, dtype=np.float64)
    for module_index in range(count):
        eligible = expressed[:, module_index]
        denominator_count = int(np.count_nonzero(eligible))
        if denominator_count:
            amplification_fraction[module_index] = float(
                np.count_nonzero(
                    eligible & (final_abs[:, module_index] > base_abs[:, module_index])
                )
                / denominator_count
            )
            suppression_fraction[module_index] = float(
                np.count_nonzero(
                    eligible & (final_abs[:, module_index] < base_abs[:, module_index])
                )
                / denominator_count
            )

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
    embodied_q = (
        np.zeros((values.shape[0], EMBODIED_OUTPUT_COUNT), dtype=np.int32)
        if evaluation.embodied_output_q is None
        else np.asarray(evaluation.embodied_output_q, dtype=np.int32)
    )
    embodied = embodied_q.astype(np.float64) / Q
    embodied_router = (
        np.tanh(auxiliary_output_gene.astype(np.float64)).reshape(values.shape[0], -1)
        if embodied_outputs_enabled(cfg)
        else np.zeros((values.shape[0], 0), dtype=np.float64)
    )
    physiology_q = (
        np.zeros((values.shape[0], PHYSIOLOGICAL_OUTPUT_COUNT), dtype=np.int32)
        if evaluation.physiology_output_q is None
        else np.asarray(evaluation.physiology_output_q, dtype=np.int32)
    )
    physiology = physiology_q.astype(np.float64) / Q
    physiology_router = (
        np.tanh(auxiliary_output_gene.astype(np.float64)).reshape(values.shape[0], -1)
        if physiological_outputs_enabled(cfg) or regulatory_outputs_enabled(cfg)
        else np.zeros((values.shape[0], 0), dtype=np.float64)
    )
    auxiliary = (
        physiology
        if physiological_outputs_enabled(cfg) or regulatory_outputs_enabled(cfg)
        else embodied
    )
    output_basis = np.concatenate((residual_shares, auxiliary), axis=1)
    output_basis_std = output_basis.std(axis=0)
    output_basis_names = [
        *[f"harvest_residual_{index}" for index in range(OUTPUT_COUNT)],
        *auxiliary_names,
    ]

    return {
        "functional_module_schema": cfg.functional_modules.schema,
        "functional_module_contribution_diagnostic_schema": (
            REGULATORY_CONTRIBUTION_DIAGNOSTIC_SCHEMA
            if regulatory_outputs_enabled(cfg)
            else EMBODIED_CONTRIBUTION_DIAGNOSTIC_SCHEMA
            if embodied_outputs_enabled(cfg)
            else PHYSIOLOGICAL_CONTRIBUTION_DIAGNOSTIC_SCHEMA
            if physiological_outputs_enabled(cfg)
            else CONTRIBUTION_DIAGNOSTIC_SCHEMA
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
        "functional_module_compositional_capable": bool(
            compositional_modules_enabled(cfg)
        ),
        "functional_module_embodied_capable": bool(embodied_outputs_enabled(cfg)),
        "functional_module_physiological_capable": bool(
            physiological_outputs_enabled(cfg) or regulatory_outputs_enabled(cfg)
        ),
        "functional_module_regulatory_capable": bool(
            regulatory_outputs_enabled(cfg)
        ),
        "functional_module_embodied_output_schema": cfg.functional_modules.output_schema,
        "functional_module_embodied_output_ablation_enabled": bool(
            evaluation.embodied_output_ablation_enabled
        ),
        "functional_module_embodied_router_effective_dimensions": float(
            _effective_dimensions(embodied_router)
        ),
        "functional_embodied_output_effective_dimensions": float(
            _effective_dimensions(embodied)
        ),
        "functional_output_basis_effective_dimensions": float(
            _effective_dimensions(output_basis)
        ),
        "functional_output_basis_active_port_count": int(
            np.count_nonzero(output_basis_std > 1.0e-6)
        ),
        "functional_output_basis_std_by_port": output_basis_std.tolist(),
        "functional_output_basis_port_names": output_basis_names,
        "functional_embodied_output_changed_entity_fraction": float(
            np.any(embodied_q != 0, axis=1).mean()
        ),
        "functional_embodied_output_mean": embodied.mean(axis=0).tolist(),
        "functional_embodied_output_std": embodied.std(axis=0).tolist(),
        "functional_embodied_output_abs_mean_by_port": (
            np.abs(embodied).mean(axis=0).tolist()
        ),
        "functional_embodied_output_names": list(EMBODIED_OUTPUT_NAMES),
        "functional_module_physiology_output_ablation_enabled": bool(
            evaluation.physiology_output_ablation_enabled
        ),
        "functional_module_physiology_router_effective_dimensions": float(
            _effective_dimensions(physiology_router)
        ),
        "functional_physiology_output_effective_dimensions": float(
            _effective_dimensions(physiology)
        ),
        "functional_physiology_output_changed_entity_fraction": float(
            np.any(physiology_q != 0, axis=1).mean()
        ),
        "functional_physiology_output_mean": physiology.mean(axis=0).tolist(),
        "functional_physiology_output_std": physiology.std(axis=0).tolist(),
        "functional_physiology_output_abs_mean_by_port": (
            np.abs(physiology).mean(axis=0).tolist()
        ),
        "functional_physiology_output_names": list(
            REGULATORY_OUTPUT_NAMES
            if regulatory_outputs_enabled(cfg)
            else PHYSIOLOGICAL_OUTPUT_NAMES
        ),
        "functional_module_hierarchy_depth_by_module": list(range(count)),
        "functional_module_coupling_link_count": int(
            functional_module_coupling_count(cfg)
        ),
        "functional_module_coupling_ablation_enabled": bool(
            evaluation.coupling_ablation_enabled
        ),
        "functional_module_coupling_weight_abs_mean": float(
            np.abs(coupling_matrix).mean() if coupling_matrix.size else 0.0
        ),
        "functional_module_coupling_weight_effective_dimensions": float(
            _effective_dimensions(coupling_matrix)
        ),
        "functional_module_modulation_abs_mean": float(
            np.abs(modulation_q.astype(np.float64) / Q).mean()
        ),
        "functional_module_modulation_abs_mean_by_module": (
            np.abs(modulation_q.astype(np.float64) / Q).mean(axis=0).tolist()
        ),
        "functional_module_mediated_signal_abs_mean": float(
            np.abs(mediated_signal_q.astype(np.float64) / Q).mean()
        ),
        "functional_module_mediated_signal_abs_mean_by_module": (
            np.abs(mediated_signal_q.astype(np.float64) / Q).mean(axis=0).tolist()
        ),
        "functional_module_coupling_changed_entity_fraction": float(
            np.any(mediated_signal_q != 0, axis=1).mean()
        ),
        "functional_module_coupling_amplification_fraction_by_module": (
            amplification_fraction.tolist()
        ),
        "functional_module_coupling_suppression_fraction_by_module": (
            suppression_fraction.tolist()
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
    "COMPOSITIONAL_FUNCTIONAL_MODULE_SCHEMA",
    "COMPOSITIONAL_INPUT_SCHEMA",
    "EMBODIED_FUNCTIONAL_MODULE_SCHEMA",
    "EMBODIED_OUTPUT_SCHEMA",
    "EMBODIED_OUTPUT_NAMES",
    "EMBODIED_OUTPUT_COUNT",
    "EMBODIED_GENES_PER_MODULE",
    "PHYSIOLOGICAL_FUNCTIONAL_MODULE_SCHEMA",
    "PHYSIOLOGICAL_INPUT_SCHEMA",
    "PHYSIOLOGICAL_OUTPUT_SCHEMA",
    "PHYSIOLOGICAL_OUTPUT_NAMES",
    "PHYSIOLOGICAL_OUTPUT_COUNT",
    "PHYSIOLOGICAL_GENES_PER_MODULE",
    "PHYSIOLOGICAL_CONTRIBUTION_DIAGNOSTIC_SCHEMA",
    "REGULATORY_CONTRIBUTION_DIAGNOSTIC_SCHEMA",
    "REGULATORY_FUNCTIONAL_MODULE_SCHEMA",
    "REGULATORY_INPUT_SCHEMA",
    "REGULATORY_OUTPUT_SCHEMA",
    "REGULATORY_OUTPUT_NAMES",
    "REGULATORY_OUTPUT_COUNT",
    "REGULATORY_GENES_PER_MODULE",
    "CONTRIBUTION_DIAGNOSTIC_SCHEMA",
    "EMBODIED_CONTRIBUTION_DIAGNOSTIC_SCHEMA",
    "COUPLING_SCHEMA",
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
    "functional_module_coupling_count",
    "functional_module_energy",
    "functional_module_gene_count",
    "functional_module_genes_per_module",
    "embodied_outputs_enabled",
    "physiological_outputs_enabled",
    "regulatory_outputs_enabled",
    "functional_module_input_count",
    "functional_module_auxiliary_output_count",
    "functional_modules_enabled",
    "compositional_modules_enabled",
]
