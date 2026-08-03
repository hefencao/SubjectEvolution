"""Stage 3C-23 dual-readout rank reachability audit.

The common fixed bootstrap exposes uncertainty-mean on token port 29 and a
second readout-only node on token port 30.  The rank-one control duplicates
uncertainty-mean on port 30; the alternative uses one data-screened existing
objective coordinate.  The screen and comparison are read-only outside the
experiment-only bootstrap initializer.  No reward, value ordering, learned
attention, permanent retention or causal-credit claim is introduced.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import patch

import numpy as np

from .. import __version__
from ..runtime.sim import Simulation
from ..subject_vm.ports import SUBJECT_VM_INPUT_PORTS
from ..runtime import subject_vm_activation as activation_adapter
from .subject_vm_stage3c13_exposure_adequacy import (
    _arm_summary,
    _canonical_sha256,
    _compare_control_behavior,
    _load_json,
    _source_records,
    _validate_report_set,
)
from .subject_vm_stage3c19_token_geometry import _source_geometry
from .subject_vm_stage3c20_readout_reachability import (
    _aggregate_association,
    _event_index,
    _stage_totals,
)

STAGE3C23_DUAL_READOUT_RANK_SCHEMA = (
    "se-subject-vm-stage3c23-dual-readout-rank-assessment-v1"
)

_FROZEN_PARAMETERS = {
    "source_ticks": 2,
    "horizon_ticks": 8,
    "bootstrap_subjects": 16,
    "backend": "cpu",
    "rollback_after_ticks": 3,
    "bootstrap_target_family": "edge_forward_gate",
    "bootstrap_edge_carrier_enabled": True,
    "bootstrap_node0_visible_readout_enabled": False,
    "bootstrap_readout_input_port": 11,
    "association_tie_break": "latest",
    "association_candidate_limit": 1,
    "association_candidate_aggregation": "equal-weight-mean",
}


def _validate_study(study: dict[str, Any], *, second_port: int) -> None:
    if study.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-23 requires short paired study reports")
    params = study.get("parameters", {})
    for key, value in _FROZEN_PARAMETERS.items():
        if params.get(key) != value:
            raise ValueError(f"Stage-3C-23 frozen factor mismatch: {key}")
    if int(params.get("bootstrap_second_readout_input_port", -1)) != int(second_port):
        raise ValueError("Stage-3C-23 second readout arm mismatch")
    if len(study.get("seeds", ())) < 3:
        raise ValueError("Stage-3C-23 requires at least three independent sources")
    if not bool(study["engineering_summary"]["stage3c7_engineering_screen_passed"]):
        raise ValueError("Stage-3C-23 arms must pass Stage-3C-7")
    if bool(study.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-23 cannot use permanent retention")

    profile = study["bootstrap_profile"]
    if int(profile.get("node_count", -1)) != 10:
        raise ValueError("Stage-3C-23 requires the common ten-node bootstrap")
    shaping = profile.get("association_visible_readout_shaping", {})
    first = shaping.get("readout_only_node", {})
    second = shaping.get("second_readout_only_node", {})
    if (
        int(first.get("node_index", -1)) != 8
        or int(first.get("input_port", -1)) != 11
        or int(first.get("token_port", -1)) != 29
        or bool(first.get("changes_action_output"))
        or first.get("value_semantics") is not None
    ):
        raise ValueError("Stage-3C-23 primary readout profile mismatch")
    if (
        int(second.get("node_index", -1)) != 9
        or int(second.get("input_port", -1)) != int(second_port)
        or int(second.get("token_port", -1)) != 30
        or bool(second.get("changes_action_output"))
        or second.get("value_semantics") is not None
    ):
        raise ValueError("Stage-3C-23 second readout profile mismatch")


def _factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    params = dict(study["parameters"])
    params.pop("bootstrap_second_readout_input_port", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_second_readout_input_port": params,
        "population": study["population"],
        "resolved_backend": study["resolved_backend"],
        "temporary_exposure_contract": study["temporary_exposure_contract"],
        "fixed_bootstrap_is_evolved_result": study["fixed_bootstrap_is_evolved_result"],
        "universal_attention_claim": study["universal_attention_claim"],
        "permanent_parameter_retention_authorized": study[
            "permanent_parameter_retention_authorized"
        ],
    }


def _normalized_profile(profile: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(profile)
    payload.pop("profile_sha256", None)
    second = payload["association_visible_readout_shaping"][
        "second_readout_only_node"
    ]
    node9 = next(item for item in payload["nodes"] if int(item["index"]) == 9)
    second["input_port"] = "<second-readout-input-port>"
    node9["input_port"] = "<second-readout-input-port>"
    return payload


def _compare_authorized_port30(
    baseline_checkpoint: str | Path, alternative_checkpoint: str | Path
) -> dict[str, Any]:
    from ..checkpointing import read_checkpoint_bundle

    _, left_state = read_checkpoint_bundle(baseline_checkpoint)
    _, right_state = read_checkpoint_bundle(alternative_checkpoint)
    left = left_state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    right = right_state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    left_index = _event_index(left)
    right_index = _event_index(right)
    keys_equal = set(left_index) == set(right_index)
    non_port30_mismatch = 0
    port29_mismatch = 0
    port30_different = 0
    if keys_equal:
        for key in sorted(left_index):
            li = left_index[key]
            ri = right_index[key]
            lt = np.asarray(left["thought_token"][li])
            rt = np.asarray(right["thought_token"][ri])
            mask = np.ones(lt.shape, dtype=bool)
            mask[30] = False
            non_port30_mismatch += int(not np.array_equal(lt[mask], rt[mask]))
            port29_mismatch += int(lt[29] != rt[29])
            port30_different += int(lt[30] != rt[30])
    return {
        "event_keys_equal": bool(keys_equal),
        "non_port30_token_mismatch_count": int(non_port30_mismatch),
        "port29_mismatch_count": int(port29_mismatch),
        "port30_different_event_count": int(port30_different),
        "tokens_equal_except_authorized_port30_input_change": bool(
            keys_equal
            and non_port30_mismatch == 0
            and port29_mismatch == 0
            and port30_different > 0
        ),
    }


def _capture_objective_inputs(record: dict[str, Any]) -> np.ndarray:
    """Replay one read-only branch and capture all approved objective inputs."""
    original = activation_adapter.build_objective_input_ports
    captures: list[np.ndarray] = []
    active_rows: list[np.ndarray] = []

    def capture(**kwargs: Any) -> np.ndarray:
        result = original(**kwargs)
        captures.append(np.asarray(result, dtype=np.float64).copy())
        return result

    with tempfile.TemporaryDirectory(prefix="se-stage3c23-screen-") as tmp:
        simulation = Simulation.from_checkpoint(
            record["source_checkpoint"],
            Path(tmp) / "control",
            backend="cpu",
            until_tick=int(record["source_tick"]) + 8,
        )
        with patch.object(activation_adapter, "build_objective_input_ports", capture):
            for _ in range(8):
                simulation.step()
                active_rows.append(np.asarray(simulation.last_active, dtype=np.int32).copy())

        if len(captures) != 8:
            raise ValueError("Stage-3C-23 objective-input screen captured wrong tick count")
        subjects = [int(v) for v in record["bootstrap_lineage"]["primed_subject_ids"]]
        matrix = np.zeros((len(subjects), 8, len(SUBJECT_VM_INPUT_PORTS)), dtype=np.float64)
        for tick_index, (values, rows) in enumerate(zip(captures, active_rows, strict=True)):
            active_subjects = simulation.entities.primary_subject_id[rows]
            lookup = {int(subject): i for i, subject in enumerate(active_subjects.tolist())}
            if any(subject not in lookup for subject in subjects):
                raise ValueError("Stage-3C-23 primed subject disappeared during screen")
            for subject_index, subject in enumerate(subjects):
                matrix[subject_index, tick_index] = values[lookup[subject]]
    return matrix


def _candidate_metrics(matrix: np.ndarray, port: int, threshold: float = 0.8) -> dict[str, Any]:
    uncertainty = matrix[:, :, 11]
    candidate = matrix[:, :, int(port)]
    visible = np.stack(
        [uncertainty, candidate, np.ones_like(uncertainty)], axis=-1
    ).reshape(-1, 3)
    centered_rank = int(
        np.linalg.matrix_rank(visible - visible.mean(axis=0, keepdims=True), tol=1e-10)
    )
    design = np.stack(
        [np.ones(uncertainty.size), uncertainty.reshape(-1)], axis=1
    )
    response = candidate.reshape(-1)
    beta = np.linalg.lstsq(design, response, rcond=None)[0]
    residual_variance = float(np.var(response - design @ beta))
    within_tick = [float(np.var(candidate[:, tick])) for tick in range(candidate.shape[1])]
    within_subject = [
        float(np.var(candidate[subject])) for subject in range(candidate.shape[0])
    ]

    eligible_reference_count = 0
    queries_with_no_eligible = 0
    score_values: list[float] = []
    selected_delay_histogram: dict[int, int] = {}
    for subject in range(candidate.shape[0]):
        tokens = np.stack(
            [
                uncertainty[subject],
                candidate[subject],
                np.ones(candidate.shape[1]),
            ],
            axis=1,
        )
        for current_tick in range(1, candidate.shape[1]):
            eligible: list[tuple[float, int, int]] = []
            for historical_tick in range(max(0, current_tick - 6), current_tick):
                query = tokens[current_tick]
                historical = tokens[historical_tick]
                score = float(
                    np.dot(query, historical)
                    / (np.linalg.norm(query) * np.linalg.norm(historical))
                )
                score_values.append(score)
                if score >= threshold:
                    eligible.append((score, historical_tick, current_tick - historical_tick))
            eligible_reference_count += len(eligible)
            if not eligible:
                queries_with_no_eligible += 1
                continue
            # Frozen latest-on-tie top-1 ordering.
            eligible.sort(key=lambda item: (item[0], item[1]), reverse=True)
            delay = int(eligible[0][2])
            selected_delay_histogram[delay] = selected_delay_histogram.get(delay, 0) + 1

    return {
        "port": int(port),
        "name": SUBJECT_VM_INPUT_PORTS[int(port)],
        "centered_rank": centered_rank,
        "all_ticks_have_subject_variance": bool(within_tick and all(v > 0.0 for v in within_tick)),
        "all_subjects_have_temporal_variance": bool(
            within_subject and all(v > 0.0 for v in within_subject)
        ),
        "minimum_within_tick_subject_variance": min(within_tick, default=0.0),
        "minimum_within_subject_temporal_variance": min(within_subject, default=0.0),
        "residual_variance_after_uncertainty": residual_variance,
        "eligible_reference_count": int(eligible_reference_count),
        "queries_with_no_eligible": int(queries_with_no_eligible),
        "score_minimum": min(score_values, default=None),
        "score_maximum": max(score_values, default=None),
        "selected_delay_histogram": {
            str(key): int(value) for key, value in sorted(selected_delay_histogram.items())
        },
    }


def _screen_candidate_ports(study: dict[str, Any]) -> dict[str, Any]:
    per_source: list[dict[str, Any]] = []
    aggregate: dict[int, list[dict[str, Any]]] = {
        port: [] for port in range(len(SUBJECT_VM_INPUT_PORTS)) if port not in {0, 11}
    }
    for record in study["seeds"]:
        matrix = _capture_objective_inputs(record)
        rows = [_candidate_metrics(matrix, port) for port in aggregate]
        for row in rows:
            aggregate[int(row["port"])].append(row)
        per_source.append({"seed": int(record["seed"]), "candidates": rows})

    candidates: list[dict[str, Any]] = []
    for port, rows in sorted(aggregate.items()):
        qualifies = bool(
            all(row["centered_rank"] >= 2 for row in rows)
            and all(row["all_ticks_have_subject_variance"] for row in rows)
            and all(row["all_subjects_have_temporal_variance"] for row in rows)
            and all(row["queries_with_no_eligible"] == 0 for row in rows)
        )
        candidates.append(
            {
                "port": int(port),
                "name": SUBJECT_VM_INPUT_PORTS[port],
                "qualifies": qualifies,
                "minimum_centered_rank": min(row["centered_rank"] for row in rows),
                "minimum_residual_variance_after_uncertainty": min(
                    row["residual_variance_after_uncertainty"] for row in rows
                ),
                "minimum_eligible_reference_count": min(
                    row["eligible_reference_count"] for row in rows
                ),
                "maximum_queries_with_no_eligible": max(
                    row["queries_with_no_eligible"] for row in rows
                ),
            }
        )
    qualified = [row for row in candidates if row["qualifies"]]
    if not qualified:
        raise ValueError("Stage-3C-23 screen found no rank-two candidate")
    selected = sorted(
        qualified,
        key=lambda row: (
            -float(row["minimum_residual_variance_after_uncertainty"]),
            int(row["port"]),
        ),
    )[0]
    return {
        "screened_source_count": len(study["seeds"]),
        "primary_coordinate": {"port": 11, "name": SUBJECT_VM_INPUT_PORTS[11]},
        "selection_rule": (
            "qualify only if every source reaches centered rank >=2, every tick has "
            "subject variance, every subject has temporal variance, and no query loses "
            "all threshold-eligible history; then maximize the cross-source minimum "
            "residual variance after linear regression on uncertainty, tie by port index"
        ),
        "candidates": candidates,
        "selected_candidate": selected,
        "per_source": per_source,
    }


def _geometry_summary(study: dict[str, Any]) -> dict[str, Any]:
    rows = [_source_geometry(record) for record in study["seeds"]]
    return {
        "centered_covariance_rank_per_source": [
            int(row["centered_covariance"]["numerical_rank"]) for row in rows
        ],
        "uncentered_second_moment_rank_per_source": [
            int(row["uncentered_second_moment"]["numerical_rank"]) for row in rows
        ],
        "exact_unique_visible_token_count_per_source": [
            int(row["exact_unique_visible_token_count"]) for row in rows
        ],
        "all_pairwise_score_statistics_per_source": [
            row["score_separability"]["all_pairwise_normalized_dot_scores"] for row in rows
        ],
        "best_minus_second_score_spread_per_source": [
            row["score_separability"]["best_minus_second_score_spread"] for row in rows
        ],
    }


def assess_stage3c23_dual_readout_rank(
    rank1_study: dict[str, Any],
    rank1_component: dict[str, Any],
    rank1_diagnostics: dict[str, Any],
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    selected_port = int(
        rank2_study.get("parameters", {}).get(
            "bootstrap_second_readout_input_port", -1
        )
    )
    if selected_port in {0, 11} or not 0 <= selected_port < len(SUBJECT_VM_INPUT_PORTS):
        raise ValueError("Stage-3C-23 alternative second readout port is invalid")
    _validate_study(rank1_study, second_port=11)
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(rank1_study, rank1_component, rank1_diagnostics, label="rank1")
    _validate_report_set(rank2_study, rank2_component, rank2_diagnostics, label="rank2")
    if _factor_signature(rank1_study) != _factor_signature(rank2_study):
        raise ValueError("Stage-3C-23 comparison changed another study factor")
    if _normalized_profile(rank1_study["bootstrap_profile"]) != _normalized_profile(
        rank2_study["bootstrap_profile"]
    ):
        raise ValueError("Stage-3C-23 profiles differ beyond node-9 input port")

    left_sources = _source_records(rank1_study)
    right_sources = _source_records(rank2_study)
    if set(left_sources) != set(right_sources):
        raise ValueError("Stage-3C-23 arms use different source panels")

    checks = {
        "pre_bootstrap_state_hashes_equal": True,
        "pre_bootstrap_config_hashes_equal": True,
        "bootstrap_subject_selection_equal": True,
        "read_only_control_objective_behavior_equal": True,
        "tokens_equal_except_authorized_port30_input_change": True,
    }
    per_source: list[dict[str, Any]] = []
    for seed in sorted(left_sources):
        left = left_sources[seed]
        right = right_sources[seed]
        same_state = left["pre_bootstrap_checkpoint_state_sha256"] == right[
            "pre_bootstrap_checkpoint_state_sha256"
        ]
        same_config = left["pre_bootstrap_checkpoint_config_sha256"] == right[
            "pre_bootstrap_checkpoint_config_sha256"
        ]
        same_subjects = (
            left["bootstrap_lineage"]["primed_tick"]
            == right["bootstrap_lineage"]["primed_tick"]
            and left["bootstrap_lineage"]["primed_subject_ids"]
            == right["bootstrap_lineage"]["primed_subject_ids"]
        )
        control = _compare_control_behavior(
            left["read_only_control_checkpoint"], right["read_only_control_checkpoint"]
        )
        objective_equal = bool(
            control["event_keys_equal"]
            and set(control["mismatched_array_event_counts"]) <= {"thought_token"}
        )
        token = _compare_authorized_port30(
            left["read_only_control_checkpoint"], right["read_only_control_checkpoint"]
        )
        checks["pre_bootstrap_state_hashes_equal"] &= bool(same_state)
        checks["pre_bootstrap_config_hashes_equal"] &= bool(same_config)
        checks["bootstrap_subject_selection_equal"] &= bool(same_subjects)
        checks["read_only_control_objective_behavior_equal"] &= bool(objective_equal)
        checks["tokens_equal_except_authorized_port30_input_change"] &= bool(
            token["tokens_equal_except_authorized_port30_input_change"]
        )
        per_source.append(
            {
                "seed": int(seed),
                "pre_bootstrap_state_hash_equal": bool(same_state),
                "pre_bootstrap_config_hash_equal": bool(same_config),
                "bootstrap_subject_selection_equal": bool(same_subjects),
                "read_only_control_behavior": control,
                "read_only_control_objective_behavior_equal": bool(objective_equal),
                "authorized_port30_comparison": token,
            }
        )
    if not all(checks.values()):
        raise ValueError("Stage-3C-23 isolation or read-only invariance check failed")

    screen = _screen_candidate_ports(rank1_study)
    selected = screen["selected_candidate"]
    if int(selected["port"]) != selected_port:
        raise ValueError(
            "Stage-3C-23 alternative does not match the frozen data-screen selection"
        )

    rank1_geometry = _geometry_summary(rank1_study)
    rank2_geometry = _geometry_summary(rank2_study)
    source_count = len(per_source)
    if rank1_geometry["centered_covariance_rank_per_source"] != [1] * source_count:
        raise ValueError("Stage-3C-23 duplicated-coordinate control is not rank one")
    if not all(rank >= 2 for rank in rank2_geometry["centered_covariance_rank_per_source"]):
        raise ValueError("Stage-3C-23 alternative did not reach rank two")

    rank1_association = _aggregate_association(rank1_study)
    rank2_association = _aggregate_association(rank2_study)
    rank1_arm = {
        **_arm_summary(rank1_study, rank1_component, rank1_diagnostics),
        "stage_event_totals": _stage_totals(rank1_diagnostics),
        "association_allocation": rank1_association,
        "token_geometry": rank1_geometry,
    }
    rank2_arm = {
        **_arm_summary(rank2_study, rank2_component, rank2_diagnostics),
        "stage_event_totals": _stage_totals(rank2_diagnostics),
        "association_allocation": rank2_association,
        "token_geometry": rank2_geometry,
    }

    payload = {
        "schema": STAGE3C23_DUAL_READOUT_RANK_SCHEMA,
        "producer_version": __version__,
        "rank1_study_sha256": rank1_study["study_sha256"],
        "rank2_study_sha256": rank2_study["study_sha256"],
        "single_changed_experimental_factor": (
            "readout-only node-9 objective input: uncertainty-mean port 11 -> "
            f"{SUBJECT_VM_INPUT_PORTS[selected_port]} port {selected_port}"
        ),
        "unchanged_factor_signature": _factor_signature(rank1_study),
        "candidate_screen": screen,
        "isolation_contract": {
            **checks,
            "bootstrap_profiles_differ_only_in_second_readout_input_port": True,
            "same_primary_uncertainty_readout_on_port29": True,
            "same_second_readout_node_trace_port_and_gate": True,
            "same_action_outputs": True,
            "same_similarity_threshold_delay_bounds_candidate_limit_and_tie_break": True,
            "same_edge_forward_gate_target_and_carrier": True,
            "same_delta_exposure_rollback_and_evaluation_contract": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "tokens_windows_or_subjects_are_independent_replicates": False,
        },
        "rank1_duplicate_uncertainty_control": rank1_arm,
        "rank2_selected_coordinate": rank2_arm,
        "comparison": {
            "change_in_assigned_associations": int(
                rank2_association["assigned_association_count"]
                - rank1_association["assigned_association_count"]
            ),
            "change_in_modulation_proposals": int(
                rank2_arm["stage_event_totals"]["modulation_proposal_count"]
                - rank1_arm["stage_event_totals"]["modulation_proposal_count"]
            ),
            "change_in_live_commits": int(rank2_arm["live_commits"] - rank1_arm["live_commits"]),
            "change_in_completed_paired_windows": int(
                rank2_arm["completed_paired_windows"] - rank1_arm["completed_paired_windows"]
            ),
            "change_in_discrete_action_difference_events": int(
                rank2_arm["discrete_action_difference_events"]
                - rank1_arm["discrete_action_difference_events"]
            ),
            "change_in_sources_with_objective_event_divergence": int(
                rank2_arm["sources_with_objective_event_divergence"]
                - rank1_arm["sources_with_objective_event_divergence"]
            ),
            "change_in_stable_objective_coordinate_count": int(
                rank2_arm["stable_objective_coordinate_count"]
                - rank1_arm["stable_objective_coordinate_count"]
            ),
        },
        "per_source": per_source,
        "diagnostic_interpretation": {
            "second_subject_event_specific_coordinate_is_mechanically_reachable": True,
            "association_visible_centered_rank_reaches_two_in_all_sources": True,
            "selected_objective_coordinate_has_fixed_value_semantics": False,
            "rank_two_proves_causal_credit": False,
            "rank_two_proves_learning": False,
            "next_authorized_step": (
                "Hold the rank-two readout, similarity, latest top-1, target/carrier, "
                "delta, exposure and rollback fixed; audit candidate coverage, score "
                "margin and selection reuse before any addressing change."
            ),
        },
        "fixed_cognition_engineering_shaping_aid": True,
        "evolved_topology": False,
        "universal_attention_claim": False,
        "universal_scalar_objective": False,
        "permanent_parameter_retention_authorized": False,
        "automatic_keep_or_revert_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
        "runtime_or_checkpoint_schema_changed": False,
        "common_study_node_capacity_increase": 1,
        "common_study_storage_growth_formula_bytes": "63 * max_entities + 3",
        "common_study_storage_growth_bytes_at_32_entities": 2019,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assess Stage-3C-23 dual-readout rank reachability.")
    for prefix in ("rank1", "rank2"):
        parser.add_argument(f"--{prefix}-study-report", required=True)
        parser.add_argument(f"--{prefix}-component", required=True)
        parser.add_argument(f"--{prefix}-diagnostics", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c23_dual_readout_rank(
        _load_json(args.rank1_study_report),
        _load_json(args.rank1_component),
        _load_json(args.rank1_diagnostics),
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "selected_port": result["candidate_screen"]["selected_candidate"]["port"],
        "rank1": result["rank1_duplicate_uncertainty_control"]["token_geometry"]["centered_covariance_rank_per_source"],
        "rank2": result["rank2_selected_coordinate"]["token_geometry"]["centered_covariance_rank_per_source"],
        "stable_objective_coordinates": result["rank2_selected_coordinate"]["stable_objective_coordinate_count"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C23_DUAL_READOUT_RANK_SCHEMA",
    "assess_stage3c23_dual_readout_rank",
    "build_parser",
    "main",
]
