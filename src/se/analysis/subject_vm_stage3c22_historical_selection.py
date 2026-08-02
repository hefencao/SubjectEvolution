"""Stage 3C-22 selected historical-event coverage and reuse audit.

This module reconstructs the complete bounded association opportunity set from
read-only control checkpoints produced by the frozen Stage 3C-21 arms.  It
separates candidate eligibility, selected event identity coverage, repeated
selection and objective-fact span.  The analysis is read-only: it does not
change addressing, token geometry, update scale, rollback or retention.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.association import select_delayed_association_candidate
from ..subject_vm.modulation import modulation_control_ports, objective_fact_vector
from .subject_vm_stage3c13_exposure_adequacy import (
    _load_json,
    _source_records,
    _validate_report_set,
)
from .subject_vm_stage3c21_subject_event_readout import (
    STAGE3C21_SUBJECT_EVENT_READOUT_SCHEMA,
    _factor_signature,
    _normalized_profile,
    _validate_study,
)

STAGE3C22_HISTORICAL_SELECTION_SCHEMA = (
    "se-subject-vm-stage3c22-historical-selection-assessment-v1"
)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _stats(values: Iterable[float | int]) -> dict[str, Any]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {
            "count": 0,
            "minimum": None,
            "q25": None,
            "median": None,
            "q75": None,
            "maximum": None,
            "mean": None,
        }
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "q75": float(np.quantile(array, 0.75)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _gini(values: Iterable[int]) -> float:
    array = np.sort(np.asarray(list(values), dtype=np.float64))
    if array.size == 0 or float(array.sum()) == 0.0:
        return 0.0
    indices = np.arange(1, array.size + 1, dtype=np.float64)
    return float(
        (2.0 * np.sum(indices * array) / (array.size * array.sum()))
        - ((array.size + 1.0) / array.size)
    )


def _effective_counts(values: Iterable[int]) -> tuple[float, float]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0 or float(array.sum()) == 0.0:
        return 0.0, 0.0
    probability = array / array.sum()
    nonzero = probability[probability > 0.0]
    shannon = float(np.exp(-np.sum(nonzero * np.log(nonzero))))
    inverse_simpson = float(1.0 / np.sum(probability * probability))
    return shannon, inverse_simpson


def _fact_geometry(
    event_ids: Iterable[int], facts_by_event: dict[int, np.ndarray]
) -> dict[str, Any]:
    ordered = [int(event_id) for event_id in sorted(set(event_ids))]
    if not ordered:
        return {
            "event_count": 0,
            "exact_unique_fact_vector_count": 0,
            "centered_covariance_rank": 0,
        }
    matrix = np.asarray([facts_by_event[event_id] for event_id in ordered])
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    exact = {
        tuple(np.asarray(row, dtype=np.float32).tolist()) for row in matrix
    }
    return {
        "event_count": len(ordered),
        "exact_unique_fact_vector_count": len(exact),
        "centered_covariance_rank": int(np.linalg.matrix_rank(centered, tol=1e-10)),
    }


def _visible_query(token: np.ndarray, excluded_ports: tuple[int, ...]) -> np.ndarray:
    result = np.asarray(token, dtype=np.float64).copy()
    for port in excluded_ports:
        result[int(port)] = 0.0
    return result


def _selection_snapshot(checkpoint: str | Path) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(checkpoint)
    subject_vm_cfg = state["config"].subject_vm
    association_cfg = subject_vm_cfg.association
    trace = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]

    valid = np.asarray(trace["event_valid"], dtype=bool)
    event_ids = np.asarray(trace["event_id"], dtype=np.uint64)
    event_ticks = np.asarray(trace["event_tick"], dtype=np.int64)
    subject_ids = np.asarray(trace["subject_id"], dtype=np.uint64)
    tokens = np.asarray(trace["thought_token"], dtype=np.float64)
    requested = np.asarray(trace["association_requested"], dtype=bool) & valid
    assigned = np.asarray(trace["association_assigned"], dtype=bool) & valid
    stored_event_ids = np.asarray(trace["associated_event_id"], dtype=np.uint64)
    stored_event_ticks = np.asarray(trace["associated_event_tick"], dtype=np.int64)
    stored_delays = np.asarray(trace["association_delay_ticks"], dtype=np.int64)
    stored_similarities = np.asarray(trace["association_similarity"], dtype=np.float64)

    excluded_ports = (
        int(association_cfg.request_token_port),
        *modulation_control_ports(subject_vm_cfg.modulation),
    )

    facts_by_event: dict[int, np.ndarray] = {}
    event_metadata: dict[int, tuple[int, int]] = {}
    for row, slot in zip(*np.nonzero(valid), strict=True):
        event_id = int(event_ids[row, slot])
        if event_id in facts_by_event:
            raise ValueError(f"duplicate Stage-3C-22 event id: {event_id}")
        facts_by_event[event_id] = objective_fact_vector(
            objective_delta=trace["objective_delta"][row, slot],
            resource_delta=trace["resolution_resource_delta"][row, slot],
            internal_resource_delta=trace["resolution_internal_resource_delta"][
                row, slot
            ],
            energy_cost=float(trace["resolution_energy_cost"][row, slot]),
        )
        event_metadata[event_id] = (
            int(subject_ids[row, slot]),
            int(event_ticks[row, slot]),
        )

    delay_valid_union: set[int] = set()
    nonzero_union: set[int] = set()
    eligible_union: set[int] = set()
    selected_counts: Counter[int] = Counter()
    opportunity_counts: Counter[int] = Counter()
    per_subject_eligible: dict[int, set[int]] = defaultdict(set)
    per_subject_selected: dict[int, set[int]] = defaultdict(set)
    eligible_reference_counts: list[int] = []
    delay_valid_reference_count = 0
    nonzero_reference_count = 0
    reconstructed_selection_mismatch_count = 0
    selected_delay_histogram: Counter[int] = Counter()
    selection_by_current_event: dict[int, int] = {}

    for row, slot in zip(*np.nonzero(requested), strict=True):
        current_tick = int(event_ticks[row, slot])
        subject_id = int(subject_ids[row, slot])
        query = _visible_query(tokens[row, slot], excluded_ports)
        query_norm = float(np.linalg.norm(query))
        eligible_count = 0

        for historical_slot in np.flatnonzero(valid[row]).tolist():
            historical_tick = int(event_ticks[row, historical_slot])
            delay = current_tick - historical_tick
            if delay < int(association_cfg.min_delay_ticks) or delay > int(
                association_cfg.max_delay_ticks
            ):
                continue
            historical_event_id = int(event_ids[row, historical_slot])
            delay_valid_reference_count += 1
            delay_valid_union.add(historical_event_id)
            candidate = _visible_query(tokens[row, historical_slot], excluded_ports)
            candidate_norm = float(np.linalg.norm(candidate))
            if query_norm == 0.0 or candidate_norm == 0.0:
                continue
            nonzero_reference_count += 1
            nonzero_union.add(historical_event_id)
            similarity = float(
                np.clip(
                    np.dot(query, candidate) / (query_norm * candidate_norm),
                    -1.0,
                    1.0,
                )
            )
            if similarity < float(association_cfg.similarity_threshold):
                continue
            eligible_count += 1
            eligible_union.add(historical_event_id)
            opportunity_counts[historical_event_id] += 1
            per_subject_eligible[subject_id].add(historical_event_id)

        eligible_reference_counts.append(eligible_count)
        reconstructed = select_delayed_association_candidate(
            cfg=association_cfg,
            tie_break="latest",
            candidate_limit=1,
            current_tick=current_tick,
            current_token=tokens[row, slot],
            event_valid=valid[row],
            event_ids=event_ids[row],
            event_ticks=event_ticks[row],
            historical_tokens=tokens[row],
            excluded_slot=int(slot),
            excluded_token_ports=modulation_control_ports(subject_vm_cfg.modulation),
        )
        stored_assigned = bool(assigned[row, slot])
        reconstructed_matches = bool(reconstructed.assigned == stored_assigned)
        if stored_assigned:
            reconstructed_matches &= bool(
                int(reconstructed.associated_event_id)
                == int(stored_event_ids[row, slot])
                and int(reconstructed.associated_event_tick)
                == int(stored_event_ticks[row, slot])
                and int(reconstructed.delay_ticks) == int(stored_delays[row, slot])
                and np.isclose(
                    float(reconstructed.similarity),
                    float(stored_similarities[row, slot]),
                    rtol=0.0,
                    atol=1e-6,
                )
            )
            selected_event_id = int(stored_event_ids[row, slot])
            selected_counts[selected_event_id] += 1
            selection_by_current_event[int(event_ids[row, slot])] = selected_event_id
            per_subject_selected[subject_id].add(selected_event_id)
            selected_delay_histogram[int(stored_delays[row, slot])] += 1
        if not reconstructed_matches:
            reconstructed_selection_mismatch_count += 1

    eligible_ids = sorted(eligible_union)
    selected_ids = sorted(selected_counts)
    selection_counts_over_eligible = [selected_counts[event_id] for event_id in eligible_ids]
    shannon_effective, inverse_simpson_effective = _effective_counts(
        selection_counts_over_eligible
    )
    total_selections = int(sum(selection_counts_over_eligible))
    ordered_counts = sorted(selection_counts_over_eligible, reverse=True)
    top_decile_count = max(1, math.ceil(len(ordered_counts) * 0.1)) if ordered_counts else 0

    per_subject: list[dict[str, Any]] = []
    for subject_id in sorted(per_subject_eligible):
        eligible = per_subject_eligible[subject_id]
        selected = per_subject_selected[subject_id]
        counts = [selected_counts[event_id] for event_id in eligible]
        per_subject.append(
            {
                "stable_subject_id": int(subject_id),
                "eligible_unique_historical_event_count": len(eligible),
                "selected_unique_historical_event_count": len(selected),
                "selected_unique_fraction_of_eligible": float(
                    len(selected) / len(eligible) if eligible else 0.0
                ),
                "maximum_historical_event_reuse": max(counts, default=0),
            }
        )

    tick_rows: list[dict[str, Any]] = []
    for tick in sorted({event_metadata[event_id][1] for event_id in eligible_ids}):
        eligible_at_tick = {
            event_id
            for event_id in eligible_ids
            if event_metadata[event_id][1] == tick
        }
        selected_at_tick = eligible_at_tick & set(selected_ids)
        tick_rows.append(
            {
                "historical_tick": int(tick),
                "eligible_unique_event_count": len(eligible_at_tick),
                "selected_unique_event_count": len(selected_at_tick),
                "selected_unique_fraction_of_eligible": float(
                    len(selected_at_tick) / len(eligible_at_tick)
                    if eligible_at_tick
                    else 0.0
                ),
                "selection_assignment_count": int(
                    sum(selected_counts[event_id] for event_id in eligible_at_tick)
                ),
            }
        )

    return {
        "valid_trace_event_count": int(np.count_nonzero(valid)),
        "association_request_count": int(np.count_nonzero(requested)),
        "assigned_current_event_count": int(np.count_nonzero(assigned)),
        "reconstructed_selection_mismatch_count": int(
            reconstructed_selection_mismatch_count
        ),
        "candidate_opportunity": {
            "delay_valid_reference_count": int(delay_valid_reference_count),
            "nonzero_reference_count": int(nonzero_reference_count),
            "above_threshold_reference_count": int(
                sum(eligible_reference_counts)
            ),
            "unique_delay_valid_historical_event_count": len(delay_valid_union),
            "unique_nonzero_historical_event_count": len(nonzero_union),
            "unique_above_threshold_historical_event_count": len(eligible_union),
            "eligible_candidates_per_request": _stats(eligible_reference_counts),
            "all_delay_valid_references_are_nonzero": bool(
                delay_valid_reference_count == nonzero_reference_count
            ),
            "all_nonzero_references_are_above_threshold": bool(
                nonzero_reference_count == sum(eligible_reference_counts)
            ),
        },
        "selected_identity_coverage": {
            "unique_selected_historical_event_count": len(selected_counts),
            "unique_unselected_eligible_event_count": int(
                len(eligible_union - set(selected_counts))
            ),
            "selected_unique_fraction_of_eligible_union": float(
                len(selected_counts) / len(eligible_union) if eligible_union else 0.0
            ),
            "all_selected_events_are_eligible": bool(
                set(selected_counts) <= eligible_union
            ),
            "selected_delay_histogram": {
                str(key): int(value)
                for key, value in sorted(selected_delay_histogram.items())
            },
            "per_historical_tick": tick_rows,
            "per_subject": per_subject,
            "per_subject_selected_unique_fraction": _stats(
                row["selected_unique_fraction_of_eligible"] for row in per_subject
            ),
        },
        "reuse_concentration": {
            "selection_count_histogram_over_eligible_events": {
                str(key): int(value)
                for key, value in sorted(
                    Counter(selection_counts_over_eligible).items()
                )
            },
            "historical_events_selected_more_than_once": int(
                sum(value > 1 for value in selection_counts_over_eligible)
            ),
            "maximum_historical_event_reuse": max(
                selection_counts_over_eligible, default=0
            ),
            "eligible_union_selection_gini": _gini(
                selection_counts_over_eligible
            ),
            "shannon_effective_selected_event_count": shannon_effective,
            "inverse_simpson_effective_selected_event_count": (
                inverse_simpson_effective
            ),
            "shannon_effective_fraction_of_eligible_union": float(
                shannon_effective / len(eligible_union) if eligible_union else 0.0
            ),
            "inverse_simpson_effective_fraction_of_eligible_union": float(
                inverse_simpson_effective / len(eligible_union)
                if eligible_union
                else 0.0
            ),
            "maximum_single_event_selection_share": float(
                max(selection_counts_over_eligible, default=0) / total_selections
                if total_selections
                else 0.0
            ),
            "top_decile_event_selection_share": float(
                sum(ordered_counts[:top_decile_count]) / total_selections
                if total_selections
                else 0.0
            ),
            "selection_rate_given_eligibility": _stats(
                selected_counts[event_id] / opportunity_counts[event_id]
                for event_id in eligible_ids
            ),
        },
        "objective_fact_geometry": {
            "eligible_historical_events": _fact_geometry(
                eligible_ids, facts_by_event
            ),
            "selected_historical_events": _fact_geometry(
                selected_ids, facts_by_event
            ),
        },
        "eligible_event_ids": eligible_ids,
        "selected_event_ids": selected_ids,
        "_selection_by_current_event": {
            str(current_event_id): int(selected_event_id)
            for current_event_id, selected_event_id in sorted(
                selection_by_current_event.items()
            )
        },
        "selected_event_counts": {
            str(event_id): int(selected_counts[event_id])
            for event_id in selected_ids
        },
    }


def _aggregate_source_metric(
    per_source: list[dict[str, Any]], path: tuple[str, ...]
) -> dict[str, Any]:
    values: list[float] = []
    for item in per_source:
        current: Any = item
        for key in path:
            current = current[key]
        values.append(float(current))
    return _stats(values)


def assess_stage3c22_historical_selection(
    constant_study: dict[str, Any],
    constant_component: dict[str, Any],
    constant_diagnostics: dict[str, Any],
    uncertainty_study: dict[str, Any],
    uncertainty_component: dict[str, Any],
    uncertainty_diagnostics: dict[str, Any],
    stage3c21_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit selected-event identity coverage without changing runtime state."""
    _validate_study(constant_study, input_port=0)
    _validate_study(uncertainty_study, input_port=11)
    _validate_report_set(
        constant_study, constant_component, constant_diagnostics, label="constant"
    )
    _validate_report_set(
        uncertainty_study,
        uncertainty_component,
        uncertainty_diagnostics,
        label="uncertainty",
    )
    if _factor_signature(constant_study) != _factor_signature(uncertainty_study):
        raise ValueError("Stage-3C-22 comparison changed another study factor")
    if _normalized_profile(constant_study["bootstrap_profile"]) != _normalized_profile(
        uncertainty_study["bootstrap_profile"]
    ):
        raise ValueError("Stage-3C-22 profiles differ beyond readout input port")
    if stage3c21_assessment.get("schema") != STAGE3C21_SUBJECT_EVENT_READOUT_SCHEMA:
        raise ValueError("Stage-3C-22 requires a Stage-3C-21 assessment")
    if stage3c21_assessment.get("constant_study_sha256") != constant_study.get(
        "study_sha256"
    ) or stage3c21_assessment.get("uncertainty_study_sha256") != uncertainty_study.get(
        "study_sha256"
    ):
        raise ValueError("Stage-3C-22 Stage-3C-21 lineage mismatch")
    if not all(
        bool(stage3c21_assessment["isolation_contract"].get(key))
        for key in (
            "pre_bootstrap_state_hashes_equal",
            "pre_bootstrap_config_hashes_equal",
            "bootstrap_subject_selection_equal",
            "read_only_control_objective_behavior_equal",
            "tokens_equal_except_authorized_port29_input_change",
        )
    ):
        raise ValueError("Stage-3C-22 requires the complete Stage-3C-21 isolation contract")

    constant_sources = _source_records(constant_study)
    uncertainty_sources = _source_records(uncertainty_study)
    if set(constant_sources) != set(uncertainty_sources):
        raise ValueError("Stage-3C-22 arms use different source panels")

    constant_rows: list[dict[str, Any]] = []
    uncertainty_rows: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    candidate_opportunity_equal = True
    uncertainty_adds_new_selected = False
    uncertainty_subset = True
    uncertainty_reduces_coverage = True
    uncertainty_increases_reuse = True
    fact_rank_preserved = True

    for seed in sorted(constant_sources):
        constant = _selection_snapshot(
            constant_sources[seed]["read_only_control_checkpoint"]
        )
        uncertainty = _selection_snapshot(
            uncertainty_sources[seed]["read_only_control_checkpoint"]
        )
        constant["seed"] = int(seed)
        uncertainty["seed"] = int(seed)
        constant_rows.append(constant)
        uncertainty_rows.append(uncertainty)

        if constant["reconstructed_selection_mismatch_count"] != 0 or uncertainty[
            "reconstructed_selection_mismatch_count"
        ] != 0:
            raise ValueError("Stage-3C-22 reconstructed selector mismatch")
        opportunity_equal = bool(
            constant["candidate_opportunity"] == uncertainty["candidate_opportunity"]
            and constant["eligible_event_ids"] == uncertainty["eligible_event_ids"]
        )
        candidate_opportunity_equal &= opportunity_equal
        constant_selected = set(constant["selected_event_ids"])
        uncertainty_selected = set(uncertainty["selected_event_ids"])
        new_selected = uncertainty_selected - constant_selected
        lost_selected = constant_selected - uncertainty_selected
        uncertainty_adds_new_selected |= bool(new_selected)
        uncertainty_subset &= bool(uncertainty_selected < constant_selected)
        constant_coverage = float(
            constant["selected_identity_coverage"][
                "selected_unique_fraction_of_eligible_union"
            ]
        )
        uncertainty_coverage = float(
            uncertainty["selected_identity_coverage"][
                "selected_unique_fraction_of_eligible_union"
            ]
        )
        uncertainty_reduces_coverage &= bool(
            uncertainty_coverage < constant_coverage
        )
        constant_max_reuse = int(
            constant["reuse_concentration"]["maximum_historical_event_reuse"]
        )
        uncertainty_max_reuse = int(
            uncertainty["reuse_concentration"]["maximum_historical_event_reuse"]
        )
        uncertainty_increases_reuse &= bool(
            uncertainty_max_reuse > constant_max_reuse
        )
        constant_rank = int(
            constant["objective_fact_geometry"]["eligible_historical_events"][
                "centered_covariance_rank"
            ]
        )
        uncertainty_selected_rank = int(
            uncertainty["objective_fact_geometry"]["selected_historical_events"][
                "centered_covariance_rank"
            ]
        )
        fact_rank_preserved &= bool(uncertainty_selected_rank == constant_rank)

        constant_by_query = constant["_selection_by_current_event"]
        uncertainty_by_query = uncertainty["_selection_by_current_event"]
        if set(constant_by_query) != set(uncertainty_by_query):
            raise ValueError("Stage-3C-22 assigned current-event keys changed")
        exact_same_query_selection_count = sum(
            constant_by_query[current_event_id]
            == uncertainty_by_query[current_event_id]
            for current_event_id in constant_by_query
        )
        assignments = int(constant["assigned_current_event_count"])
        constant.pop("_selection_by_current_event", None)
        uncertainty.pop("_selection_by_current_event", None)

        comparisons.append(
            {
                "seed": int(seed),
                "candidate_opportunity_equal": opportunity_equal,
                "constant_selected_unique_event_count": len(constant_selected),
                "uncertainty_selected_unique_event_count": len(uncertainty_selected),
                "new_uncertainty_selected_event_count": len(new_selected),
                "constant_selected_events_not_selected_by_uncertainty": len(
                    lost_selected
                ),
                "selected_event_set_jaccard": float(
                    len(constant_selected & uncertainty_selected)
                    / len(constant_selected | uncertainty_selected)
                ),
                "exact_same_query_selection_fraction": float(
                    exact_same_query_selection_count / assignments
                    if assignments
                    else 0.0
                ),
                "change_in_unique_event_coverage_fraction": float(
                    uncertainty_coverage - constant_coverage
                ),
                "change_in_maximum_reuse": int(
                    uncertainty_max_reuse - constant_max_reuse
                ),
                "change_in_eligible_union_selection_gini": float(
                    uncertainty["reuse_concentration"][
                        "eligible_union_selection_gini"
                    ]
                    - constant["reuse_concentration"][
                        "eligible_union_selection_gini"
                    ]
                ),
            }
        )

    if not candidate_opportunity_equal:
        raise ValueError("Stage-3C-22 candidate opportunity changed across arms")
    if not uncertainty_subset or uncertainty_adds_new_selected:
        raise ValueError("Stage-3C-22 current result does not reproduce subset selection")

    payload = {
        "schema": STAGE3C22_HISTORICAL_SELECTION_SCHEMA,
        "producer_version": __version__,
        "constant_study_sha256": constant_study["study_sha256"],
        "uncertainty_study_sha256": uncertainty_study["study_sha256"],
        "stage3c21_assessment_sha256": stage3c21_assessment["assessment_sha256"],
        "analysis_only_factor": (
            "reconstruct complete per-query historical candidate opportunity and "
            "measure selected-event identity coverage and reuse concentration"
        ),
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(comparisons),
            "seeds": sorted(constant_sources),
            "stage3c21_isolation_contract_reused": True,
            "same_delay_valid_nonzero_and_above_threshold_candidate_opportunity": (
                candidate_opportunity_equal
            ),
            "stored_selections_exactly_reconstructed": True,
            "same_similarity_threshold_delay_bounds_candidate_limit_and_tie_break": True,
            "same_target_carrier_delta_exposure_rollback_and_evaluation_contract": True,
            "highest_independent_replicate": (
                "independent-pre-bootstrap-source-checkpoint"
            ),
            "events_subjects_or_windows_are_independent_replicates": False,
        },
        "constant_readout": {
            "per_source": constant_rows,
            "selected_unique_event_count_per_source": _aggregate_source_metric(
                constant_rows,
                ("selected_identity_coverage", "unique_selected_historical_event_count"),
            ),
            "selected_unique_fraction_of_eligible_per_source": _aggregate_source_metric(
                constant_rows,
                (
                    "selected_identity_coverage",
                    "selected_unique_fraction_of_eligible_union",
                ),
            ),
            "maximum_reuse_per_source": _aggregate_source_metric(
                constant_rows,
                ("reuse_concentration", "maximum_historical_event_reuse"),
            ),
            "selection_gini_per_source": _aggregate_source_metric(
                constant_rows,
                ("reuse_concentration", "eligible_union_selection_gini"),
            ),
            "inverse_simpson_effective_fraction_per_source": _aggregate_source_metric(
                constant_rows,
                (
                    "reuse_concentration",
                    "inverse_simpson_effective_fraction_of_eligible_union",
                ),
            ),
        },
        "uncertainty_readout": {
            "per_source": uncertainty_rows,
            "selected_unique_event_count_per_source": _aggregate_source_metric(
                uncertainty_rows,
                ("selected_identity_coverage", "unique_selected_historical_event_count"),
            ),
            "selected_unique_fraction_of_eligible_per_source": _aggregate_source_metric(
                uncertainty_rows,
                (
                    "selected_identity_coverage",
                    "selected_unique_fraction_of_eligible_union",
                ),
            ),
            "maximum_reuse_per_source": _aggregate_source_metric(
                uncertainty_rows,
                ("reuse_concentration", "maximum_historical_event_reuse"),
            ),
            "selection_gini_per_source": _aggregate_source_metric(
                uncertainty_rows,
                ("reuse_concentration", "eligible_union_selection_gini"),
            ),
            "inverse_simpson_effective_fraction_per_source": _aggregate_source_metric(
                uncertainty_rows,
                (
                    "reuse_concentration",
                    "inverse_simpson_effective_fraction_of_eligible_union",
                ),
            ),
        },
        "comparison": {
            "per_source": comparisons,
            "candidate_opportunity_equal_in_all_sources": candidate_opportunity_equal,
            "uncertainty_selected_set_is_strict_subset_in_all_sources": uncertainty_subset,
            "uncertainty_adds_any_new_selected_event_identity": uncertainty_adds_new_selected,
            "uncertainty_reduces_unique_identity_coverage_in_all_sources": (
                uncertainty_reduces_coverage
            ),
            "uncertainty_increases_maximum_reuse_in_all_sources": (
                uncertainty_increases_reuse
            ),
            "selected_objective_fact_centered_rank_preserved_in_all_sources": (
                fact_rank_preserved
            ),
            "exact_same_query_selection_fraction": _stats(
                row["exact_same_query_selection_fraction"] for row in comparisons
            ),
            "selected_event_set_jaccard": _stats(
                row["selected_event_set_jaccard"] for row in comparisons
            ),
        },
        "diagnostic_interpretation": {
            "subject_event_geometry_changes_ranking_not_candidate_eligibility": True,
            "subject_event_geometry_increases_selected_event_identity_diversity": False,
            "subject_event_geometry_selects_new_identity_outside_constant_coverage": False,
            "subject_event_geometry_increases_reuse_concentration": True,
            "objective_fact_linear_span_is_preserved_descriptively": fact_rank_preserved,
            "full_constant_identity_coverage_is_a_latest_one_step_baseline_artifact": True,
            "more_unique_events_has_fixed_value_semantics": False,
            "reuse_or_coverage_proves_causal_credit": False,
            "selection_concentration_proves_learning_effect": False,
            "next_authorized_step": (
                "Hold the Stage-3C-21 uncertainty readout, similarity, top-1, update "
                "scale, exposure and rollback fixed. Perform a read-only survey of a "
                "second role-neutral visible coordinate and require rank-two, subject/"
                "event-specific geometry before any paired addressing change."
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
        "runtime_memory_growth_bytes": 0,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess Stage-3C-22 historical selection coverage and reuse."
    )
    for prefix in ("constant", "uncertainty"):
        parser.add_argument(f"--{prefix}-study-report", required=True)
        parser.add_argument(f"--{prefix}-component", required=True)
        parser.add_argument(f"--{prefix}-diagnostics", required=True)
    parser.add_argument("--stage3c21-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c22_historical_selection(
        _load_json(args.constant_study_report),
        _load_json(args.constant_component),
        _load_json(args.constant_diagnostics),
        _load_json(args.uncertainty_study_report),
        _load_json(args.uncertainty_component),
        _load_json(args.uncertainty_diagnostics),
        _load_json(args.stage3c21_assessment),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["diagnostic_interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C22_HISTORICAL_SELECTION_SCHEMA",
    "assess_stage3c22_historical_selection",
]
