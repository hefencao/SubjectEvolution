"""Stage 3C-42 REST activation-contribution source audit.

This read-only analysis consumes the targeted Stage-3C-42 activation traces.
It decomposes the guarded-live/read-only-control REST output difference into
current edge-gate, inherited node-state, interaction and numerical residual
terms, then compares the 3-tick and 6-tick exposure conditions.  Execution
contribution is not causal attribution, value or credit quality.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from ..experiments.subject_vm_stage3c42_activation_source import (
    STAGE3C42_ACTIVATION_SOURCE_STUDY_SCHEMA,
)
from ..runtime.categorical_sampling_trace import (
    CATEGORICAL_SAMPLING_TRACE_MANIFEST_SCHEMA,
)
from ..runtime.subject_vm_activation_contribution_trace import (
    SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_MANIFEST_SCHEMA,
)
from .subject_vm_stage3c40_categorical_boundary import (
    STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA,
)
from .subject_vm_stage3c41_pressure_source import (
    STAGE3C41_PRESSURE_SOURCE_ASSESSMENT_SCHEMA,
)

STAGE3C42_ACTIVATION_SOURCE_ASSESSMENT_SCHEMA = (
    "se-subject-vm-stage3c42-activation-source-assessment-v1"
)
_TOL = 1.0e-10
_MODES = ("aligned", "alignment-ablated")
_CONDITIONS = ("horizon-control", "extended-exposure")
_ROLES = ("read-only-control", "guarded-live")


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_checksum(payload: dict[str, Any], *, field: str, label: str) -> None:
    recorded = str(payload.get(field, ""))
    unsigned = dict(payload)
    unsigned.pop(field, None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")


def _stats(values: Iterable[float | int]) -> dict[str, Any]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {"count": 0, "minimum": None, "median": None, "maximum": None, "mean": None}
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "median": float(np.median(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _trace_events(
    manifest_path: str | Path, *, activation: bool
) -> tuple[dict[tuple[int, int, int], dict[str, Any]], dict[str, Any]]:
    manifest_path = Path(manifest_path).resolve()
    manifest = _load_json(manifest_path)
    expected_schema = (
        SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_MANIFEST_SCHEMA
        if activation
        else CATEGORICAL_SAMPLING_TRACE_MANIFEST_SCHEMA
    )
    if manifest.get("schema") != expected_schema:
        raise ValueError("Stage-3C-42 trace manifest schema mismatch")
    _validate_checksum(
        manifest, field="manifest_sha256", label="Stage-3C-42 trace manifest"
    )
    trace_name = (
        "subject_vm_activation_contribution_trace.jsonl"
        if activation
        else "categorical_sampling_trace.jsonl"
    )
    trace_path = manifest_path.with_name(trace_name)
    if _sha256(trace_path) != str(manifest["trace_sha256"]):
        raise ValueError("Stage-3C-42 trace file checksum mismatch")
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    if not lines or json.loads(lines[0]).get("record_type") != "header":
        raise ValueError("Stage-3C-42 trace header is missing")
    result: dict[tuple[int, int, int], dict[str, Any]] = {}
    for line in lines[1:]:
        record = json.loads(line)
        key = (int(record["subject_id"]), int(record["tick"]), int(record["event_id"]))
        if key in result:
            raise ValueError("Stage-3C-42 trace contains duplicate event identity")
        result[key] = record
    if len(result) != int(manifest["event_count"]):
        raise ValueError("Stage-3C-42 trace event count mismatch")
    return result, manifest


def _rest_path(record: dict[str, Any]) -> dict[str, Any]:
    outputs = [item for item in record["output_contributions"] if int(item["action_port"]) == 0]
    if len(outputs) != 1:
        raise ValueError("Stage-3C-42 requires exactly one REST output contribution")
    output = outputs[0]
    node_index = int(output["node_index"])
    nodes = [item for item in record["node_activations"] if int(item["node_index"]) == node_index]
    if len(nodes) != 1:
        raise ValueError("Stage-3C-42 REST output node is missing or ambiguous")
    node = nodes[0]
    edges = [item for item in record["edge_transmissions"] if int(item["target_node_index"]) == node_index]
    if len(edges) != 1:
        raise ValueError("Stage-3C-42 requires one recurrent REST edge")
    edge = edges[0]
    if int(edge["source_node_index"]) != node_index or int(edge["delay"]) != 1:
        raise ValueError("Stage-3C-42 REST edge is not the frozen delay-one self edge")
    return {"node": node, "edge": edge, "output": output}


def _write_targets(record: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for entry in record.get("temporary_write_lineage", []):
        for target in entry.get("targets", []):
            targets.append(
                {
                    "status_name": str(entry["status_name"]),
                    "source_event_id": int(entry["source_event_id"]),
                    "applied_tick": int(entry["applied_tick"]),
                    "rollback_due_tick": int(entry["rollback_due_tick"]),
                    **target,
                }
            )
    return targets


def _live_control_decomposition(
    control_record: dict[str, Any], live_record: dict[str, Any]
) -> dict[str, Any]:
    identity_fields = ("subject_id", "tick", "event_id", "entity_id")
    for field in identity_fields:
        if int(control_record[field]) != int(live_record[field]):
            raise ValueError("Stage-3C-42 live/control event identity mismatch")
    control = _rest_path(control_record)
    live = _rest_path(live_record)
    c_node, l_node = control["node"], live["node"]
    c_edge, l_edge = control["edge"], live["edge"]
    c_out, l_out = control["output"], live["output"]
    if int(c_node["operator_id"]) != 0 or int(l_node["operator_id"]) != 0:
        raise ValueError("Stage-3C-42 frozen REST node must remain linear")
    if bool(c_node["activation_clip_applied"]) or bool(l_node["activation_clip_applied"]):
        raise ValueError("Stage-3C-42 REST node activation clipping is unsupported")
    if bool(c_edge["bandwidth_clip_applied"]) or bool(l_edge["bandwidth_clip_applied"]):
        raise ValueError("Stage-3C-42 recurrent edge bandwidth clipping is unsupported")

    source_control = float(c_edge["source_value"])
    source_live = float(l_edge["source_value"])
    gate_control = float(c_edge["forward_gate"])
    gate_live = float(l_edge["forward_gate"])
    source_delta = source_live - source_control
    gate_delta = gate_live - gate_control
    inherited_state_driver = source_delta * gate_control
    current_gate_driver = source_control * gate_delta
    state_gate_interaction = source_delta * gate_delta
    edge_delta = float(l_edge["bounded_contribution"]) - float(c_edge["bounded_contribution"])
    edge_residual = edge_delta - (
        inherited_state_driver + current_gate_driver + state_gate_interaction
    )

    bias_driver = float(l_node["bias_value"]) - float(c_node["bias_value"])
    input_driver = float(l_node["input_contribution"]) - float(c_node["input_contribution"])
    node_delta = float(l_node["node_value"]) - float(c_node["node_value"])
    node_residual = node_delta - (bias_driver + input_driver + edge_delta)

    output_gate_control = float(c_out["output_gate"])
    output_gate_live = float(l_out["output_gate"])
    output_gate_delta = output_gate_live - output_gate_control
    node_change_output_driver = node_delta * output_gate_control
    output_gate_driver = float(c_node["node_value"]) * output_gate_delta
    node_gate_interaction = node_delta * output_gate_delta
    rest_output_delta = float(l_out["float32_contribution"]) - float(
        c_out["float32_contribution"]
    )
    output_residual = rest_output_delta - (
        node_change_output_driver + output_gate_driver + node_gate_interaction
    )

    component_output = {
        "inherited_node_state": inherited_state_driver * output_gate_control,
        "current_edge_gate": current_gate_driver * output_gate_control,
        "state_gate_interaction": state_gate_interaction * output_gate_control,
        "input": input_driver * output_gate_control,
        "bias": bias_driver * output_gate_control,
        "edge_numerical_residual": edge_residual * output_gate_control,
        "node_numerical_residual": node_residual * output_gate_control,
        "output_gate": output_gate_driver,
        "node_output_gate_interaction": node_gate_interaction,
        "output_numerical_residual": output_residual,
    }
    reconstructed = float(sum(component_output.values()))
    if abs(reconstructed - rest_output_delta) > _TOL:
        raise ValueError("Stage-3C-42 REST output decomposition is not exact")

    control_targets = _write_targets(control_record)
    live_targets = _write_targets(live_record)
    edge_targets = [
        item
        for item in control_targets + live_targets
        if str(item.get("family_name")) == "edge-forward-gate"
        and int(item.get("target_index", -1)) == int(c_edge["edge_index"])
    ]
    foreign_targets = [
        item
        for item in control_targets + live_targets
        if str(item.get("family_name")) != "edge-forward-gate"
    ]
    return {
        "rest_output_control": float(c_out["float32_contribution"]),
        "rest_output_live": float(l_out["float32_contribution"]),
        "rest_output_live_minus_control": rest_output_delta,
        "source_state_control": source_control,
        "source_state_live": source_live,
        "source_state_delta": source_delta,
        "edge_gate_control": gate_control,
        "edge_gate_live": gate_live,
        "edge_gate_delta": gate_delta,
        "component_output_contributions": component_output,
        "absolute_reconstruction_error": abs(reconstructed - rest_output_delta),
        "control_temporary_write_targets": control_targets,
        "live_temporary_write_targets": live_targets,
        "edge_forward_gate_target_count": len(edge_targets),
        "foreign_target_count": len(foreign_targets),
    }


def _opportunity(stage3c40: dict[str, Any], *, panel: str, seed: int, key: tuple[int, int, int]) -> dict[str, Any]:
    records = [
        item
        for item in stage3c40["panels"][panel]["per_source"]
        if int(item["seed"]) == seed
    ]
    if len(records) != 1:
        raise ValueError("Stage-3C-42 source opportunity is missing")
    for item in records[0]["top_boundary_opportunities"]:
        candidate = (int(item["subject_id"]), int(item["tick"]), int(item["event_id"]))
        if candidate == key:
            return item
    raise ValueError("Stage-3C-42 frozen opportunity event is missing")


def _source_category(panel: str, seed: int) -> str:
    if panel == "replication":
        return "replication-highest-opportunity-noncrossing"
    if seed in (12305, 12308):
        return "reference-alignment-differential-crossing"
    if seed == 12307:
        return "reference-alignment-common-crossing"
    raise ValueError("Stage-3C-42 contains an unauthorized source category")


def assess_stage3c42_activation_source(
    study: dict[str, Any],
    stage3c40: dict[str, Any],
    stage3c41: dict[str, Any],
    integrity: dict[str, Any],
) -> dict[str, Any]:
    if study.get("schema") != STAGE3C42_ACTIVATION_SOURCE_STUDY_SCHEMA:
        raise ValueError("unsupported Stage-3C-42 study schema")
    _validate_checksum(study, field="study_sha256", label="Stage-3C-42 study")
    if stage3c40.get("schema") != STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA:
        raise ValueError("unsupported Stage-3C-40 assessment schema")
    _validate_checksum(stage3c40, field="assessment_sha256", label="Stage-3C-40 assessment")
    if stage3c41.get("schema") != STAGE3C41_PRESSURE_SOURCE_ASSESSMENT_SCHEMA:
        raise ValueError("unsupported Stage-3C-41 assessment schema")
    _validate_checksum(stage3c41, field="assessment_sha256", label="Stage-3C-41 assessment")
    _validate_checksum(integrity, field="assessment_sha256", label="activation trace integrity")
    checks = study["input_checksums"]
    if checks["stage3c40_assessment"] != stage3c40["assessment_sha256"]:
        raise ValueError("Stage-3C-42 Stage-3C-40 lineage mismatch")
    if checks["stage3c41_assessment"] != stage3c41["assessment_sha256"]:
        raise ValueError("Stage-3C-42 Stage-3C-41 lineage mismatch")
    if checks["activation_trace_integrity"] != integrity["assessment_sha256"]:
        raise ValueError("Stage-3C-42 activation trace lineage mismatch")

    trace_cache: dict[tuple[str, bool], dict[tuple[int, int, int], dict[str, Any]]] = {}
    trace_identity: list[str] = []

    def events(path: str, *, activation: bool) -> dict[tuple[int, int, int], dict[str, Any]]:
        key = (str(Path(path).resolve()), activation)
        if key not in trace_cache:
            loaded, manifest = _trace_events(path, activation=activation)
            trace_cache[key] = loaded
            trace_identity.append(str(manifest["manifest_sha256"]))
            trace_identity.append(str(manifest["trace_sha256"]))
        return trace_cache[key]

    event_records: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    target_family_counter: Counter[str] = Counter()
    all_errors: list[float] = []

    for source in study["sources"]:
        panel = str(source["panel"])
        seed = int(source["seed"])
        source_records: list[dict[str, Any]] = []
        for selected in source["selected_events"]:
            key = (
                int(selected["subject_id"]),
                int(selected["tick"]),
                int(selected["event_id"]),
            )
            frozen = _opportunity(stage3c40, panel=panel, seed=seed, key=key)
            for mode in _MODES:
                branch_records: dict[tuple[str, str], dict[str, Any]] = {}
                categorical_records: dict[tuple[str, str], dict[str, Any]] = {}
                for condition in _CONDITIONS:
                    mode_report = source["conditions"][condition][mode]
                    for role in _ROLES:
                        activation_manifest = mode_report[
                            "activation_contribution_trace_manifests"
                        ][role]
                        categorical_manifest = mode_report[
                            "categorical_sampling_trace_manifests"
                        ][role]
                        activation_map = events(activation_manifest, activation=True)
                        categorical_map = events(categorical_manifest, activation=False)
                        if key not in activation_map or key not in categorical_map:
                            raise ValueError("Stage-3C-42 selected event is absent from trace")
                        branch_records[(condition, role)] = activation_map[key]
                        categorical_records[(condition, role)] = categorical_map[key]

                horizon = _live_control_decomposition(
                    branch_records[("horizon-control", "read-only-control")],
                    branch_records[("horizon-control", "guarded-live")],
                )
                extended = _live_control_decomposition(
                    branch_records[("extended-exposure", "read-only-control")],
                    branch_records[("extended-exposure", "guarded-live")],
                )
                all_errors.extend(
                    [horizon["absolute_reconstruction_error"], extended["absolute_reconstruction_error"]]
                )
                for decomposition in (horizon, extended):
                    for target in (
                        decomposition["control_temporary_write_targets"]
                        + decomposition["live_temporary_write_targets"]
                    ):
                        target_family_counter[str(target["family_name"])] += 1
                    if decomposition["foreign_target_count"]:
                        raise ValueError("Stage-3C-42 observed a non-edge target family")

                component_names = tuple(horizon["component_output_contributions"])
                did_components = {
                    name: float(
                        extended["component_output_contributions"][name]
                        - horizon["component_output_contributions"][name]
                    )
                    for name in component_names
                }
                horizon_effect = float(horizon["rest_output_live_minus_control"])
                extended_effect = float(extended["rest_output_live_minus_control"])
                did_rest = extended_effect - horizon_effect
                did_reconstructed = float(sum(did_components.values()))
                if abs(did_rest - did_reconstructed) > _TOL:
                    raise ValueError("Stage-3C-42 exposure DID decomposition is not exact")

                cat_h_live = categorical_records[("horizon-control", "guarded-live")]
                cat_e_live = categorical_records[("extended-exposure", "guarded-live")]
                cat_h_control = categorical_records[("horizon-control", "read-only-control")]
                cat_e_control = categorical_records[("extended-exposure", "read-only-control")]
                guarded_rest_logit_delta = float(cat_e_live["masked_logits"][0]) - float(
                    cat_h_live["masked_logits"][0]
                )
                control_rest_logit_delta = float(cat_e_control["masked_logits"][0]) - float(
                    cat_h_control["masked_logits"][0]
                )
                categorical_did = guarded_rest_logit_delta - control_rest_logit_delta
                if abs(categorical_did - did_rest) > 5.0e-7:
                    raise ValueError("Stage-3C-42 activation/policy REST delta mismatch")

                frozen_mode = frozen[mode.replace("-", "_")]
                if int(cat_h_live["action_id"]) != int(frozen_mode["horizon_action_id"]):
                    raise ValueError("Stage-3C-42 horizon action differs from frozen event")
                if int(cat_e_live["action_id"]) != int(frozen_mode["extended_action_id"]):
                    raise ValueError("Stage-3C-42 extended action differs from frozen event")
                if float(cat_h_live["uniform_draw"]) != float(frozen_mode["uniform_draw"]):
                    raise ValueError("Stage-3C-42 uniform draw differs from frozen event")

                crossing = bool(frozen_mode["same_action_interval_crossed"])
                record = {
                    "panel": panel,
                    "source_category": _source_category(panel, seed),
                    "seed": seed,
                    "subject_id": key[0],
                    "tick": key[1],
                    "event_id": key[2],
                    "mode": mode,
                    "frozen_action_crossing": crossing,
                    "frozen_pressure_ratio": float(
                        frozen_mode["boundary_pressure_to_horizon_margin_ratio"]
                    ),
                    "guarded_rest_logit_delta": guarded_rest_logit_delta,
                    "control_rest_logit_delta": control_rest_logit_delta,
                    "rest_output_exposure_did": did_rest,
                    "rest_output_exposure_did_components": did_components,
                    "horizon_live_control": horizon,
                    "extended_live_control": extended,
                    "did_absolute_reconstruction_error": abs(did_rest - did_reconstructed),
                }
                event_records.append(record)
                source_records.append(record)

        crossing_records = [item for item in source_records if item["frozen_action_crossing"]]
        source_summaries.append(
            {
                "panel": panel,
                "source_category": _source_category(panel, seed),
                "seed": seed,
                "event_identity_count": len(source["selected_events"]),
                "mode_event_count": len(source_records),
                "crossing_mode_event_count": len(crossing_records),
                "nonzero_rest_output_did_count": sum(
                    abs(float(item["rest_output_exposure_did"])) > _TOL
                    for item in source_records
                ),
                "rest_output_did_statistics": _stats(
                    item["rest_output_exposure_did"] for item in source_records
                ),
                "current_edge_gate_component_statistics": _stats(
                    item["rest_output_exposure_did_components"]["current_edge_gate"]
                    for item in source_records
                ),
                "inherited_node_state_component_statistics": _stats(
                    item["rest_output_exposure_did_components"]["inherited_node_state"]
                    for item in source_records
                ),
                "state_gate_interaction_statistics": _stats(
                    item["rest_output_exposure_did_components"]["state_gate_interaction"]
                    for item in source_records
                ),
                "maximum_absolute_reconstruction_error": max(
                    [float(item["did_absolute_reconstruction_error"]) for item in source_records],
                    default=0.0,
                ),
            }
        )

    crossing_records = [item for item in event_records if item["frozen_action_crossing"]]
    noncrossing_records = [item for item in event_records if not item["frozen_action_crossing"]]
    component_names = tuple(event_records[0]["rest_output_exposure_did_components"])
    crossing_abs_gate = [
        abs(float(item["rest_output_exposure_did_components"]["current_edge_gate"]))
        for item in crossing_records
    ]
    noncrossing_abs_gate = [
        abs(float(item["rest_output_exposure_did_components"]["current_edge_gate"]))
        for item in noncrossing_records
    ]
    non_gate_structural_components = (
        "inherited_node_state",
        "state_gate_interaction",
        "input",
        "bias",
        "output_gate",
        "node_output_gate_interaction",
    )
    maximum_abs_non_gate_structural_component = max(
        (
            abs(float(item["rest_output_exposure_did_components"][name]))
            for item in event_records
            for name in non_gate_structural_components
        ),
        default=0.0,
    )
    maximum_abs_numerical_component = max(
        (
            abs(float(item["rest_output_exposure_did_components"][name]))
            for item in event_records
            for name in (
                "edge_numerical_residual",
                "node_numerical_residual",
                "output_numerical_residual",
            )
        ),
        default=0.0,
    )
    alignment_common_crossing = [
        item for item in crossing_records if int(item["seed"]) == 12307
    ]
    if len(alignment_common_crossing) != 2:
        raise ValueError("Stage-3C-42 requires the two frozen Stage-3C-34 alignment-common crossings")
    alignment_common_gate_difference = abs(
        float(alignment_common_crossing[0]["rest_output_exposure_did_components"]["current_edge_gate"])
        - float(alignment_common_crossing[1]["rest_output_exposure_did_components"]["current_edge_gate"])
    )
    replication_records = [item for item in event_records if item["panel"] == "replication"]
    replication_highest_opportunity = max(
        replication_records, key=lambda item: float(item["frozen_pressure_ratio"])
    )
    crossing_component_stats = {
        name: _stats(item["rest_output_exposure_did_components"][name] for item in crossing_records)
        for name in component_names
    }
    noncrossing_component_stats = {
        name: _stats(item["rest_output_exposure_did_components"][name] for item in noncrossing_records)
        for name in component_names
    }

    payload: dict[str, Any] = {
        "schema": STAGE3C42_ACTIVATION_SOURCE_ASSESSMENT_SCHEMA,
        "producer_version": __version__,
        "study_sha256": str(study["study_sha256"]),
        "stage3c40_assessment_sha256": str(stage3c40["assessment_sha256"]),
        "stage3c41_assessment_sha256": str(stage3c41["assessment_sha256"]),
        "activation_trace_integrity_sha256": str(integrity["assessment_sha256"]),
        "experimental_factor": "read-only-frozen-event-activation-contribution-decomposition",
        "audit_support": {
            "source_count": len(study["sources"]),
            "event_identity_count": sum(len(item["selected_events"]) for item in study["sources"]),
            "mode_event_count": len(event_records),
            "crossing_mode_event_count": len(crossing_records),
            "trace_manifest_count": int(study["trace_manifest_count"]),
            "trace_identity_sha256": _canonical_sha256({"identities": sorted(trace_identity)}),
            "selection_rule": "Stage-3C-40 frozen top-five opportunities for preregistered Stage-3C-42 source categories",
        },
        "source_summaries": source_summaries,
        "event_records": event_records,
        "crossing_component_statistics": crossing_component_stats,
        "noncrossing_component_statistics": noncrossing_component_stats,
        "cross_panel_findings": {
            "all_rest_output_deltas_exactly_reconstructed": max(all_errors, default=0.0) <= _TOL,
            "all_observed_temporary_write_targets_are_edge_forward_gate": set(target_family_counter) <= {"edge-forward-gate"},
            "temporary_write_target_family_counts": dict(sorted(target_family_counter.items())),
            "crossing_mode_event_count": len(crossing_records),
            "noncrossing_mode_event_count": len(noncrossing_records),
            "nonzero_rest_output_did_mode_event_count": sum(
                abs(float(item["rest_output_exposure_did"])) > _TOL
                for item in event_records
            ),
            "maximum_abs_non_gate_structural_component": maximum_abs_non_gate_structural_component,
            "maximum_abs_numerical_component": maximum_abs_numerical_component,
            "all_exposure_did_structural_contribution_is_current_edge_gate": (
                maximum_abs_non_gate_structural_component <= _TOL
            ),
            "maximum_abs_inherited_node_state_component": max(
                (
                    abs(float(item["rest_output_exposure_did_components"]["inherited_node_state"]))
                    for item in event_records
                ),
                default=0.0,
            ),
            "maximum_abs_state_gate_interaction_component": max(
                (
                    abs(float(item["rest_output_exposure_did_components"]["state_gate_interaction"]))
                    for item in event_records
                ),
                default=0.0,
            ),
            "crossing_abs_current_gate_component": {
                "minimum": min(crossing_abs_gate),
                "maximum": max(crossing_abs_gate),
            },
            "noncrossing_abs_current_gate_component": {
                "minimum": min(noncrossing_abs_gate),
                "maximum": max(noncrossing_abs_gate),
            },
            "current_gate_component_alone_separates_crossing": (
                min(crossing_abs_gate) > max(noncrossing_abs_gate)
            ),
            "noncrossing_current_gate_magnitude_can_exceed_crossing": (
                max(noncrossing_abs_gate) > max(crossing_abs_gate)
            ),
            "inherited_state_component_alone_separates_crossing": False,
            "alignment_common_current_gate_component_absolute_difference": (
                alignment_common_gate_difference
            ),
            "replication_highest_opportunity": {
                "seed": int(replication_highest_opportunity["seed"]),
                "subject_id": int(replication_highest_opportunity["subject_id"]),
                "tick": int(replication_highest_opportunity["tick"]),
                "event_id": int(replication_highest_opportunity["event_id"]),
                "mode": str(replication_highest_opportunity["mode"]),
                "frozen_pressure_ratio": float(
                    replication_highest_opportunity["frozen_pressure_ratio"]
                ),
                "current_edge_gate_component": float(
                    replication_highest_opportunity[
                        "rest_output_exposure_did_components"
                    ]["current_edge_gate"]
                ),
                "horizon_live_edge_gate": float(
                    replication_highest_opportunity["horizon_live_control"][
                        "edge_gate_live"
                    ]
                ),
                "extended_live_edge_gate": float(
                    replication_highest_opportunity["extended_live_control"][
                        "edge_gate_live"
                    ]
                ),
            },
        },
        "frozen_interpretation": {
            "fixed_bootstrap_rest_output_execution_path_is_single_node_single_recurrent_edge": True,
            "temporary_write_reaches_rest_output_through_edge_forward_gate": True,
            "exposure_did_uses_current_edge_gate_without_inherited_state_divergence_on_frozen_support": True,
            "current_edge_gate_magnitude_is_sufficient_crossing_classifier": False,
            "execution_contribution_is_causal_attribution": False,
            "rest_action_port_has_value_semantics": False,
            "source_history_origin_is_fully_resolved": False,
            "thought_chain_implementation_authorized_in_this_stage": False,
        },
        "governance": {
            "runtime_rerun_used_only_to_generate_observation_trace": True,
            "new_source_panel_used": False,
            "event_selection_changed_after_trace_observation": False,
            "sampling_semantics_changed": False,
            "random_stream_changed": False,
            "exposure_or_horizon_changed": False,
            "post_hoc_scalar_classifier_fitted": False,
        },
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learned_weight_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "se-subject-vm-stage3c42-study-summary-v1",
        "producer_version": payload["producer_version"],
        "assessment_sha256": payload["assessment_sha256"],
        "audit_support": payload["audit_support"],
        "cross_panel_findings": payload["cross_panel_findings"],
        "retention_authorized": False,
    }


def _diagnostic(payload: dict[str, Any]) -> str:
    findings = payload["cross_panel_findings"]
    lines = [
        "# Stage 3C-42 REST activation contribution 来源审计",
        "",
        "## 支持",
        "",
        f"- source：{payload['audit_support']['source_count']}",
        f"- 冻结事件 identity：{payload['audit_support']['event_identity_count']}",
        f"- mode-event：{payload['audit_support']['mode_event_count']}",
        f"- crossing mode-event：{payload['audit_support']['crossing_mode_event_count']}",
        "",
        "## 完整性",
        "",
        f"- REST output 精确重建：`{findings['all_rest_output_deltas_exactly_reconstructed']}`",
        f"- write target 仅 edge-forward-gate：`{findings['all_observed_temporary_write_targets_are_edge_forward_gate']}`",
        f"- exposure DID 结构贡献全部来自当前 edge gate：`{findings['all_exposure_did_structural_contribution_is_current_edge_gate']}`",
        f"- crossing gate 幅度范围：`{findings['crossing_abs_current_gate_component']}`",
        f"- noncrossing gate 幅度范围：`{findings['noncrossing_abs_current_gate_component']}`",
        "",
        "## 解释边界",
        "",
        "- 当前结论只描述 fixed bootstrap graph 的执行贡献路径。",
        "- contribution 不是 causal attribution、value、reward 或 credit quality。",
        "- 本阶段不实现 thought chain。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="评估 Stage 3C-42 REST activation contribution 来源。")
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--stage3c40-assessment", required=True)
    parser.add_argument("--stage3c41-assessment", required=True)
    parser.add_argument("--activation-trace-integrity", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args()
    payload = assess_stage3c42_activation_source(
        _load_json(args.study_report),
        _load_json(args.stage3c40_assessment),
        _load_json(args.stage3c41_assessment),
        _load_json(args.activation_trace_integrity),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.summary_output:
        Path(args.summary_output).write_text(
            json.dumps(_summary(payload), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.diagnostic_report:
        Path(args.diagnostic_report).write_text(_diagnostic(payload), encoding="utf-8")
    print(json.dumps(payload["cross_panel_findings"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C42_ACTIVATION_SOURCE_ASSESSMENT_SCHEMA",
    "_live_control_decomposition",
    "assess_stage3c42_activation_source",
]
