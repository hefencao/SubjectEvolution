"""Stage 3C-15 fixed-bootstrap local sensitivity and degeneracy audit.

This module performs bounded, external, one-step finite-difference probes on the
six generic Subject VM parameter families.  The probes are replayed from the
same quiescent source checkpoints and are never written back to a checkpoint or
interpreted as reward, value, causal credit, learning, or retention evidence.

Two operating contexts are inspected:

* the first activation after bootstrap, before the delayed edge has prior state;
* one unperturbed activation later, when the delayed edge can contribute.

The second context prevents a zero first-tick edge response from being mistaken
for permanent structural inactivity.  The analysis lives outside the runtime
and adds no checkpoint state or persistent diagnostic buffers.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..runtime.sim import Simulation
from ..subject_vm import LOCAL_ELIGIBILITY_FLAG
from ..subject_vm.config import SUBJECT_VM_MODULATION_TARGET_NAMES
from ..subject_vm.update_safety import PARAMETER_ARRAY_BY_FAMILY
from .subject_vm_stage3c13_exposure_adequacy import (
    _canonical_sha256,
    _load_json,
)

STAGE3C15_LOCAL_SENSITIVITY_SCHEMA = (
    "se-subject-vm-stage3c15-local-sensitivity-assessment-v1"
)

_CONTEXTS = ("first-post-bootstrap", "warmed-delayed-edge")
_TARGETS: tuple[tuple[str, str, int, str], ...] = (
    ("node_bias", "node_bias", 0, "node"),
    ("node_input_gate", "node_input_gate", 0, "node"),
    ("node_output_gate", "node_output_gate", 0, "node"),
    ("node_trace_gate", "node_trace_gate", 7, "node"),
    ("edge_forward_gate", "edge_forward_gate", 0, "edge"),
    ("edge_bandwidth", "edge_bandwidth", 0, "edge"),
)
_FAMILY_INDEX = {name.replace("-", "_"): index for index, name in enumerate(
    SUBJECT_VM_MODULATION_TARGET_NAMES
)}


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_study(study: dict[str, Any]) -> None:
    if study.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-15 requires a short paired study report")
    if study.get("parameters", {}).get("bootstrap_target_family") != "node_bias":
        raise ValueError("Stage-3C-15 requires the node-bias baseline bootstrap")
    summary = study.get("engineering_summary", {})
    if not bool(summary.get("stage3c7_engineering_screen_passed")):
        raise ValueError("Stage-3C-15 requires a passing Stage-3C-7 source panel")
    if not bool(summary.get("stage3c10_diagnostics_generated")):
        raise ValueError("Stage-3C-15 requires Stage-3C-10 diagnostics")
    if bool(study.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-15 cannot use a retention-authorized study")
    if bool(study.get("fixed_bootstrap_is_evolved_result")):
        raise ValueError("Stage-3C-15 requires an explicit fixed bootstrap")
    seeds = study.get("seeds", [])
    if len(seeds) < 3:
        raise ValueError("Stage-3C-15 requires at least three independent sources")


def _selected_rows(simulation: Simulation, subject_ids: Iterable[int]) -> np.ndarray:
    ids = np.asarray(tuple(int(value) for value in subject_ids), dtype=np.uint64)
    rows: list[int] = []
    for subject_id in ids.tolist():
        found = np.flatnonzero(
            simulation.entities.primary_subject_id == np.uint64(subject_id)
        )
        if found.size != 1:
            raise ValueError(
                f"bootstrap subject {subject_id} does not map to one entity row"
            )
        row = int(found[0])
        if not bool(simulation.entities.alive[row]):
            raise ValueError(f"bootstrap subject {subject_id} is not alive")
        rows.append(row)
    return np.asarray(rows, dtype=np.int32)


def _extract_event(
    simulation: Simulation,
    *,
    rows: np.ndarray,
    subject_ids: tuple[int, ...],
    event_tick: int,
) -> dict[str, np.ndarray]:
    trace = simulation.subject_vm.trace_storage
    if trace is None:
        raise ValueError("Stage-3C-15 source lacks trace storage")
    action_potentials: list[np.ndarray] = []
    thought_tokens: list[np.ndarray] = []
    probabilities: list[float] = []
    actions: list[int] = []
    objective: list[np.ndarray] = []
    resources: list[np.ndarray] = []
    internal_resources: list[np.ndarray] = []
    energy_cost: list[float] = []
    success: list[bool] = []
    for row, subject_id in zip(rows.tolist(), subject_ids, strict=True):
        slots = np.flatnonzero(
            trace.event_valid[row]
            & (trace.event_tick[row] == int(event_tick))
            & (trace.subject_id[row] == np.uint64(subject_id))
        )
        if slots.size != 1:
            raise ValueError(
                "Stage-3C-15 expected one trace event for "
                f"subject={subject_id}, tick={event_tick}; found {slots.size}"
            )
        slot = int(slots[0])
        action_potentials.append(trace.action_potentials[row, slot].copy())
        thought_tokens.append(trace.thought_token[row, slot].copy())
        probabilities.append(float(trace.sampled_probability[row, slot]))
        actions.append(int(trace.action_id[row, slot]))
        objective.append(trace.objective_delta[row, slot].copy())
        resources.append(trace.resolution_resource_delta[row, slot].copy())
        internal_resources.append(
            trace.resolution_internal_resource_delta[row, slot].copy()
        )
        energy_cost.append(float(trace.resolution_energy_cost[row, slot]))
        success.append(bool(trace.success[row, slot]))
    return {
        "action_potentials": np.asarray(action_potentials, dtype=np.float32),
        "thought_token": np.asarray(thought_tokens, dtype=np.float32),
        "sampled_probability": np.asarray(probabilities, dtype=np.float32),
        "action_id": np.asarray(actions, dtype=np.int16),
        "objective_delta": np.asarray(objective, dtype=np.float32),
        "resolution_resource_delta": np.asarray(resources, dtype=np.float32),
        "resolution_internal_resource_delta": np.asarray(
            internal_resources, dtype=np.float32
        ),
        "resolution_energy_cost": np.asarray(energy_cost, dtype=np.float32),
        "success": np.asarray(success, dtype=bool),
    }


def _finalize_quietly(simulation: Simulation) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        simulation.run(until_tick=simulation.tick)


def _target_descriptor(
    simulation: Simulation,
    *,
    rows: np.ndarray,
    family: str,
    array_name: str,
    target_index: int,
    kind: str,
    probe_delta: float,
) -> dict[str, Any]:
    storage = simulation.subject_vm.storage
    if storage is None:
        raise ValueError("Stage-3C-15 source lacks Subject VM storage")
    family_index = _FAMILY_INDEX[family]
    parameter = np.asarray(getattr(storage, array_name)[rows, target_index])
    safety = simulation.cfg.subject_vm.update_safety
    lower = float(safety.parameter_lower_bounds[family_index])
    upper = float(safety.parameter_upper_bounds[family_index])
    minus_allowed = bool(np.all(parameter - probe_delta >= lower - 1e-12))
    plus_allowed = bool(np.all(parameter + probe_delta <= upper + 1e-12))
    if kind == "node":
        expressed = np.asarray(storage.node_expressed[rows, target_index])
        flags = np.asarray(storage.node_plasticity_flags[rows, target_index])
        local_gate = np.asarray(storage.node_eligibility_gate[rows, target_index])
        target_live = expressed.copy()
        if family == "node_input_gate":
            target_live &= storage.node_input_port[rows, target_index] >= 0
        elif family == "node_output_gate":
            target_live &= storage.node_output_port[rows, target_index] >= 0
        elif family == "node_trace_gate":
            target_live &= storage.node_trace_port[rows, target_index] >= 0
    else:
        expressed = np.asarray(storage.edge_expressed[rows, target_index])
        flags = np.asarray(storage.plasticity_flags[rows, target_index])
        local_gate = np.asarray(storage.edge_eligibility_gate[rows, target_index])
        target_live = expressed.copy()
    eligible = (
        expressed
        & ((flags & np.uint8(LOCAL_ELIGIBILITY_FLAG)) != 0)
        & (local_gate != 0.0)
    )
    return {
        "family": family,
        "family_index": family_index,
        "parameter_array": array_name,
        "target_kind": kind,
        "target_index": int(target_index),
        "parameter_min": float(parameter.min()),
        "parameter_max": float(parameter.max()),
        "parameter_mean": float(parameter.mean(dtype=np.float64)),
        "lower_bound": lower,
        "upper_bound": upper,
        "family_delta_clip": float(safety.family_delta_clip[family_index]),
        "minus_probe_allowed_for_all_subjects": minus_allowed,
        "plus_probe_allowed_for_all_subjects": plus_allowed,
        "target_live_for_all_subjects": bool(np.all(target_live)),
        "local_eligibility_reachable_for_all_subjects": bool(np.all(eligible)),
        "local_eligibility_reachable_subject_count": int(np.count_nonzero(eligible)),
    }


def _edge_operating_point(simulation: Simulation, rows: np.ndarray) -> dict[str, Any]:
    storage = simulation.subject_vm.storage
    if storage is None or storage.edge_capacity < 1:
        raise ValueError("Stage-3C-15 requires bootstrap edge 0")
    source = storage.edge_source[rows, 0].astype(np.int64)
    if np.any(source < 0):
        raise ValueError("Stage-3C-15 bootstrap edge has no source")
    previous = storage.node_state[rows, source, 0].astype(np.float64)
    forward = storage.edge_forward_gate[rows, 0].astype(np.float64)
    bandwidth = storage.edge_bandwidth[rows, 0].astype(np.float64)
    raw = previous * forward
    margin = bandwidth - np.abs(raw)
    saturated = margin <= 1e-12
    return {
        "delayed_source_state_abs_mean": float(np.abs(previous).mean()),
        "raw_contribution_abs_mean": float(np.abs(raw).mean()),
        "raw_contribution_abs_max": float(np.abs(raw).max()),
        "bandwidth_mean": float(bandwidth.mean()),
        "minimum_saturation_margin": float(margin.min()),
        "saturated_subject_count": int(np.count_nonzero(saturated)),
        "subject_count": int(rows.size),
        "clamp_active_for_any_subject": bool(np.any(saturated)),
    }


def _mutate(
    simulation: Simulation,
    *,
    rows: np.ndarray,
    array_name: str,
    target_index: int,
    delta: float,
) -> None:
    storage = simulation.subject_vm.storage
    if storage is None:
        raise ValueError("Stage-3C-15 source lacks Subject VM storage")
    array = getattr(storage, array_name)
    array[rows, target_index] = (
        array[rows, target_index].astype(np.float64) + float(delta)
    ).astype(np.float32)
    storage.validate_internal()


def _response_hash(response: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for key in sorted(response):
        array = np.ascontiguousarray(response[key])
        digest.update(key.encode("utf-8"))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes())
    return digest.hexdigest()


def _difference_metrics(
    baseline: dict[str, np.ndarray], probe: dict[str, np.ndarray]
) -> dict[str, Any]:
    ap = probe["action_potentials"].astype(np.float64) - baseline[
        "action_potentials"
    ].astype(np.float64)
    token = probe["thought_token"].astype(np.float64) - baseline[
        "thought_token"
    ].astype(np.float64)
    probability = probe["sampled_probability"].astype(np.float64) - baseline[
        "sampled_probability"
    ].astype(np.float64)
    objective_arrays = (
        "objective_delta",
        "resolution_resource_delta",
        "resolution_internal_resource_delta",
        "resolution_energy_cost",
        "success",
    )
    objective_difference = np.zeros(probe["action_id"].shape, dtype=bool)
    for name in objective_arrays:
        left = np.asarray(baseline[name])
        right = np.asarray(probe[name])
        if left.ndim == 1:
            objective_difference |= left != right
        else:
            objective_difference |= np.any(left != right, axis=tuple(range(1, left.ndim)))
    action_difference = probe["action_id"] != baseline["action_id"]
    return {
        "action_potential_l1": float(np.abs(ap).sum()),
        "action_potential_max_abs": float(np.abs(ap).max(initial=0.0)),
        "action_potential_nonzero_subject_count": int(
            np.count_nonzero(np.any(ap != 0.0, axis=1))
        ),
        "thought_token_l1": float(np.abs(token).sum()),
        "thought_token_max_abs": float(np.abs(token).max(initial=0.0)),
        "thought_token_nonzero_subject_count": int(
            np.count_nonzero(np.any(token != 0.0, axis=1))
        ),
        "sampled_probability_l1": float(np.abs(probability).sum()),
        "sampled_probability_max_abs": float(
            np.abs(probability).max(initial=0.0)
        ),
        "sampled_probability_nonzero_subject_count": int(
            np.count_nonzero(probability != 0.0)
        ),
        "discrete_action_difference_count": int(np.count_nonzero(action_difference)),
        "objective_event_difference_count": int(
            np.count_nonzero(objective_difference)
        ),
        "probe_response_sha256": _response_hash(probe),
    }


def _derivative_metrics(
    *,
    baseline: dict[str, np.ndarray],
    minus: dict[str, np.ndarray] | None,
    plus: dict[str, np.ndarray] | None,
    probe_delta: float,
) -> dict[str, Any]:
    if minus is not None and plus is not None:
        scheme = "centered"
        denominator = 2.0 * probe_delta
        left = minus
        right = plus
    elif minus is not None:
        scheme = "inward-one-sided-from-minus-to-baseline"
        denominator = probe_delta
        left = minus
        right = baseline
    elif plus is not None:
        scheme = "one-sided-from-baseline-to-plus"
        denominator = probe_delta
        left = baseline
        right = plus
    else:
        return {
            "scheme": "unavailable-at-parameter-bounds",
            "action_potential_derivative_l1": 0.0,
            "action_potential_derivative_max_abs": 0.0,
            "thought_token_derivative_l1": 0.0,
            "thought_token_derivative_max_abs": 0.0,
            "sampled_probability_derivative_l1": 0.0,
            "sampled_probability_derivative_max_abs": 0.0,
        }
    ap = (right["action_potentials"].astype(np.float64) - left[
        "action_potentials"
    ].astype(np.float64)) / denominator
    token = (right["thought_token"].astype(np.float64) - left[
        "thought_token"
    ].astype(np.float64)) / denominator
    probability = (right["sampled_probability"].astype(np.float64) - left[
        "sampled_probability"
    ].astype(np.float64)) / denominator
    return {
        "scheme": scheme,
        "action_potential_derivative_l1": float(np.abs(ap).sum()),
        "action_potential_derivative_max_abs": float(
            np.abs(ap).max(initial=0.0)
        ),
        "action_potential_derivative_nonzero_subject_count": int(
            np.count_nonzero(np.any(ap != 0.0, axis=1))
        ),
        "thought_token_derivative_l1": float(np.abs(token).sum()),
        "thought_token_derivative_max_abs": float(
            np.abs(token).max(initial=0.0)
        ),
        "thought_token_derivative_nonzero_subject_count": int(
            np.count_nonzero(np.any(token != 0.0, axis=1))
        ),
        "sampled_probability_derivative_l1": float(np.abs(probability).sum()),
        "sampled_probability_derivative_max_abs": float(
            np.abs(probability).max(initial=0.0)
        ),
        "sampled_probability_derivative_nonzero_subject_count": int(
            np.count_nonzero(probability != 0.0)
        ),
    }


def _probe_branch(
    parent: Simulation,
    *,
    output_dir: Path,
    subject_ids: tuple[int, ...],
    array_name: str | None = None,
    target_index: int = 0,
    delta: float = 0.0,
) -> tuple[dict[str, np.ndarray], int]:
    branch = parent.clone(output_dir)
    rows = _selected_rows(branch, subject_ids)
    if array_name is not None:
        _mutate(
            branch,
            rows=rows,
            array_name=array_name,
            target_index=target_index,
            delta=delta,
        )
    event_tick = int(branch.tick)
    branch.step()
    response = _extract_event(
        branch, rows=rows, subject_ids=subject_ids, event_tick=event_tick
    )
    _finalize_quietly(branch)
    return response, event_tick


def _aggregate_numeric(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = np.asarray([float(record[key]) for record in records], dtype=np.float64)
    return {
        "sum": float(values.sum()),
        "mean": float(values.mean()),
        "min": float(values.min()),
        "max": float(values.max()),
        "nonzero_source_count": int(np.count_nonzero(values != 0.0)),
    }


def _aggregate_context_family(records: list[dict[str, Any]]) -> dict[str, Any]:
    derivative_keys = (
        "action_potential_derivative_l1",
        "action_potential_derivative_max_abs",
        "thought_token_derivative_l1",
        "thought_token_derivative_max_abs",
        "sampled_probability_derivative_l1",
        "sampled_probability_derivative_max_abs",
    )
    result = {
        key: _aggregate_numeric([record["finite_difference"] for record in records], key)
        for key in derivative_keys
    }
    for direction in ("minus", "plus"):
        available = [record[direction] for record in records if record[direction] is not None]
        result[f"{direction}_probe_available_source_count"] = len(available)
        result[f"{direction}_discrete_action_difference_count"] = int(
            sum(int(record["discrete_action_difference_count"]) for record in available)
        )
        result[f"{direction}_objective_event_difference_count"] = int(
            sum(int(record["objective_event_difference_count"]) for record in available)
        )
    result["finite_difference_schemes"] = sorted(
        {record["finite_difference"]["scheme"] for record in records}
    )
    return result


def assess_stage3c15_local_sensitivity(
    study: dict[str, Any],
    *,
    probe_delta: float = 0.05,
    work_root: str | Path | None = None,
) -> dict[str, Any]:
    """Replay bounded local probes from every independent source checkpoint."""
    _validate_study(study)
    if not np.isfinite(probe_delta) or not 0.0 < float(probe_delta) <= 0.1:
        raise ValueError("Stage-3C-15 probe_delta must be in (0, 0.1]")

    own_temp: tempfile.TemporaryDirectory[str] | None = None
    if work_root is None:
        own_temp = tempfile.TemporaryDirectory(prefix="se-stage3c15-")
        root = Path(own_temp.name)
    else:
        root = Path(work_root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)

    per_source: list[dict[str, Any]] = []
    internal_responses: dict[
        tuple[int, str, str, str], dict[str, np.ndarray]
    ] = {}
    try:
        for seed_record in sorted(study["seeds"], key=lambda item: int(item["seed"])):
            seed = int(seed_record["seed"])
            source_checkpoint = Path(seed_record["source_checkpoint"]).resolve()
            if not source_checkpoint.is_file():
                raise FileNotFoundError(source_checkpoint)
            if _sha256_file(source_checkpoint) != seed_record[
                "source_checkpoint_file_sha256"
            ]:
                raise ValueError(f"source checkpoint file hash mismatch for seed {seed}")
            subject_ids = tuple(
                int(value)
                for value in seed_record["bootstrap_lineage"]["primed_subject_ids"]
            )
            source_dir = root / f"seed_{seed}"
            source = Simulation.from_checkpoint(
                source_checkpoint, source_dir / "source", backend="cpu"
            )
            rows = _selected_rows(source, subject_ids)
            storage = source.subject_vm.storage
            if storage is None:
                raise ValueError("Stage-3C-15 source lacks Subject VM storage")
            if np.any(source.subject_vm.trace_storage.event_valid):
                raise ValueError("Stage-3C-15 source checkpoint trace must be quiescent")

            descriptors = {
                family: _target_descriptor(
                    source,
                    rows=rows,
                    family=family,
                    array_name=array_name,
                    target_index=target_index,
                    kind=kind,
                    probe_delta=float(probe_delta),
                )
                for family, array_name, target_index, kind in _TARGETS
            }
            cold_edge = _edge_operating_point(source, rows)

            warm_parent = source.clone(source_dir / "warm-parent")
            warm_tick = int(warm_parent.tick)
            warm_parent.step()
            cold_baseline = _extract_event(
                warm_parent,
                rows=rows,
                subject_ids=subject_ids,
                event_tick=warm_tick,
            )
            internal_responses[(seed, _CONTEXTS[0], "baseline", "baseline")] = (
                cold_baseline
            )
            warm_rows = _selected_rows(warm_parent, subject_ids)
            warm_edge = _edge_operating_point(warm_parent, warm_rows)

            context_parents = {
                _CONTEXTS[0]: source,
                _CONTEXTS[1]: warm_parent,
            }
            context_baselines: dict[str, dict[str, np.ndarray]] = {
                _CONTEXTS[0]: cold_baseline
            }
            warm_baseline, warm_event_tick = _probe_branch(
                warm_parent,
                output_dir=source_dir / "warmed-baseline",
                subject_ids=subject_ids,
            )
            context_baselines[_CONTEXTS[1]] = warm_baseline
            internal_responses[(seed, _CONTEXTS[1], "baseline", "baseline")] = (
                warm_baseline
            )

            context_records: dict[str, Any] = {}
            for context, parent in context_parents.items():
                baseline = context_baselines[context]
                families: dict[str, Any] = {}
                for family, array_name, target_index, _kind in _TARGETS:
                    descriptor = descriptors[family]
                    minus_response = None
                    plus_response = None
                    minus_metrics = None
                    plus_metrics = None
                    if descriptor["minus_probe_allowed_for_all_subjects"]:
                        minus_response, _ = _probe_branch(
                            parent,
                            output_dir=source_dir / context / family / "minus",
                            subject_ids=subject_ids,
                            array_name=array_name,
                            target_index=target_index,
                            delta=-float(probe_delta),
                        )
                        minus_metrics = _difference_metrics(baseline, minus_response)
                        internal_responses[(seed, context, family, "minus")] = (
                            minus_response
                        )
                    if descriptor["plus_probe_allowed_for_all_subjects"]:
                        plus_response, _ = _probe_branch(
                            parent,
                            output_dir=source_dir / context / family / "plus",
                            subject_ids=subject_ids,
                            array_name=array_name,
                            target_index=target_index,
                            delta=float(probe_delta),
                        )
                        plus_metrics = _difference_metrics(baseline, plus_response)
                        internal_responses[(seed, context, family, "plus")] = (
                            plus_response
                        )
                    families[family] = {
                        "descriptor": descriptor,
                        "minus": minus_metrics,
                        "plus": plus_metrics,
                        "finite_difference": _derivative_metrics(
                            baseline=baseline,
                            minus=minus_response,
                            plus=plus_response,
                            probe_delta=float(probe_delta),
                        ),
                    }
                context_records[context] = {
                    "event_tick": (
                        int(warm_tick)
                        if context == _CONTEXTS[0]
                        else int(warm_event_tick)
                    ),
                    "baseline_response_sha256": _response_hash(baseline),
                    "edge_operating_point": (
                        cold_edge if context == _CONTEXTS[0] else warm_edge
                    ),
                    "families": families,
                }

            _finalize_quietly(warm_parent)
            _finalize_quietly(source)
            per_source.append(
                {
                    "seed": seed,
                    "source_checkpoint_state_sha256": seed_record[
                        "source_checkpoint_state_sha256"
                    ],
                    "source_checkpoint_config_sha256": seed_record[
                        "pre_bootstrap_checkpoint_config_sha256"
                    ],
                    "bootstrap_subject_count": len(subject_ids),
                    "contexts": context_records,
                }
            )
    finally:
        if own_temp is not None:
            own_temp.cleanup()

    aggregate: dict[str, Any] = {"contexts": {}}
    for context in _CONTEXTS:
        family_aggregate: dict[str, Any] = {}
        for family, *_ in _TARGETS:
            records = [
                source_record["contexts"][context]["families"][family]
                for source_record in per_source
            ]
            family_aggregate[family] = _aggregate_context_family(records)
            family_aggregate[family]["target_descriptor"] = records[0]["descriptor"]
            if any(record["descriptor"] != records[0]["descriptor"] for record in records):
                raise ValueError(
                    f"Stage-3C-15 target descriptor varies across sources: {family}"
                )
        edge_records = [
            source_record["contexts"][context]["edge_operating_point"]
            for source_record in per_source
        ]
        aggregate["contexts"][context] = {
            "families": family_aggregate,
            "edge_operating_point": {
                "clamp_active_source_count": int(
                    sum(bool(record["clamp_active_for_any_subject"]) for record in edge_records)
                ),
                "saturated_subject_count": int(
                    sum(int(record["saturated_subject_count"]) for record in edge_records)
                ),
                "minimum_saturation_margin": float(
                    min(float(record["minimum_saturation_margin"]) for record in edge_records)
                ),
                "raw_contribution_abs_max": float(
                    max(float(record["raw_contribution_abs_max"]) for record in edge_records)
                ),
            },
        }

    equivalence_mismatches = 0
    equivalence_max_abs = 0.0
    for seed_record in per_source:
        seed = int(seed_record["seed"])
        for context in _CONTEXTS:
            for direction in ("minus", "plus"):
                left = internal_responses[(seed, context, "node_bias", direction)]
                right = internal_responses[
                    (seed, context, "node_input_gate", direction)
                ]
                for key in left:
                    if not np.array_equal(left[key], right[key]):
                        equivalence_mismatches += 1
                        if np.issubdtype(left[key].dtype, np.number):
                            equivalence_max_abs = max(
                                equivalence_max_abs,
                                float(
                                    np.max(
                                        np.abs(
                                            left[key].astype(np.float64)
                                            - right[key].astype(np.float64)
                                        ),
                                        initial=0.0,
                                    )
                                ),
                            )

    cold = aggregate["contexts"][_CONTEXTS[0]]["families"]
    warm = aggregate["contexts"][_CONTEXTS[1]]["families"]
    payload = {
        "schema": STAGE3C15_LOCAL_SENSITIVITY_SCHEMA,
        "producer_version": __version__,
        "source_study_sha256": study["study_sha256"],
        "independent_source_count": len(per_source),
        "seeds": [int(record["seed"]) for record in per_source],
        "probe_contract": {
            "probe_delta": float(probe_delta),
            "family_delta_clips": {
                family: float(
                    aggregate["contexts"][_CONTEXTS[0]]["families"][family][
                        "target_descriptor"
                    ]["family_delta_clip"]
                )
                for family, *_ in _TARGETS
            },
            "external_finite_difference_only": True,
            "writes_persisted_to_source_checkpoint": False,
            "permanent_parameter_retention": False,
            "random_draw_contract_changed": False,
            "topology_changed": False,
            "association_selector_changed": False,
            "objective_value_semantics": None,
            "contexts": list(_CONTEXTS),
            "target_map": [
                {
                    "family": family,
                    "array": array_name,
                    "target_index": target_index,
                    "target_kind": kind,
                }
                for family, array_name, target_index, kind in _TARGETS
            ],
        },
        "aggregate": aggregate,
        "algebraic_degeneracy": {
            "node_bias_vs_node_input_gate_exact_probe_equivalence": bool(
                equivalence_mismatches == 0
            ),
            "node_bias_vs_node_input_gate_numerically_equivalent_within_float32_tolerance": bool(
                equivalence_max_abs <= 1e-7
            ),
            "float32_equivalence_tolerance": 1e-7,
            "mismatched_response_array_count": int(equivalence_mismatches),
            "maximum_absolute_response_difference": float(equivalence_max_abs),
            "operating_reason": (
                "bootstrap node 0 reads objective input port 0, which is the "
                "frozen constant-one coordinate; equal bias and input-gate "
                "perturbations therefore enter the accumulator identically"
            ),
            "general_graph_equivalence_claim": False,
        },
        "reachability_vs_sensitivity": {
            family: {
                "local_eligibility_reachable": bool(
                    cold[family]["target_descriptor"][
                        "local_eligibility_reachable_for_all_subjects"
                    ]
                ),
                "first_context_action_sensitive": bool(
                    cold[family]["action_potential_derivative_l1"]["sum"] > 0.0
                ),
                "warmed_context_action_sensitive": bool(
                    warm[family]["action_potential_derivative_l1"]["sum"] > 0.0
                ),
                "first_context_token_sensitive": bool(
                    cold[family]["thought_token_derivative_l1"]["sum"] > 0.0
                ),
                "warmed_context_token_sensitive": bool(
                    warm[family]["thought_token_derivative_l1"]["sum"] > 0.0
                ),
            }
            for family, *_ in _TARGETS
        },
        "diagnostic_findings": {
            "node_bias_and_input_gate_degenerate_in_this_bootstrap": bool(
                equivalence_max_abs <= 1e-7
            ),
            "edge_forward_gate_requires_warmed_delayed_context": bool(
                cold["edge_forward_gate"]["action_potential_derivative_l1"]["sum"]
                == 0.0
                and warm["edge_forward_gate"]["action_potential_derivative_l1"][
                    "sum"
                ]
                > 0.0
            ),
            "node_trace_gate_is_token_channel_only_at_probe_horizon": bool(
                cold["node_trace_gate"]["action_potential_derivative_l1"]["sum"]
                == 0.0
                and cold["node_trace_gate"]["thought_token_derivative_l1"]["sum"]
                > 0.0
            ),
            "edge_bandwidth_clamp_inactive_in_both_contexts": bool(
                aggregate["contexts"][_CONTEXTS[0]]["edge_operating_point"][
                    "clamp_active_source_count"
                ]
                == 0
                and aggregate["contexts"][_CONTEXTS[1]]["edge_operating_point"][
                    "clamp_active_source_count"
                ]
                == 0
            ),
            "edge_bandwidth_locally_zero_at_current_operating_points": bool(
                cold["edge_bandwidth"]["action_potential_derivative_l1"]["sum"]
                == 0.0
                and warm["edge_bandwidth"]["action_potential_derivative_l1"][
                    "sum"
                ]
                == 0.0
            ),
            "sensitive_but_not_currently_eligibility_reachable_families": sorted(
                family
                for family, details in {
                    family: {
                        "reachable": cold[family]["target_descriptor"][
                            "local_eligibility_reachable_for_all_subjects"
                        ],
                        "sensitive": (
                            cold[family]["action_potential_derivative_l1"]["sum"]
                            > 0.0
                            or warm[family]["action_potential_derivative_l1"]["sum"]
                            > 0.0
                            or cold[family]["thought_token_derivative_l1"]["sum"]
                            > 0.0
                            or warm[family]["thought_token_derivative_l1"]["sum"]
                            > 0.0
                        ),
                    }
                    for family, *_ in _TARGETS
                }.items()
                if details["sensitive"] and not details["reachable"]
            ),
        },
        "per_source": per_source,
        "interpretation_boundary": {
            "more_local_sensitivity_is_better": False,
            "zero_local_sensitivity_proves_family_useless": False,
            "finite_difference_is_causal_credit": False,
            "learning_claim_authorized": False,
            "subjecthood_claim_authorized": False,
            "permanent_parameter_retention_authorized": False,
            "automatic_keep_or_revert_authorized": False,
            "universal_attention_claim": False,
            "next_authorized_step": (
                "Use sensitivity and eligibility reachability as separate facts. "
                "A later bootstrap adjustment may expose one currently sensitive "
                "but unreachable carrier, one variable at a time, without value "
                "semantics or permanent retention."
            ),
        },
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def assess_from_path(
    *,
    study_report: str | Path,
    probe_delta: float = 0.05,
    work_root: str | Path | None = None,
) -> dict[str, Any]:
    return assess_stage3c15_local_sensitivity(
        _load_json(study_report), probe_delta=probe_delta, work_root=work_root
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess Stage-3C-15 fixed-bootstrap local sensitivity."
    )
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--probe-delta", type=float, default=0.05)
    parser.add_argument("--work-root")
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_from_path(
        study_report=args.study_report,
        probe_delta=args.probe_delta,
        work_root=args.work_root,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "assessment_sha256": result["assessment_sha256"],
                "diagnostic_findings": result["diagnostic_findings"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C15_LOCAL_SENSITIVITY_SCHEMA",
    "assess_stage3c15_local_sensitivity",
    "assess_from_path",
]
