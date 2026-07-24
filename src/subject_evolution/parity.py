"""CPU/GPU semantic parity diagnostics.

The CPU simulation is the semantic reference.  This module compares the
backend-neutral device algorithms against that reference stage by stage, then
(optionally) advances paired CPU/GPU worlds and stops at the first divergent
stage.  It is intentionally a diagnostic tool rather than a tolerance-based
claim that two final curves merely look similar.
"""

from __future__ import annotations

import argparse
import copy
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
import json
from pathlib import Path
import tempfile
from typing import Any

import numpy as np

from .backend import BackendUnavailableError, cupy_available, resolve_backend, to_numpy
from .config import SimulationConfig, load_config
from .environment import Environment
from .gpu_environment import DeviceEnvironment, DeviceInformationField
from .information import DirectMessageObservationPlan, InformationSystem
from .policy import ParametricPolicy
from .reductions import stable_segmented_sum
from .simulation import Simulation
from .spatial import SpatialIndex


PARITY_SCHEMA = "cpu-gpu-parity-v1"
DEFAULT_ATOL = 1e-6
DEFAULT_RTOL = 1e-6


def _json_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def _first_index(mask: np.ndarray) -> list[int] | None:
    if not np.any(mask):
        return None
    return [int(v) for v in np.argwhere(mask)[0]]


def compare_array(
    name: str,
    reference: Any,
    candidate: Any,
    *,
    atol: float = DEFAULT_ATOL,
    rtol: float = DEFAULT_RTOL,
) -> dict[str, Any]:
    """Compare one array and return a compact, machine-readable result."""
    if reference is None or candidate is None:
        passed = reference is None and candidate is None
        return {
            "name": name,
            "passed": passed,
            "reason": None if passed else "optional-presence-mismatch",
            "reference_present": reference is not None,
            "candidate_present": candidate is not None,
        }
    ref = np.asarray(to_numpy(reference))
    got = np.asarray(to_numpy(candidate))
    result: dict[str, Any] = {
        "name": name,
        "reference_shape": list(ref.shape),
        "candidate_shape": list(got.shape),
        "reference_dtype": str(ref.dtype),
        "candidate_dtype": str(got.dtype),
        "exact_required": bool(
            ref.dtype.kind in "biu" and got.dtype.kind in "biu"
        ),
    }
    if ref.shape != got.shape:
        result.update({"passed": False, "reason": "shape-mismatch"})
        return result
    if ref.dtype.kind in "biu" or got.dtype.kind in "biu":
        mismatch = ref != got
        passed = bool(np.array_equal(ref, got))
        result.update(
            {
                "passed": passed,
                "reason": None if passed else "discrete-mismatch",
                "first_mismatch_index": _first_index(mismatch),
            }
        )
        if not passed and result["first_mismatch_index"] is not None:
            idx = tuple(result["first_mismatch_index"])
            result["reference_value"] = _json_scalar(ref[idx])
            result["candidate_value"] = _json_scalar(got[idx])
        return result

    ref64 = ref.astype(np.float64, copy=False)
    got64 = got.astype(np.float64, copy=False)
    finite_equal = np.array_equal(np.isfinite(ref64), np.isfinite(got64))
    close = np.isclose(ref64, got64, atol=atol, rtol=rtol, equal_nan=True)
    passed = bool(finite_equal and np.all(close))
    abs_error = np.abs(ref64 - got64)
    denominator = np.maximum(np.abs(ref64), np.finfo(np.float64).tiny)
    rel_error = abs_error / denominator
    result.update(
        {
            "passed": passed,
            "reason": None if passed else "float-mismatch",
            "atol": float(atol),
            "rtol": float(rtol),
            "max_abs_error": float(np.nanmax(abs_error)) if abs_error.size else 0.0,
            "max_rel_error": float(np.nanmax(rel_error)) if rel_error.size else 0.0,
            "first_mismatch_index": _first_index(~close),
        }
    )
    if not passed and result["first_mismatch_index"] is not None:
        idx = tuple(result["first_mismatch_index"])
        result["reference_value"] = _json_scalar(ref[idx])
        result["candidate_value"] = _json_scalar(got[idx])
    return result


def _compare_value(prefix: str, reference: Any, candidate: Any) -> list[dict[str, Any]]:
    if reference is None or candidate is None:
        passed = reference is None and candidate is None
        return [
            {
                "name": prefix,
                "passed": passed,
                "reason": None if passed else "optional-presence-mismatch",
                "reference_present": reference is not None,
                "candidate_present": candidate is not None,
            }
        ]
    if isinstance(reference, Mapping) and isinstance(candidate, Mapping):
        reference_keys = set(reference)
        candidate_keys = set(candidate)
        if reference_keys != candidate_keys:
            return [
                {
                    "name": prefix,
                    "passed": False,
                    "reason": "mapping-key-mismatch",
                    "reference_only": sorted(str(key) for key in reference_keys - candidate_keys),
                    "candidate_only": sorted(str(key) for key in candidate_keys - reference_keys),
                }
            ]
        results: list[dict[str, Any]] = []
        for key in sorted(reference_keys, key=str):
            results.extend(
                _compare_value(
                    f"{prefix}.{key}", reference[key], candidate[key]
                )
            )
        return results
    if is_dataclass(reference) and is_dataclass(candidate):
        results: list[dict[str, Any]] = []
        for field in fields(reference):
            results.extend(
                _compare_value(
                    f"{prefix}.{field.name}",
                    getattr(reference, field.name),
                    getattr(candidate, field.name),
                )
            )
        return results
    if isinstance(reference, np.ndarray) or isinstance(candidate, np.ndarray):
        return [compare_array(prefix, reference, candidate)]
    if isinstance(reference, (tuple, list)) and isinstance(candidate, (tuple, list)):
        if len(reference) != len(candidate):
            return [
                {
                    "name": prefix,
                    "passed": False,
                    "reason": "length-mismatch",
                    "reference_length": len(reference),
                    "candidate_length": len(candidate),
                }
            ]
        results = []
        for index, (ref_item, got_item) in enumerate(zip(reference, candidate)):
            results.extend(_compare_value(f"{prefix}[{index}]", ref_item, got_item))
        return results
    passed = reference == candidate
    return [
        {
            "name": prefix,
            "passed": bool(passed),
            "reason": None if passed else "scalar-mismatch",
            "reference_value": _json_scalar(reference),
            "candidate_value": _json_scalar(candidate),
        }
    ]


def _stage(name: str, comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stage": name,
        "passed": all(bool(item.get("passed")) for item in comparisons),
        "comparisons": comparisons,
    }


def _small_config(
    cfg: SimulationConfig,
    *,
    ticks: int,
    entities: int,
    preserve_world: bool = False,
) -> SimulationConfig:
    entity_count = max(1, int(entities))
    max_entities = max(entity_count + max(8, entity_count // 2), entity_count)
    run = replace(
        cfg.run,
        ticks=max(1, int(ticks)),
        metrics_period=max(1, int(ticks)),
        checkpoint_period=max(1, int(ticks)),
        evolution_evaluation_period=max(int(ticks) + 1, 2),
        validation_mode=True,
        trajectory_subject_ids=(),
    )
    world = (
        cfg.world
        if preserve_world
        else replace(
            cfg.world, initial_entities=entity_count, max_entities=max_entities
        )
    )
    return replace(cfg, run=run, world=world)


def _close_simulation(simulation: Simulation) -> None:
    # ``step`` does not finalize writers.  Parity runs intentionally avoid
    # ``Simulation.run`` so they can stop at the first divergent tick.
    for writer_name in ("metrics", "evolution_progress", "knowledge"):
        writer = getattr(simulation, writer_name, None)
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
    trajectory = getattr(simulation, "_trajectory_file", None)
    if trajectory is not None and not trajectory.closed:
        trajectory.close()


def run_stage_parity(
    cfg: SimulationConfig,
    *,
    backend_name: str,
    ticks: int,
    output_dir: Path,
) -> dict[str, Any]:
    """Compare CPU reference stages with the device algorithms."""
    backend = resolve_backend(backend_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    stages: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="subject-parity-stage-") as tmp:
        simulation = Simulation(cfg, Path(tmp) / "reference", backend="cpu")
        try:
            # Field initialization and updates.
            cpu_environment = Environment(cfg)
            device_environment = DeviceEnvironment(cfg, backend=backend)
            initial_comparisons = [
                compare_array(
                    "environment.resources",
                    cpu_environment.resources,
                    device_environment.resources,
                ),
                compare_array(
                    "environment.hazard",
                    cpu_environment.hazard,
                    device_environment.hazard,
                ),
            ]
            stages.append(_stage("environment-initialization", initial_comparisons))
            for tick in range(max(1, ticks)):
                cpu_environment.update(tick)
                device_environment.update(tick)
            stages.append(
                _stage(
                    "environment-update",
                    [
                        compare_array(
                            "environment.resources",
                            cpu_environment.resources,
                            device_environment.resources,
                        ),
                        compare_array(
                            "environment.hazard",
                            cpu_environment.hazard,
                            device_environment.hazard,
                        ),
                    ],
                )
            )

            # Deterministic reduction and harvest allocation/commit.
            cell_count = cfg.world.grid_x * cfg.world.grid_y
            count = min(max(cfg.world.initial_entities, 8), 256)
            cells = (np.arange(count, dtype=np.int32) * 7) % cell_count
            cells[1::3] = cells[::3][: cells[1::3].size]
            values = np.linspace(0.001, 0.25, count, dtype=np.float32)
            device_cells = backend.asarray(cells, dtype=backend.xp.int32)
            device_values = backend.asarray(values, dtype=backend.xp.float32)
            stages.append(
                _stage(
                    "stable-segmented-reduction",
                    [
                        compare_array(
                            "segmented_sum",
                            stable_segmented_sum(cells, values, cell_count, dtype=np.float32),
                            stable_segmented_sum(
                                device_cells,
                                device_values,
                                cell_count,
                                backend=backend,
                                dtype=backend.xp.float32,
                            ),
                        )
                    ],
                )
            )
            rates = np.broadcast_to(
                np.asarray(
                    [
                        cfg.entities.harvest_rate,
                        cfg.entities.harvest_rate * 0.45,
                        cfg.entities.harvest_rate * 0.25,
                        cfg.entities.harvest_rate * 0.18,
                    ],
                    dtype=np.float32,
                ),
                (count, 4),
            ).copy()
            cpu_harvest_env = Environment(cfg)
            device_harvest_env = DeviceEnvironment(cfg, backend=backend)
            cpu_gathered = cpu_harvest_env.resolve_harvest(cells, rates)
            device_gathered = device_harvest_env.resolve_harvest(
                device_cells, backend.asarray(rates, dtype=backend.xp.float32)
            )
            allocation = compare_array("harvest.gathered", cpu_gathered, device_gathered)
            cpu_harvest_env.commit_harvest(cells, cpu_gathered)
            device_harvest_env.commit_harvest(device_cells, device_gathered)
            stages.append(
                _stage(
                    "harvest-resolve-commit",
                    [
                        allocation,
                        compare_array(
                            "harvest.resources_after",
                            cpu_harvest_env.resources,
                            device_harvest_env.resources,
                        ),
                    ],
                )
            )

            # Spatial ordering and partner sampling.
            entity = simulation.entities
            reference_spatial = SpatialIndex(
                cfg.world.grid_x,
                cfg.world.grid_y,
                cfg.world.width,
                cfg.world.height,
                cfg.world.periodic,
                backend="cpu",
            )
            device_spatial = SpatialIndex(
                cfg.world.grid_x,
                cfg.world.grid_y,
                cfg.world.width,
                cfg.world.height,
                cfg.world.periodic,
                backend=backend,
            )
            active = reference_spatial.build(entity.x, entity.y, entity.alive)
            device_active = device_spatial.build(entity.x, entity.y, entity.alive)
            partners = reference_spatial.sample_partners(
                active,
                entity.entity_id,
                cfg.run.seed,
                0,
                cfg.policy.partner_samples,
            )
            device_partners = device_spatial.sample_partners(
                device_active,
                backend.asarray(entity.entity_id, dtype=backend.xp.uint64),
                cfg.run.seed,
                0,
                cfg.policy.partner_samples,
            )
            stages.append(
                _stage(
                    "spatial-index-partners",
                    [
                        compare_array("spatial.active", active, device_active),
                        compare_array(
                            "spatial.entity_cells",
                            reference_spatial.entity_cells,
                            device_spatial.entity_cells,
                        ),
                        compare_array(
                            "spatial.sorted_entity_indices",
                            reference_spatial.sorted_entity_indices,
                            device_spatial.sorted_entity_indices,
                        ),
                        compare_array("spatial.partners", partners, device_partners),
                    ],
                )
            )

            # Observation with due direct messages.  Duplicate the queue so the
            # CPU and device consumers see precisely the same immutable events.
            cells_active = reference_spatial.entity_cells[active]
            message_source = simulation.information
            if active.size >= 4:
                half = min(int(active.size // 2), 16)
                source_ids = entity.entity_id[active[:half]]
                receiver_ids = entity.entity_id[active[half : half * 2]]
                payloads = (
                    np.arange(half * 3, dtype=np.float64).reshape(half, 3) / 100.0
                )
                confidences = np.linspace(0.25, 0.95, half, dtype=np.float64)
                message_source.emit_direct(
                    source_ids,
                    receiver_ids,
                    payloads,
                    confidences,
                    cfg.run.seed,
                    -1,
                )
            device_message_source: InformationSystem = copy.deepcopy(message_source)
            sensor_quality = entity.sensor_quality()
            cpu_info = message_source.observe(
                active,
                entity.entity_id,
                cells_active,
                partners,
                entity.energy,
                simulation.social.group_id,
                sensor_quality,
                cfg.run.seed,
                0,
            )
            direct_plan: DirectMessageObservationPlan = (
                device_message_source._receive_direct_plan(
                    active,
                    entity.entity_id,
                    sensor_quality,
                    cfg.run.seed,
                    0,
                )
            )
            device_info_field = DeviceInformationField(cfg, backend=backend)
            device_info_field.field = backend.asarray(
                device_message_source.field, dtype=backend.xp.float32, copy=True
            )
            device_info_field.source = backend.asarray(
                device_message_source.source, dtype=backend.xp.float32, copy=True
            )
            device_info_field.age = backend.asarray(
                device_message_source.age, dtype=backend.xp.uint16, copy=True
            )
            gpu_info = device_info_field.observe(
                stable_ids=backend.asarray(
                    entity.entity_id[active], dtype=backend.xp.uint64
                ),
                cell_ids=backend.asarray(cells_active, dtype=backend.xp.int32),
                partners=backend.asarray(partners, dtype=backend.xp.int32),
                energy=backend.asarray(entity.energy, dtype=backend.xp.float32),
                group_id=backend.asarray(
                    simulation.social.group_id, dtype=backend.xp.uint64
                ),
                own_group_id=backend.asarray(
                    simulation.social.group_id[active], dtype=backend.xp.uint64
                ),
                sensor_quality=backend.asarray(
                    sensor_quality[active], dtype=backend.xp.float32
                ),
                direct_message_plan=direct_plan,
                run_seed=cfg.run.seed,
                tick=0,
            )
            observation_fields = (
                "signals",
                "signal_mask",
                "signal_age",
                "partner_energy",
                "partner_group_match",
                "partner_mask",
                "uncertainty",
            )
            stages.append(
                _stage(
                    "information-observation",
                    [
                        compare_array(
                            f"information.{name}",
                            getattr(cpu_info, name),
                            getattr(gpu_info, name),
                        )
                        for name in observation_fields
                    ],
                )
            )

            # Policy batch.  The field and gradient state is the same snapshot
            # used by the CPU reference above.
            local_resources = simulation.environment.cell_values(cells_active)
            resource_gradient, danger_gradient = simulation.environment.gradients_for_entities(
                reference_spatial.entity_cells, entity.alive.size
            )
            policy = ParametricPolicy(cfg)
            cpu_decision = policy.decide(
                active,
                entity.entity_id,
                entity.energy,
                entity.integrity,
                entity.fertility,
                entity.genotype,
                entity.memory,
                local_resources,
                resource_gradient,
                danger_gradient,
                (simulation.social.group_dir_x, simulation.social.group_dir_y),
                partners,
                cpu_info,
                cfg.run.seed,
                0,
            )
            device_resource_gradient = tuple(
                backend.asarray(value, dtype=backend.xp.float32)
                for value in resource_gradient
            )
            device_danger_gradient = tuple(
                backend.asarray(value, dtype=backend.xp.float32)
                for value in danger_gradient
            )
            device_decision = policy.decide(
                backend.asarray(active, dtype=backend.xp.int32),
                backend.asarray(entity.entity_id, dtype=backend.xp.uint64),
                backend.asarray(entity.energy, dtype=backend.xp.float32),
                backend.asarray(entity.integrity, dtype=backend.xp.float32),
                backend.asarray(entity.fertility, dtype=backend.xp.float32),
                backend.asarray(entity.genotype, dtype=backend.xp.float32),
                backend.asarray(entity.memory, dtype=backend.xp.float32),
                backend.asarray(local_resources, dtype=backend.xp.float32),
                device_resource_gradient,
                device_danger_gradient,
                (
                    backend.asarray(
                        simulation.social.group_dir_x, dtype=backend.xp.float32
                    ),
                    backend.asarray(
                        simulation.social.group_dir_y, dtype=backend.xp.float32
                    ),
                ),
                backend.asarray(partners, dtype=backend.xp.int32),
                gpu_info,
                cfg.run.seed,
                0,
            )
            decision_fields = (
                "features",
                "genetic_logits",
                "knowledge_logits",
                "logits",
                "genetic_action",
                "action_mask",
                "action",
                "probability",
                "entropy",
                "direction_x",
                "direction_y",
                "selected_partner",
            )
            stages.append(
                _stage(
                    "policy-batch",
                    [
                        compare_array(
                            f"policy.{name}",
                            getattr(cpu_decision, name),
                            getattr(device_decision, name),
                        )
                        for name in decision_fields
                    ],
                )
            )
        finally:
            _close_simulation(simulation)

    first_failure = next((stage for stage in stages if not stage["passed"]), None)
    return {
        "schema": PARITY_SCHEMA,
        "mode": "stage-parity",
        "device_backend": backend.name,
        "passed": first_failure is None,
        "first_failure_stage": None if first_failure is None else first_failure["stage"],
        "stages": stages,
    }


def _array_state_snapshot(value: Any) -> dict[str, Any]:
    """Return the object's actual named array state without guessing aliases.

    SocialSystem stores relation arrays as ``target`` and ``trust``.
    ``relation_targets`` belongs to GroupDetectionSnapshot and is not an
    attribute of SocialSystem.  Discovering the live arrays from ``__dict__``
    keeps this diagnostic aligned with the authoritative implementation and
    automatically includes future array-backed social state.
    """
    state = {
        name: array
        for name, array in vars(value).items()
        if isinstance(array, np.ndarray)
        or array.__class__.__module__.split(".", 1)[0] == "cupy"
    }
    if not state:
        raise TypeError(
            f"{type(value).__name__} exposes no array-backed state for parity comparison"
        )
    return dict(sorted(state.items()))


def _simulation_stages(cpu: Simulation, gpu: Simulation) -> list[tuple[str, Any, Any]]:
    stages: list[tuple[str, Any, Any]] = [
        ("prepared-index", (cpu.last_active, cpu.last_cells), (gpu.last_active, gpu.last_cells)),
        (
            "prepared-local-resources",
            cpu.last_local_resources,
            gpu.last_local_resources,
        ),
    ]
    if cpu.last_information is not None or gpu.last_information is not None:
        info_fields = (
            "signals",
            "signal_mask",
            "signal_age",
            "partner_energy",
            "partner_group_match",
            "partner_mask",
            "uncertainty",
        )
        stages.append(
            (
                "policy-observation",
                (
                    None
                    if cpu.last_information is None
                    else {name: getattr(cpu.last_information, name) for name in info_fields}
                ),
                (
                    None
                    if gpu.last_information is None
                    else {name: getattr(gpu.last_information, name) for name in info_fields}
                ),
            )
        )
    if cpu.last_policy_decision is not None or gpu.last_policy_decision is not None:
        decision_fields = (
            "features",
            "genetic_logits",
            "knowledge_logits",
            "linear_knowledge_logits",
            "logits",
            "action_mask",
            "genetic_action",
            "linear_knowledge_action",
            "memory_free_knowledge_action",
            "action",
            "probability",
            "entropy",
            "direction_x",
            "direction_y",
            "selected_partner",
        )
        stages.append(
            (
                "policy-decision",
                (
                    None
                    if cpu.last_policy_decision is None
                    else {name: getattr(cpu.last_policy_decision, name) for name in decision_fields}
                ),
                (
                    None
                    if gpu.last_policy_decision is None
                    else {name: getattr(gpu.last_policy_decision, name) for name in decision_fields}
                ),
            )
        )
    stages.append((
        "knowledge-policy-plan",
        cpu.last_knowledge_policy_plan,
        gpu.last_knowledge_policy_plan,
    ))
    if cpu.last_intents is not None or gpu.last_intents is not None:
        stages.append(("intents", cpu.last_intents, gpu.last_intents))
    if cpu.last_resolutions is not None or gpu.last_resolutions is not None:
        stages.append(("resolutions", cpu.last_resolutions, gpu.last_resolutions))
    stages.extend(
        [
            ("birth-allocation", cpu.last_birth_allocation, gpu.last_birth_allocation),
            ("death-events", cpu.last_death_events, gpu.last_death_events),
        ]
    )
    entity_fields = (
        "entity_id",
        "alive",
        "x",
        "y",
        "energy",
        "integrity",
        "fertility",
        "information_store",
        "age",
        "generation",
        "lineage_id",
        "primary_subject_id",
        "lineage_subject_id",
        "genotype",
        "memory",
        "working_memory_q",
        "working_memory_previous_observation_q",
    )
    stages.append(
        (
            "entity-state",
            tuple(getattr(cpu.entities, name) for name in entity_fields),
            tuple(getattr(gpu.entities, name) for name in entity_fields),
        )
    )
    stages.append(
        (
            "environment-fields",
            {
                "resources": cpu.environment.resources,
                "hazard": cpu.environment.hazard,
            },
            {
                "resources": gpu.environment.resources,
                "hazard": gpu.environment.hazard,
            },
        )
    )
    stages.append(
        (
            "information-fields",
            {
                "field": cpu.information.field,
                "source": cpu.information.source,
                "age": cpu.information.age,
            },
            {
                "field": gpu.information.field,
                "source": gpu.information.source,
                "age": gpu.information.age,
            },
        )
    )
    stages.append(
        (
            "social-state",
            _array_state_snapshot(cpu.social),
            _array_state_snapshot(gpu.social),
        )
    )
    if cpu.cfg.knowledge.enabled:
        cpu_knowledge = cpu.knowledge.checkpoint_arrays()
        gpu_knowledge = gpu.knowledge.checkpoint_arrays()
        keys = sorted(set(cpu_knowledge) | set(gpu_knowledge))
        stages.append(
            (
                "knowledge-state",
                tuple(cpu_knowledge.get(key, np.asarray([], dtype=np.uint8)) for key in keys),
                tuple(gpu_knowledge.get(key, np.asarray([], dtype=np.uint8)) for key in keys),
            )
        )
    return stages


def _failure_entity_context(
    cpu: Simulation, stage_name: str, comparisons: list[dict[str, Any]]
) -> dict[str, Any] | None:
    failed = next((item for item in comparisons if not item.get("passed")), None)
    if failed is None:
        return None
    index = failed.get("first_mismatch_index")
    if not isinstance(index, list) or not index:
        return None
    row = int(index[0])
    active_row_stages = {
        "prepared-index",
        "prepared-local-resources",
        "policy-observation",
        "policy-decision",
        "knowledge-policy-plan",
        "intents",
        "resolutions",
    }
    if stage_name in active_row_stages and 0 <= row < cpu.last_active.size:
        slot = int(cpu.last_active[row])
    elif stage_name in {"entity-state", "social-state"} and 0 <= row < cpu.entities.alive.size:
        slot = row
    else:
        return None
    return {
        "active_row": row if stage_name in active_row_stages else None,
        "entity_slot": slot,
        "reference_entity_id": int(cpu.entities.entity_id[slot]),
        "candidate_entity_id": int(gpu.entities.entity_id[slot]),
    }


def run_world_parity(cfg: SimulationConfig, *, ticks: int, output_dir: Path) -> dict[str, Any]:
    """Run paired CPU/experimental-hybrid worlds and stop at first divergence.

    Normal scientific GPU runs default to strict CPU-reference semantics.  A
    parity diagnostic must explicitly exercise the accelerated implementation,
    otherwise both worlds would intentionally follow the same CPU authority.
    """
    if not cupy_available():
        return {
            "schema": PARITY_SCHEMA,
            "mode": "world-parity",
            "gpu_available": False,
            "passed": False,
            "reason": "GPU backend is unavailable; install a compatible CuPy/CUDA runtime.",
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    hybrid_cfg = replace(
        cfg, run=replace(cfg.run, gpu_semantics_mode="hybrid-accelerated")
    )
    cpu = Simulation(hybrid_cfg, output_dir / "cpu", backend="cpu")
    gpu = Simulation(hybrid_cfg, output_dir / "gpu", backend="gpu")
    tick_reports: list[dict[str, Any]] = []
    first_failure: dict[str, Any] | None = None
    try:
        for _ in range(max(1, ticks)):
            cpu.step()
            gpu.step()
            stage_reports: list[dict[str, Any]] = []
            for stage_name, reference, candidate in _simulation_stages(cpu, gpu):
                comparisons = _compare_value(stage_name, reference, candidate)
                report = _stage(stage_name, comparisons)
                stage_reports.append(report)
                if not report["passed"]:
                    first_failure = {
                        "tick": int(cpu.tick),
                        "stage": stage_name,
                        "entity_context": _failure_entity_context(
                            cpu, stage_name, comparisons
                        ),
                        "comparisons": comparisons,
                    }
                    break
            tick_reports.append(
                {
                    "tick": int(cpu.tick),
                    "passed": first_failure is None,
                    **(
                        {"stages": stage_reports}
                        if first_failure is not None
                        else {}
                    ),
                }
            )
            if first_failure is not None:
                break
    finally:
        _close_simulation(cpu)
        _close_simulation(gpu)
    return {
        "schema": PARITY_SCHEMA,
        "mode": "world-parity",
        "gpu_available": True,
        "passed": first_failure is None,
        "first_failure": first_failure,
        "ticks_compared": len(tick_reports),
        "ticks": tick_reports,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Locate the first CPU/GPU semantic divergence."
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ticks", type=int, default=5)
    parser.add_argument("--entities", type=int, default=64)
    parser.add_argument(
        "--device-backend",
        choices=("auto", "cpu", "gpu"),
        default="auto",
        help="Stage backend: cpu emulates device algorithms; auto also runs real GPU when available.",
    )
    parser.add_argument(
        "--world-only",
        action="store_true",
        help=(
            "Skip standalone stage checks and run only the paired CPU versus "
            "experimental hybrid world trace."
        ),
    )
    parser.add_argument(
        "--preserve-config-world",
        action="store_true",
        help=(
            "Keep the configuration's initial/max entity counts instead of "
            "building a reduced diagnostic world."
        ),
    )
    parser.add_argument(
        "--require-gpu",
        action="store_true",
        help="Return a failing exit status when no real GPU is available.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    cfg = _small_config(
        load_config(args.config),
        ticks=args.ticks,
        entities=args.entities,
        preserve_world=args.preserve_config_world,
    )
    report: dict[str, Any] = {
        "schema": PARITY_SCHEMA,
        "config": str(Path(args.config)),
        "ticks": int(args.ticks),
        "entities": (
            int(cfg.world.initial_entities)
            if args.preserve_config_world
            else int(args.entities)
        ),
        "preserve_config_world": bool(args.preserve_config_world),
        "world_gpu_mode": "hybrid-accelerated",
        "tolerance_policy": {
            "discrete": "bitwise-exact",
            "float_atol": DEFAULT_ATOL,
            "float_rtol": DEFAULT_RTOL,
            "decision_actions": "bitwise-exact",
        },
        "gpu_available": cupy_available(),
    }
    stage_backend = args.device_backend
    if stage_backend == "auto":
        stage_backend = "gpu" if cupy_available() else "cpu"
    if args.world_only:
        report["stage_parity"] = {
            "passed": True,
            "skipped": True,
            "reason": "--world-only",
        }
    else:
        try:
            report["stage_parity"] = run_stage_parity(
                cfg,
                backend_name=stage_backend,
                ticks=args.ticks,
                output_dir=output / "stage",
            )
        except BackendUnavailableError as exc:
            report["stage_parity"] = {
                "passed": False,
                "device_backend": stage_backend,
                "reason": str(exc),
            }
    if cupy_available():
        report["world_parity"] = run_world_parity(
            cfg, ticks=args.ticks, output_dir=output / "world"
        )
    else:
        report["world_parity"] = {
            "passed": False,
            "gpu_available": False,
            "reason": "Real GPU world parity was not run because CuPy/CUDA is unavailable.",
        }
    report["passed"] = bool(
        report.get("stage_parity", {}).get("passed")
        and (
            report.get("world_parity", {}).get("passed")
            if report["gpu_available"]
            else not args.require_gpu
        )
    )
    (output / "parity_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
