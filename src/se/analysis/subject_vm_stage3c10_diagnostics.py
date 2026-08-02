"""Stage 3C-10 funnel, visibility, and branch-divergence diagnostics.

This module reads trusted project checkpoints and existing Stage-3C-7/8 outputs.
It does not mutate runtime state, assign value to objective coordinates, or
change the source/subject/window replicate hierarchy.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.association import ASSOCIATION_REASON_NAMES
from ..subject_vm.binding import BINDING_REASON_NAMES
from ..subject_vm.config import (
    SUBJECT_VM_MODULATION_TARGET_NAMES,
    SUBJECT_VM_REGION_NAMES,
)
from ..subject_vm.evaluation import (
    EVALUATION_STATUS_COMPLETE_CONTROL,
    EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK,
)
from ..subject_vm.live_write import LIVE_WRITE_REASON_NAMES
from ..subject_vm.modulation import MODULATION_REASON_NAMES
from ..subject_vm.transaction import TRANSACTION_REASON_NAMES
from ..subject_vm.update_safety import UPDATE_REASON_NAMES

STAGE3C10_DIAGNOSTICS_SCHEMA = "se-subject-vm-stage3c10-diagnostics-v1"


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()



def _stats(values: Iterable[float | int]) -> dict[str, Any]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {"count": 0, "minimum": None, "q25": None, "median": None, "q75": None, "maximum": None, "mean": None}
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "q75": float(np.quantile(array, 0.75)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _reason_counts(codes: np.ndarray, names: tuple[str, ...], mask: np.ndarray) -> dict[str, int]:
    selected = np.asarray(codes)[np.asarray(mask, dtype=bool)]
    result: dict[str, int] = {}
    for value, count in zip(*np.unique(selected, return_counts=True), strict=True):
        index = int(value)
        name = names[index] if 0 <= index < len(names) else f"unknown-{index}"
        result[name] = int(count)
    return result




def _trace_tick_coverage(
    *, source_tick: int, final_tick: int, observed_ticks: Iterable[int]
) -> dict[str, Any]:
    expected = list(range(int(source_tick), int(final_tick)))
    observed = sorted({int(tick) for tick in observed_ticks})
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    return {
        "expected_event_ticks": expected,
        "observed_event_ticks": observed,
        "missing_event_ticks": missing,
        "unexpected_event_ticks": unexpected,
        "coverage_fraction": (
            float((len(expected) - len(missing)) / len(expected))
            if expected
            else 1.0
        ),
        "complete": not missing and not unexpected,
        "retention_limited": bool(missing),
        "observed_divergence_counts_are_lower_bounds_when_incomplete": bool(missing),
    }

def _subject_rows(state: dict[str, Any]) -> dict[int, int]:
    entities = state["simulation"]["entities"]
    return {
        int(subject_id): int(row)
        for row, subject_id in enumerate(entities.primary_subject_id.tolist())
        if bool(entities.alive[row]) and int(subject_id) > 0
    }


def _trace_arrays(state: dict[str, Any]) -> dict[str, np.ndarray]:
    return state["simulation"]["subject_vm"]["trace_storage"]["arrays"]


def _event_index(trace: dict[str, np.ndarray]) -> dict[tuple[int, int], tuple[int, int]]:
    result: dict[tuple[int, int], tuple[int, int]] = {}
    for row, slot in zip(*np.nonzero(trace["event_valid"]), strict=True):
        result[(int(trace["subject_id"][row, slot]), int(trace["event_tick"][row, slot]))] = (int(row), int(slot))
    return result


def _completed_windows_by_subject(state: dict[str, Any]) -> Counter[int]:
    simulation = state["simulation"]
    arrays = simulation["subject_vm"]["evaluation_ledger"]["arrays"]
    entities = simulation["entities"]
    complete = (arrays["status"] == int(EVALUATION_STATUS_COMPLETE_CONTROL)) | (
        arrays["status"] == int(EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK)
    )
    result: Counter[int] = Counter()
    for row, slot in zip(*np.nonzero(complete), strict=True):
        subject_id = int(entities.primary_subject_id[row])
        if subject_id > 0:
            result[subject_id] += 1
    return result


def _branch_subject_funnel(state: dict[str, Any], bootstrap_subject_ids: list[int]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    trace = _trace_arrays(state)
    events = _event_index(trace)
    complete_windows = _completed_windows_by_subject(state)
    subject_rows = _subject_rows(state)
    storage = state["simulation"]["subject_vm"]["storage"]["arrays"]
    by_subject_slots: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for (subject_id, _tick), slot in events.items():
        by_subject_slots[subject_id].append(slot)

    rows: list[dict[str, Any]] = []
    totals = Counter()
    rejection_totals: Counter[str] = Counter()
    window_counts: list[int] = []
    for subject_id in bootstrap_subject_ids:
        slots = by_subject_slots.get(subject_id, [])
        row_index = subject_rows.get(subject_id)
        expressed = bool(row_index is not None and np.any(storage["node_expressed"][row_index]))
        valid_pairs = tuple(zip(*slots, strict=True)) if slots else ((), ())
        rr = np.asarray(valid_pairs[0], dtype=np.int64)
        ss = np.asarray(valid_pairs[1], dtype=np.int64)

        def count(name: str) -> int:
            if not slots:
                return 0
            return int(np.count_nonzero(trace[name][rr, ss]))

        subject_rejections = Counter()
        if not expressed:
            subject_rejections["no-activation-capability"] += 1
        elif not slots:
            subject_rejections["no-token"] += 1
        else:
            for name, amount in _reason_counts(trace["association_reason"][rr, ss], ASSOCIATION_REASON_NAMES, np.ones(rr.size, dtype=bool)).items():
                if name != "assigned":
                    subject_rejections[f"association:{name}"] += amount
            for name, amount in _reason_counts(trace["modulation_reason"][rr, ss], MODULATION_REASON_NAMES, np.ones(rr.size, dtype=bool)).items():
                if name != "proposed":
                    subject_rejections[f"modulation:{name}"] += amount
            binding_mask = np.ones(trace["binding_reason"][rr, ss].shape, dtype=bool)
            for name, amount in _reason_counts(trace["binding_reason"][rr, ss], BINDING_REASON_NAMES, binding_mask).items():
                if name != "bound":
                    subject_rejections[f"binding:{name}"] += amount
            update_mask = np.ones(trace["update_reason"][rr, ss].shape, dtype=bool)
            for name, amount in _reason_counts(trace["update_reason"][rr, ss], UPDATE_REASON_NAMES, update_mask).items():
                if name != "proposed":
                    subject_rejections[f"update:{name}"] += amount
            transaction_mask = np.ones(trace["transaction_reason"][rr, ss].shape, dtype=bool)
            for name, amount in _reason_counts(trace["transaction_reason"][rr, ss], TRANSACTION_REASON_NAMES, transaction_mask).items():
                if name != "prepared":
                    subject_rejections[f"transaction:{name}"] += amount
            for name, amount in _reason_counts(trace["live_write_reason"][rr, ss], LIVE_WRITE_REASON_NAMES, np.ones(rr.size, dtype=bool)).items():
                if name not in {"committed", "control-reserved"}:
                    subject_rejections[f"live-write:{name}"] += amount

        record = {
            "stable_subject_id": int(subject_id),
            "graph_expression_present": expressed,
            "token_event_count": len(slots),
            "association_candidate_count": count("association_assigned"),
            "modulation_proposal_count": count("modulation_proposed"),
            "target_binding_event_count": count("binding_bound_any"),
            "safe_update_event_count": count("update_proposed_any"),
            "shadow_transaction_count": count("transaction_prepared"),
            "guarded_live_or_control_admission_count": count("live_write_authorized"),
            "guarded_live_commit_count": count("live_write_committed"),
            "completed_evaluation_window_count": int(complete_windows[subject_id]),
            "rejection_reasons": dict(sorted(subject_rejections.items())),
        }
        rows.append(record)
        totals.update({key: value for key, value in record.items() if key.endswith("_count")})
        rejection_totals.update(subject_rejections)
        window_counts.append(int(complete_windows[subject_id]))

    summary = {
        "bootstrap_subject_count": len(bootstrap_subject_ids),
        "subjects_with_graph_expression": int(sum(row["graph_expression_present"] for row in rows)),
        "subjects_with_tokens": int(sum(row["token_event_count"] > 0 for row in rows)),
        "subjects_with_association_candidate": int(sum(row["association_candidate_count"] > 0 for row in rows)),
        "subjects_with_modulation_proposal": int(sum(row["modulation_proposal_count"] > 0 for row in rows)),
        "subjects_with_target_binding": int(sum(row["target_binding_event_count"] > 0 for row in rows)),
        "subjects_with_safe_update": int(sum(row["safe_update_event_count"] > 0 for row in rows)),
        "subjects_with_shadow_transaction": int(sum(row["shadow_transaction_count"] > 0 for row in rows)),
        "subjects_with_live_or_control_admission": int(sum(row["guarded_live_or_control_admission_count"] > 0 for row in rows)),
        "subjects_with_completed_window": int(sum(row["completed_evaluation_window_count"] > 0 for row in rows)),
        "stage_event_totals": dict(sorted(totals.items())),
        "completed_windows_per_subject": _stats(window_counts),
        "rejection_reason_totals": dict(sorted(rejection_totals.items())),
    }
    raw = summary["rejection_reason_totals"]
    summary["canonical_rejection_categories"] = {
        "no_activation": int(raw.get("no-activation-capability", 0)),
        "no_token": int(raw.get("no-token", 0)),
        "no_historical_candidate": int(
            raw.get("association:no-candidate", 0)
            + raw.get("association:zero-candidate", 0)
        ),
        "candidate_similarity_below_threshold": int(
            raw.get("association:below-threshold", 0)
        ),
        "no_parameter_family_proposal": int(sum(
            amount for reason, amount in raw.items()
            if reason.startswith("modulation:")
        )),
        "no_eligibility_target": int(
            raw.get("binding:no-valid-local-carrier", 0)
        ),
        "delta_too_small": int(raw.get("update:candidate-below-minimum", 0)),
        "budget_or_parameter_boundary_rejection": int(
            raw.get("update:parameter-bound-no-room", 0)
        ),
        "target_pending": int(
            raw.get("live-write:row-locked", 0)
            + raw.get("live-write:overlapping-pending-target", 0)
        ),
        "window_budget_exhausted": int(
            raw.get("live-write:window-target-budget", 0)
            + raw.get("live-write:window-delta-budget", 0)
            + raw.get("live-write:pending-capacity", 0)
            + raw.get("live-write:ledger-capacity", 0)
        ),
        "rollback_or_finalization_issue": int(
            raw.get("transaction:rollback-mismatch", 0)
            + raw.get("live-write:commit-rollback-failed", 0)
        ),
    }
    return rows, summary


def _update_visibility(
    state: dict[str, Any],
    counterpart_state: dict[str, Any],
    *,
    source_tick: int,
    final_tick: int,
) -> dict[str, Any]:
    trace = _trace_arrays(state)
    valid = trace["event_valid"]
    proposed = trace["update_family_proposed"] & valid[:, :, None]
    committed = trace["live_write_family_committed"] & valid[:, :, None]
    cfg = state["config"].subject_vm.update_safety
    lower = np.asarray(cfg.parameter_lower_bounds, dtype=np.float64)
    upper = np.asarray(cfg.parameter_upper_bounds, dtype=np.float64)
    ranges = upper - lower

    family_records = []
    for family, name in enumerate(SUBJECT_VM_MODULATION_TARGET_NAMES):
        proposed_mask = proposed[:, :, family]
        committed_mask = committed[:, :, family]
        raw = trace["update_raw_delta"][:, :, family][proposed_mask]
        bounded = trace["update_bounded_delta"][:, :, family][proposed_mask]
        projected_change = (
            trace["update_projected_parameter_value"][:, :, family]
            - trace["update_expected_parameter_value"][:, :, family]
        )[proposed_mask]
        family_records.append({
            "parameter_family": name,
            "proposal_count": int(np.count_nonzero(proposed_mask)),
            "committed_write_count": int(np.count_nonzero(committed_mask)),
            "raw_delta_abs": _stats(np.abs(raw)),
            "bounded_delta_abs": _stats(np.abs(bounded)),
            "projected_change_abs": _stats(np.abs(projected_change)),
            "projected_change_fraction_of_configured_range": _stats(
                np.abs(projected_change) / float(ranges[family]) if ranges[family] > 0 else []
            ),
        })

    bound = trace["binding_family_bound"] & valid[:, :, None]
    target_counter: Counter[str] = Counter()
    region_counter: Counter[str] = Counter()
    storage = state["simulation"]["subject_vm"]["storage"]["arrays"]
    for row, slot, family in zip(*np.nonzero(bound), strict=True):
        kind = int(trace["binding_target_kind"][row, slot, family])
        target_counter["node" if kind == 1 else "edge" if kind == 2 else "none"] += 1
        index = int(trace["binding_target_index"][row, slot, family])
        if kind == 1 and index >= 0:
            region = int(storage["node_region"][row, index])
            region_counter[SUBJECT_VM_REGION_NAMES[region] if region < len(SUBJECT_VM_REGION_NAMES) else f"unknown-{region}"] += 1
        elif kind == 2 and index >= 0:
            region = int(storage["edge_region"][row, index])
            region_counter[SUBJECT_VM_REGION_NAMES[region] if region < len(SUBJECT_VM_REGION_NAMES) else f"unknown-{region}"] += 1

    event_map = _event_index(trace)
    counterpart_trace = _trace_arrays(counterpart_state)
    counterpart_map = _event_index(counterpart_trace)
    active_tick_counts: list[int] = []
    active_event_counts: list[int] = []
    first_commit_tick: int | None = None
    for row, slot in zip(*np.nonzero(trace["live_write_committed"] & valid), strict=True):
        subject_id = int(trace["subject_id"][row, slot])
        applied_tick = int(trace["event_tick"][row, slot])
        due_tick = int(trace["live_write_rollback_due_tick"][row, slot])
        first_commit_tick = applied_tick if first_commit_tick is None else min(first_commit_tick, applied_tick)
        active_ticks = [tick for (sid, tick) in event_map if sid == subject_id and applied_tick < tick < due_tick]
        active_tick_counts.append(len(set(active_ticks)))
        active_event_counts.append(len(active_ticks))

    divergence_timeline = []
    first_difference: dict[str, Any] | None = None
    all_ticks = sorted({tick for _, tick in event_map} | {tick for _, tick in counterpart_map})
    trace_coverage = _trace_tick_coverage(
        source_tick=source_tick, final_tick=final_tick, observed_ticks=all_ticks
    )
    for tick in all_ticks:
        counts = Counter()
        common = sorted(set(event_map) & set(counterpart_map))
        for key in common:
            if key[1] != tick:
                continue
            left = event_map[key]
            right = counterpart_map[key]
            comparisons = {
                "thought_token": "thought_token",
                "action_potentials": "action_potentials",
                "sampled_probability": "sampled_probability",
                "action_id": "action_id",
                "success": "success",
                "objective_delta": "objective_delta",
                "resolution_resource_delta": "resolution_resource_delta",
                "resolution_internal_resource_delta": "resolution_internal_resource_delta",
                "resolution_energy_cost": "resolution_energy_cost",
            }
            for label, array_name in comparisons.items():
                if not np.array_equal(trace[array_name][left], counterpart_trace[array_name][right]):
                    counts[label] += 1
        record = {"tick": int(tick), "matched_subject_events": int(sum(1 for key in common if key[1] == tick)), "difference_counts": dict(sorted(counts.items()))}
        divergence_timeline.append(record)
        if first_difference is None and counts:
            first_difference = {"tick": int(tick), "structures": sorted(counts)}

    return {
        "parameter_families": family_records,
        "target_kind_counts": dict(sorted(target_counter.items())),
        "target_region_counts": dict(sorted(region_counter.items())),
        "temporary_effective_semantic_ticks_per_commit": _stats(active_tick_counts),
        "subject_events_during_temporary_effect_per_commit": _stats(active_event_counts),
        "first_commit_tick": first_commit_tick,
        "branch_divergence_trace_coverage": trace_coverage,
        "branch_divergence_timeline": divergence_timeline,
        "first_observed_branch_difference": first_difference,
        "first_difference_occurs_after_first_live_commit": bool(
            first_difference is None or first_commit_tick is None or int(first_difference["tick"]) > int(first_commit_tick)
        ),
    }


def _admission_and_cost_symmetry(
    live_state: dict[str, Any], control_state: dict[str, Any]
) -> dict[str, Any]:
    live_trace = _trace_arrays(live_state)
    control_trace = _trace_arrays(control_state)
    live_valid = live_trace["event_valid"]
    control_valid = control_trace["event_valid"]
    live_prepared = int(np.count_nonzero(live_trace["transaction_prepared"] & live_valid))
    control_prepared = int(np.count_nonzero(control_trace["transaction_prepared"] & control_valid))
    live_admissions = int(np.count_nonzero(live_trace["live_write_committed"] & live_valid))
    control_reservations = int(np.count_nonzero(
        (control_trace["live_write_reason"] == 12) & control_valid
    ))
    live_transaction_cost = int(np.sum(live_trace["transaction_counted_cost_units"][live_valid]))
    control_transaction_cost = int(np.sum(control_trace["transaction_counted_cost_units"][control_valid]))
    live_evaluation_cost = int(
        live_state["simulation"]["subject_vm"]["evaluation_ledger"]["counters"]["total_counted_cost_units"]
    )
    control_evaluation_cost = int(
        control_state["simulation"]["subject_vm"]["evaluation_ledger"]["counters"]["total_counted_cost_units"]
    )
    admission_count_equal = live_admissions == control_reservations
    evaluation_cost_equal = live_evaluation_cost == control_evaluation_cost
    prepared_count_equal = live_prepared == control_prepared
    transaction_cost_equal = live_transaction_cost == control_transaction_cost
    return {
        "live_prepared_transactions": live_prepared,
        "control_prepared_transactions": control_prepared,
        "prepared_transaction_count_equal": prepared_count_equal,
        "live_admissions": live_admissions,
        "control_reservations": control_reservations,
        "admission_count_equal": admission_count_equal,
        "live_transaction_cost_units": live_transaction_cost,
        "control_transaction_cost_units": control_transaction_cost,
        "transaction_cost_equal": transaction_cost_equal,
        "live_evaluation_cost_units": live_evaluation_cost,
        "control_evaluation_cost_units": control_evaluation_cost,
        "evaluation_cost_equal": evaluation_cost_equal,
        "paired_admission_contract_pass": bool(
            admission_count_equal and evaluation_cost_equal
        ),
        "pre_admission_transaction_path_equal": bool(
            prepared_count_equal and transaction_cost_equal
        ),
        "transaction_path_equality_required_after_branch_divergence": False,
    }


def _association_quality(state: dict[str, Any]) -> dict[str, Any]:
    trace = _trace_arrays(state)
    valid = trace["event_valid"]
    assigned = trace["association_assigned"] & valid
    bound = trace["binding_family_bound"] & valid[:, :, None]
    associated_ids = trace["associated_event_id"][assigned]
    target_keys: list[tuple[int, int, int, int]] = []
    for row, slot, family in zip(*np.nonzero(bound), strict=True):
        target_keys.append((int(trace["subject_id"][row, slot]), int(family), int(trace["binding_target_kind"][row, slot, family]), int(trace["binding_target_id"][row, slot, family])))
    history_counts = Counter(int(value) for value in associated_ids.tolist())
    target_counts = Counter(target_keys)
    similarities = trace["association_similarity"][assigned]
    delays = trace["association_delay_ticks"][assigned]
    eligibility_values = np.abs(trace["binding_eligibility_value"][bound])
    eligibility_ages = trace.get("binding_eligibility_age")
    ages = eligibility_ages[bound] if eligibility_ages is not None else np.asarray([], dtype=np.uint16)
    return {
        "association_delay_ticks": _stats(delays),
        "token_similarity": _stats(similarities),
        "assigned_similarity_exactly_one_fraction": float(np.mean(similarities == np.float32(1.0))) if similarities.size else None,
        "eligibility_value_abs_at_binding": _stats(eligibility_values),
        "eligibility_age_at_binding": _stats(ages),
        "historical_event_reuse": {
            "unique_associated_events": len(history_counts),
            "maximum_associations_to_one_historical_event": max(history_counts.values(), default=0),
            "events_associated_more_than_once": int(sum(value > 1 for value in history_counts.values())),
        },
        "target_rebinding": {
            "unique_subject_family_target_keys": len(target_counts),
            "maximum_bindings_to_one_subject_family_target": max(target_counts.values(), default=0),
            "keys_bound_more_than_once": int(sum(value > 1 for value in target_counts.values())),
        },
        "fixed_nearest_token_candidate_concentration_warning": bool(
            similarities.size > 0 and np.all(similarities == similarities[0]) and np.all(delays == delays[0])
        ),
    }


def _parameter_restoration(source_state: dict[str, Any], final_state: dict[str, Any]) -> dict[str, Any]:
    source_rows = _subject_rows(source_state)
    final_rows = _subject_rows(final_state)
    source_storage = source_state["simulation"]["subject_vm"]["storage"]["arrays"]
    final_storage = final_state["simulation"]["subject_vm"]["storage"]["arrays"]
    arrays = ("node_bias", "node_input_gate", "node_output_gate", "node_trace_gate", "edge_forward_gate", "edge_bandwidth")
    mismatches = Counter()
    checked = 0
    for subject_id in sorted(set(source_rows) & set(final_rows)):
        sr, fr = source_rows[subject_id], final_rows[subject_id]
        checked += 1
        for name in arrays:
            if not np.array_equal(source_storage[name][sr], final_storage[name][fr]):
                mismatches[name] += 1
    return {
        "matched_subject_count": checked,
        "exact_parameter_restoration": not mismatches,
        "parameter_array_subject_mismatch_counts": dict(sorted(mismatches.items())),
    }


def _nonparameter_final_divergence(live_state: dict[str, Any], control_state: dict[str, Any]) -> dict[str, Any]:
    live_entities = live_state["simulation"]["entities"]
    control_entities = control_state["simulation"]["entities"]
    entity_differences = Counter()
    for name, value in vars(live_entities).items():
        other = getattr(control_entities, name, None)
        if isinstance(value, np.ndarray) and isinstance(other, np.ndarray) and not np.array_equal(value, other):
            entity_differences[name] = int(np.count_nonzero(value != other)) if value.shape == other.shape else -1
    live_environment = live_state["simulation"]["environment"]
    control_environment = control_state["simulation"]["environment"]
    environment_differences = Counter()
    for name, value in vars(live_environment).items():
        other = getattr(control_environment, name, None)
        if isinstance(value, np.ndarray) and isinstance(other, np.ndarray) and not np.array_equal(value, other):
            environment_differences[name] = int(np.count_nonzero(value != other)) if value.shape == other.shape else -1
    return {
        "entity_array_difference_counts": dict(sorted(entity_differences.items())),
        "environment_array_difference_counts": dict(sorted(environment_differences.items())),
        "path_dependence_present_after_parameter_restoration": bool(entity_differences or environment_differences),
    }


def _aggregation_sensitivity(reproducibility: dict[str, Any] | None) -> dict[str, Any] | None:
    if reproducibility is None:
        return None
    sources = reproducibility["source_replicates"]
    coordinates = reproducibility["objective_fact_sum_reproducibility"]
    records = []
    for index, coordinate in enumerate(coordinates):
        subject_balanced = np.asarray(coordinate["source_replicate_values"], dtype=np.float64)
        window_weighted = np.asarray([source["diagnostic_window_weighted_objective_fact_mean"][index] for source in sources], dtype=np.float64)
        nonzero_subjects = 0
        total_subjects = 0
        for source in sources:
            for subject in source["subject_summaries"]:
                total_subjects += 1
                nonzero_subjects += int(not np.isclose(subject["objective_fact_window_mean"][index], 0.0, rtol=0.0, atol=1e-12))
        records.append({
            "coordinate": coordinate["coordinate"],
            "subject_balanced_source_values": subject_balanced.tolist(),
            "window_weighted_source_values": window_weighted.tolist(),
            "subject_balanced_median": float(np.median(subject_balanced)),
            "window_weighted_median": float(np.median(window_weighted)),
            "nonzero_source_count": int(np.count_nonzero(~np.isclose(subject_balanced, 0.0, rtol=0.0, atol=1e-12))),
            "nonzero_subject_fraction": float(nonzero_subjects / total_subjects) if total_subjects else None,
            "maximum_abs_subject_vs_window_weighted_source_shift": float(np.max(np.abs(subject_balanced - window_weighted))) if subject_balanced.size else 0.0,
        })
    windows = np.asarray([source["paired_window_count"] for source in sources], dtype=np.float64)
    return {
        "primary_hierarchy_unchanged": "window -> stable subject -> independent source",
        "window_counts_by_source": windows.astype(int).tolist(),
        "window_count_imbalance_ratio_max_over_min": float(np.max(windows) / np.min(windows)) if windows.size and np.min(windows) > 0 else None,
        "objective_fact_sum_coordinates": records,
        "windows_treated_as_independent_replicates": False,
    }


def assess_stage3c10_diagnostics(
    seed_records: Iterable[dict[str, Any]],
    *,
    component_reproducibility: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess already-generated Stage-3C-9 paired branches."""
    per_source = []
    aggregate = Counter()
    for seed_record in seed_records:
        source_meta, source_state = read_checkpoint_bundle(seed_record["source_checkpoint"])
        live_meta, live_state = read_checkpoint_bundle(seed_record["guarded_live_checkpoint"])
        control_meta, control_state = read_checkpoint_bundle(seed_record["read_only_control_checkpoint"])
        bootstrap_subject_ids = [int(value) for value in seed_record["bootstrap_lineage"]["primed_subject_ids"]]
        live_subjects, live_funnel = _branch_subject_funnel(live_state, bootstrap_subject_ids)
        control_subjects, control_funnel = _branch_subject_funnel(control_state, bootstrap_subject_ids)
        visibility = _update_visibility(
            live_state,
            control_state,
            source_tick=int(source_meta["tick"]),
            final_tick=int(live_meta["tick"]),
        )
        live_quality = _association_quality(live_state)
        control_quality = _association_quality(control_state)
        restoration = _parameter_restoration(source_state, live_state)
        final_divergence = _nonparameter_final_divergence(live_state, control_state)
        finalization = seed_record.get("transient_finalization", {})
        admission_symmetry = _admission_and_cost_symmetry(live_state, control_state)
        source_record = {
            "seed": int(seed_record["seed"]),
            "source_checkpoint_state_sha256": source_meta["state_sha256"],
            "source_tick": int(source_meta["tick"]),
            "final_tick": int(live_meta["tick"]),
            "initial_rng_and_state_identity": {
                "shared_source_state_sha256": source_meta["state_sha256"],
                "live_and_control_source_identity_match": bool(
                    next((item.get("source_checkpoint_state_sha256") for item in live_state["checkpoint_lineage"] if item.get("schema") == "se-subject-vm-paired-evaluation-branch-v1"), None)
                    == next((item.get("source_checkpoint_state_sha256") for item in control_state["checkpoint_lineage"] if item.get("schema") == "se-subject-vm-paired-evaluation-branch-v1"), None)
                    == source_meta["state_sha256"]
                ),
            },
            "guarded_live": {"funnel": live_funnel, "subjects": live_subjects, "association_and_eligibility": live_quality},
            "read_only_control": {"funnel": control_funnel, "subjects": control_subjects, "association_and_eligibility": control_quality},
            "update_visibility_and_divergence": visibility,
            "rollback_and_finalization": {
                "parameter_restoration": restoration,
                "live_finalization": finalization.get("guarded-live"),
                "control_finalization": finalization.get("read-only-control"),
                "pending_after_finalization_zero": bool(
                    finalization.get("guarded-live", {}).get("pending_after", 0) == 0
                    and finalization.get("read-only-control", {}).get("pending_after", 0) == 0
                ),
            },
            "post_rollback_nonparameter_state": final_divergence,
            "admission_and_counted_cost_symmetry": admission_symmetry,
            "paired_window_symmetry": {
                "completed_live_windows": int(live_state["simulation"]["subject_vm"]["evaluation_ledger"]["counters"]["total_completed_live_windows"]),
                "completed_control_windows": int(control_state["simulation"]["subject_vm"]["evaluation_ledger"]["counters"]["total_completed_control_windows"]),
                "equal": bool(seed_record["paired_window_count"] == live_state["simulation"]["subject_vm"]["evaluation_ledger"]["counters"]["total_completed_live_windows"] == control_state["simulation"]["subject_vm"]["evaluation_ledger"]["counters"]["total_completed_control_windows"]),
            },
        }
        per_source.append(source_record)
        aggregate["paired_windows"] += int(seed_record["paired_window_count"])
        aggregate["live_commits"] += int(live_state["simulation"]["subject_vm"]["live_write_ledger"]["counters"]["total_committed_transactions"])
        aggregate["sources_with_discrete_action_divergence"] += int(any(item["difference_counts"].get("action_id", 0) > 0 for item in visibility["branch_divergence_timeline"]))
        aggregate["sources_with_objective_event_divergence"] += int(any(item["difference_counts"].get("objective_delta", 0) > 0 for item in visibility["branch_divergence_timeline"]))
        aggregate["sources_with_post_rollback_path_dependence"] += int(final_divergence["path_dependence_present_after_parameter_restoration"])
        aggregate["sources_with_exact_parameter_restoration"] += int(restoration["exact_parameter_restoration"])
        aggregate["sources_with_paired_admission_contract_pass"] += int(
            admission_symmetry["paired_admission_contract_pass"]
        )
        aggregate["sources_with_equal_pre_admission_transaction_path"] += int(
            admission_symmetry["pre_admission_transaction_path_equal"]
        )
        aggregate["sources_with_complete_divergence_trace"] += int(
            visibility["branch_divergence_trace_coverage"]["complete"]
        )
        aggregate["sources_with_retention_limited_divergence_trace"] += int(
            visibility["branch_divergence_trace_coverage"]["retention_limited"]
        )
        aggregate["sources_with_pending_after_finalization"] += int(not source_record["rollback_and_finalization"]["pending_after_finalization_zero"])
        aggregate["action_potential_difference_events"] += int(sum(
            item["difference_counts"].get("action_potentials", 0)
            for item in visibility["branch_divergence_timeline"]
        ))
        aggregate["sampled_probability_difference_events"] += int(sum(
            item["difference_counts"].get("sampled_probability", 0)
            for item in visibility["branch_divergence_timeline"]
        ))
        aggregate["discrete_action_difference_events"] += int(sum(
            item["difference_counts"].get("action_id", 0)
            for item in visibility["branch_divergence_timeline"]
        ))

    all_similarity_degenerate = all(
        source["guarded_live"]["association_and_eligibility"]["fixed_nearest_token_candidate_concentration_warning"]
        for source in per_source
    )
    family_proposals = Counter()
    family_commits = Counter()
    for source in per_source:
        for record in source["update_visibility_and_divergence"]["parameter_families"]:
            family_proposals[record["parameter_family"]] += int(record["proposal_count"])
            family_commits[record["parameter_family"]] += int(record["committed_write_count"])
    nonzero_families = [name for name, count in family_proposals.items() if count > 0]

    contract_error = any(
        not source["initial_rng_and_state_identity"]["live_and_control_source_identity_match"]
        or not source["admission_and_counted_cost_symmetry"]["admission_count_equal"]
        or not source["admission_and_counted_cost_symmetry"]["paired_admission_contract_pass"]
        or not source["paired_window_symmetry"]["equal"]
        or not source["rollback_and_finalization"]["parameter_restoration"]["exact_parameter_restoration"]
        or not source["rollback_and_finalization"]["pending_after_finalization_zero"]
        for source in per_source
    )
    activation_failure = all(
        source["guarded_live"]["funnel"]["subjects_with_tokens"] == 0
        for source in per_source
    )

    payload = {
        "schema": STAGE3C10_DIAGNOSTICS_SCHEMA,
        "independent_source_count": len(per_source),
        "per_source": per_source,
        "aggregate": {
            **dict(sorted(aggregate.items())),
            "parameter_family_proposal_counts": dict(sorted(family_proposals.items())),
            "parameter_family_commit_counts": dict(sorted(family_commits.items())),
            "nonzero_proposal_parameter_families": nonzero_families,
            "nearest_token_similarity_and_delay_degenerate_in_all_sources": all_similarity_degenerate,
        },
        "stage3c8_aggregation_sensitivity": _aggregation_sensitivity(component_reproducibility),
        "diagnostic_interpretation": {
            "data_chain_activation_failure_supported": activation_failure,
            "paired_contract_error_detected": contract_error,
            "dominant_observed_limits": [
                "fixed nearest-token addressing collapses to delay=1 and similarity=1.0 in this short bootstrap",
                "safe proposals and writes are concentrated in one parameter family",
                "temporary writes alter action potentials and sampled probabilities more often than they alter sampled discrete actions",
                "objective event differences therefore appear in fewer independent sources than parameter-level effects",
            ],
            "paired_admission_contract_scope": (
                "control reservations must mirror admitted live target/window capacity and "
                "paired evaluation counted cost; equality of all later shadow-transaction "
                "preparation events is not required after the live branch changes its own "
                "future internal path"
            ),
            "divergence_trace_retention_warning": any(
                source["update_visibility_and_divergence"]
                ["branch_divergence_trace_coverage"]["retention_limited"]
                for source in per_source
            ),
            "next_authorized_path": "diagnostics-and-observability-only",
            "single_variable_mechanism_change_applied": False,
        },
        "objective_coordinate_value_interpretation": None,
        "universal_scalar_objective": False,
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["diagnostics_sha256"] = _canonical_sha256(payload)
    return payload


def build_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze Stage-3C-10 funnel and branch visibility from a study report.")
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report_path = Path(args.study_report).resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    reproducibility = None
    if report.get("component_reproducibility"):
        reproducibility = json.loads(Path(report["component_reproducibility"]).read_text(encoding="utf-8"))
    payload = assess_stage3c10_diagnostics(report["seeds"], component_reproducibility=reproducibility)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["aggregate"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = ["STAGE3C10_DIAGNOSTICS_SCHEMA", "assess_stage3c10_diagnostics"]
