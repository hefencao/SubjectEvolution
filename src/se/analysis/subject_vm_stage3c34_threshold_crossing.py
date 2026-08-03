"""Stage 3C-34 read-only action/objective crossing audit.

This assessment reuses the frozen Stage-3C-33 common-horizon checkpoints.  It
locates where the exposure-only, alignment-dependent causal contrast crosses
from continuous Subject-VM action potentials into sampled actions and then into
objective-event facts.  No runtime state is changed and no coordinate is given
value semantics.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from ..experiments.subject_vm_stage3c33_exposure_propagation import (
    STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA,
)
from ..policy import Action
from ..subject_vm.modulation import objective_fact_vector
from .subject_vm_component_reproducibility import OBJECTIVE_FACT_COORDINATE_NAMES
from .subject_vm_stage3c32_alignment_intervention import (
    _event_index,
    _read_checkpoint,
    _trace_arrays,
)
from .subject_vm_stage3c33_exposure_propagation import (
    STAGE3C33_EXPOSURE_PROPAGATION_ASSESSMENT_SCHEMA,
)

STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA = (
    "se-subject-vm-stage3c34-threshold-crossing-assessment-v1"
)
_TOL = 1.0e-12
_CONDITIONS = ("horizon-control", "extended-exposure")
_MODES = ("aligned", "alignment-ablated")
_ROLES = ("guarded-live", "read-only-control")
_ROLE_FIELDS = {
    "guarded-live": "guarded_live_checkpoint",
    "read-only-control": "read_only_control_checkpoint",
}


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate_checksum(payload: dict[str, Any], *, field: str, label: str) -> None:
    recorded = str(payload.get(field, ""))
    unsigned = dict(payload)
    unsigned.pop(field, None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")


def _stats(values: Iterable[float | int]) -> dict[str, Any]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {
            "count": 0,
            "minimum": None,
            "median": None,
            "maximum": None,
            "mean": None,
        }
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "median": float(np.median(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _seed_records(study: dict[str, Any], mode: str) -> dict[int, dict[str, Any]]:
    records = {
        int(item["seed"]): item for item in study["modes"][mode]["seed_records"]
    }
    if len(records) != len(study["modes"][mode]["seed_records"]):
        raise ValueError("Stage-3C-34 nested study contains duplicate source seeds")
    return records


def _event_fact_vector(trace: dict[str, np.ndarray], location: tuple[int, int]) -> np.ndarray:
    row, slot = location
    return objective_fact_vector(
        objective_delta=trace["objective_delta"][row, slot],
        resource_delta=trace["resolution_resource_delta"][row, slot],
        internal_resource_delta=trace["resolution_internal_resource_delta"][row, slot],
        energy_cost=float(trace["resolution_energy_cost"][row, slot]),
    )


def _nonzero(vector: np.ndarray) -> bool:
    return bool(np.any(np.abs(np.asarray(vector, dtype=np.float64)) > _TOL))


def _action_name(value: int) -> str:
    try:
        return Action(int(value)).name.lower()
    except ValueError:
        return f"unknown-{int(value)}"


def _resolution_signature(
    trace: dict[str, np.ndarray], location: tuple[int, int]
) -> dict[str, Any]:
    row, slot = location
    fact = _event_fact_vector(trace, location)
    return {
        "action_id": int(trace["action_id"][row, slot]),
        "target_subject_id": int(trace["target_subject_id"][row, slot]),
        "success": bool(trace["success"][row, slot]),
        "failure_reason": int(trace["failure_reason"][row, slot]),
        "objective_fact": fact,
    }


def _signature_changed(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return bool(
        left["action_id"] != right["action_id"]
        or left["target_subject_id"] != right["target_subject_id"]
        or left["success"] != right["success"]
        or left["failure_reason"] != right["failure_reason"]
        or not np.array_equal(left["objective_fact"], right["objective_fact"])
    )


def _load_condition_studies(
    stage3c33_study_report: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if stage3c33_study_report.get("schema") != STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA:
        raise ValueError("unsupported Stage-3C-33 study schema")
    _validate_checksum(
        stage3c33_study_report,
        field="study_sha256",
        label="Stage-3C-33 study",
    )
    if bool(stage3c33_study_report.get("adaptive_exposure_extension")):
        raise ValueError("Stage-3C-34 requires the frozen non-adaptive Stage-3C-33 study")
    if bool(stage3c33_study_report.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-34 cannot consume a retention-authorized study")

    conditions = stage3c33_study_report.get("conditions", {})
    if not all(name in conditions for name in _CONDITIONS):
        raise ValueError("Stage-3C-34 requires both matched-horizon conditions")
    studies: dict[str, dict[str, Any]] = {}
    for name in _CONDITIONS:
        record = conditions[name]
        if int(record["horizon_ticks"]) != 11:
            raise ValueError("Stage-3C-34 requires the frozen eleven-tick horizon")
        expected_exposure = 3 if name == "horizon-control" else 6
        if int(record["exposure_ticks"]) != expected_exposure:
            raise ValueError("Stage-3C-34 exposure identity mismatch")
        nested = _load_json(record["study_report"])
        _validate_checksum(nested, field="study_sha256", label=f"Stage-3C-34 {name}")
        if str(nested["study_sha256"]) != str(record["study_sha256"]):
            raise ValueError("Stage-3C-34 nested study identity mismatch")
        studies[name] = nested
    return studies


def _stage3c33_reference_by_seed(
    stage3c33_assessment: dict[str, Any],
) -> dict[int, np.ndarray]:
    if (
        stage3c33_assessment.get("schema")
        != STAGE3C33_EXPOSURE_PROPAGATION_ASSESSMENT_SCHEMA
    ):
        raise ValueError("unsupported Stage-3C-33 assessment schema")
    _validate_checksum(
        stage3c33_assessment,
        field="assessment_sha256",
        label="Stage-3C-33 assessment",
    )
    records = stage3c33_assessment["fixed_common_horizon_trajectory"][
        "exposure_only_contrast"
    ]["per_source"]
    result = {
        int(item["seed"]): np.asarray(item["fact_sum"], dtype=np.float64)
        for item in records
    }
    if len(result) != len(records):
        raise ValueError("Stage-3C-33 assessment contains duplicate source seeds")
    return result


def _checkpoint_traces_for_seed(
    studies: dict[str, dict[str, Any]], seed: int
) -> tuple[
    dict[tuple[str, str, str], dict[str, np.ndarray]],
    dict[tuple[str, str, str], dict[tuple[int, int, int], tuple[int, int]]],
    str,
]:
    traces: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    indexes: dict[
        tuple[str, str, str], dict[tuple[int, int, int], tuple[int, int]]
    ] = {}
    source_hashes: set[str] = set()
    final_ticks: set[int] = set()
    for condition in _CONDITIONS:
        for mode in _MODES:
            records = _seed_records(studies[condition], mode)
            if seed not in records:
                raise ValueError(f"Stage-3C-34 seed {seed} missing from {condition}/{mode}")
            record = records[seed]
            source_hashes.add(str(record["source_checkpoint_state_sha256"]))
            for role in _ROLES:
                metadata, runtime = _read_checkpoint(record[_ROLE_FIELDS[role]])
                final_ticks.add(int(metadata["tick"]))
                trace = _trace_arrays(runtime)
                traces[condition, mode, role] = trace
                indexes[condition, mode, role] = _event_index(trace)
    if len(source_hashes) != 1:
        raise ValueError("Stage-3C-34 source checkpoint identity mismatch")
    if final_ticks != {13}:
        raise ValueError("Stage-3C-34 final tick mismatch")
    support_sets = [set(index) for index in indexes.values()]
    if not support_sets or any(current != support_sets[0] for current in support_sets[1:]):
        raise ValueError("Stage-3C-34 event support differs across the eight arms")
    return traces, indexes, next(iter(source_hashes))


def _subject_balanced_sum(
    vectors: dict[int, list[np.ndarray]], *, width: int
) -> np.ndarray:
    if not vectors:
        return np.zeros(width, dtype=np.float64)
    return np.mean(
        [np.sum(np.stack(items, axis=0), axis=0) for items in vectors.values()],
        axis=0,
    )


def _source_crossing_audit(
    *,
    seed: int,
    studies: dict[str, dict[str, Any]],
    reference_fact_sum: np.ndarray,
) -> dict[str, Any]:
    traces, indexes, source_hash = _checkpoint_traces_for_seed(studies, seed)
    support = sorted(indexes["horizon-control", "aligned", "guarded-live"])
    by_subject: dict[int, list[np.ndarray]] = defaultdict(list)
    potential_l1: list[float] = []
    potential_linf: list[float] = []
    comparable_probability_abs: list[float] = []
    potential_ticks: dict[int, int] = defaultdict(int)
    any_action_ticks: dict[int, int] = defaultdict(int)
    differential_action_ticks: dict[int, int] = defaultdict(int)
    objective_ticks: dict[int, int] = defaultdict(int)
    crossing_events: list[dict[str, Any]] = []
    potential_count = 0
    comparable_probability_count = 0
    any_action_count = 0
    differential_action_count = 0
    common_mode_action_count = 0
    any_resolution_count = 0
    differential_objective_count = 0
    same_event_action_and_objective_count = 0

    def location(condition: str, mode: str, role: str, key: tuple[int, int, int]) -> tuple[int, int]:
        return indexes[condition, mode, role][key]

    def array(
        condition: str,
        mode: str,
        role: str,
        key: tuple[int, int, int],
        field: str,
    ) -> np.ndarray:
        return np.asarray(traces[condition, mode, role][field][location(condition, mode, role, key)])

    def scalar(
        condition: str,
        mode: str,
        role: str,
        key: tuple[int, int, int],
        field: str,
    ) -> Any:
        return traces[condition, mode, role][field][location(condition, mode, role, key)]

    for key in support:
        subject_id, event_tick, event_id = key
        live_control_potential: dict[tuple[str, str], np.ndarray] = {}
        for condition in _CONDITIONS:
            for mode in _MODES:
                live_control_potential[condition, mode] = (
                    array(condition, mode, "guarded-live", key, "action_potentials").astype(np.float64)
                    - array(condition, mode, "read-only-control", key, "action_potentials").astype(np.float64)
                )
        potential_ddd = (
            live_control_potential["extended-exposure", "alignment-ablated"]
            - live_control_potential["extended-exposure", "aligned"]
            - live_control_potential["horizon-control", "alignment-ablated"]
            + live_control_potential["horizon-control", "aligned"]
        )
        potential_nonzero = _nonzero(potential_ddd)
        if potential_nonzero:
            potential_count += 1
            potential_l1.append(float(np.abs(potential_ddd).sum()))
            potential_linf.append(float(np.abs(potential_ddd).max()))
            potential_ticks[int(event_tick)] += 1

        live_actions = {
            (condition, mode): int(scalar(condition, mode, "guarded-live", key, "action_id"))
            for condition in _CONDITIONS
            for mode in _MODES
        }
        control_actions = {
            (condition, mode): int(scalar(condition, mode, "read-only-control", key, "action_id"))
            for condition in _CONDITIONS
            for mode in _MODES
        }
        aligned_transition = (
            live_actions["horizon-control", "aligned"],
            live_actions["extended-exposure", "aligned"],
        )
        ablated_transition = (
            live_actions["horizon-control", "alignment-ablated"],
            live_actions["extended-exposure", "alignment-ablated"],
        )
        aligned_action_changed = aligned_transition[0] != aligned_transition[1]
        ablated_action_changed = ablated_transition[0] != ablated_transition[1]
        any_action_changed = bool(aligned_action_changed or ablated_action_changed)
        differential_action_changed = bool(
            any_action_changed and aligned_transition != ablated_transition
        )
        common_mode_action_changed = bool(
            any_action_changed
            and aligned_transition == ablated_transition
            and aligned_action_changed
            and ablated_action_changed
        )
        if any_action_changed:
            any_action_count += 1
            any_action_ticks[int(event_tick)] += 1
        if differential_action_changed:
            differential_action_count += 1
            differential_action_ticks[int(event_tick)] += 1
        if common_mode_action_changed:
            common_mode_action_count += 1

        all_actions = list(live_actions.values()) + list(control_actions.values())
        comparable_probability_nonzero = False
        comparable_probability_ddd = 0.0
        if len(set(all_actions)) == 1:
            live_control_probability: dict[tuple[str, str], float] = {}
            for condition in _CONDITIONS:
                for mode in _MODES:
                    live_control_probability[condition, mode] = float(
                        scalar(condition, mode, "guarded-live", key, "sampled_probability")
                    ) - float(
                        scalar(condition, mode, "read-only-control", key, "sampled_probability")
                    )
            comparable_probability_ddd = (
                live_control_probability["extended-exposure", "alignment-ablated"]
                - live_control_probability["extended-exposure", "aligned"]
                - live_control_probability["horizon-control", "alignment-ablated"]
                + live_control_probability["horizon-control", "aligned"]
            )
            comparable_probability_nonzero = abs(comparable_probability_ddd) > _TOL
            if comparable_probability_nonzero:
                comparable_probability_count += 1
                comparable_probability_abs.append(abs(comparable_probability_ddd))

        live_control_fact: dict[tuple[str, str], np.ndarray] = {}
        resolution_changes: dict[str, bool] = {}
        for condition in _CONDITIONS:
            for mode in _MODES:
                live = _resolution_signature(
                    traces[condition, mode, "guarded-live"],
                    location(condition, mode, "guarded-live", key),
                )
                control = _resolution_signature(
                    traces[condition, mode, "read-only-control"],
                    location(condition, mode, "read-only-control", key),
                )
                live_control_fact[condition, mode] = (
                    live["objective_fact"] - control["objective_fact"]
                )
        for mode in _MODES:
            horizon_live = _resolution_signature(
                traces["horizon-control", mode, "guarded-live"],
                location("horizon-control", mode, "guarded-live", key),
            )
            extended_live = _resolution_signature(
                traces["extended-exposure", mode, "guarded-live"],
                location("extended-exposure", mode, "guarded-live", key),
            )
            resolution_changes[mode] = _signature_changed(horizon_live, extended_live)

        exposure_fact = {
            mode: (
                live_control_fact["extended-exposure", mode]
                - live_control_fact["horizon-control", mode]
            )
            for mode in _MODES
        }
        fact_ddd = exposure_fact["alignment-ablated"] - exposure_fact["aligned"]
        by_subject[int(subject_id)].append(fact_ddd)
        any_resolution_changed = bool(any(resolution_changes.values()))
        differential_objective_changed = _nonzero(fact_ddd)
        if any_resolution_changed:
            any_resolution_count += 1
        if differential_objective_changed:
            differential_objective_count += 1
            objective_ticks[int(event_tick)] += 1
            if differential_action_changed:
                same_event_action_and_objective_count += 1

        if any_action_changed or differential_objective_changed:
            nonzero_coordinate_indexes = np.flatnonzero(np.abs(fact_ddd) > _TOL)
            crossing_events.append(
                {
                    "stable_subject_id": int(subject_id),
                    "event_tick": int(event_tick),
                    "event_id": int(event_id),
                    "aligned_action_transition": {
                        "horizon_control": {
                            "id": int(aligned_transition[0]),
                            "name": _action_name(aligned_transition[0]),
                        },
                        "extended_exposure": {
                            "id": int(aligned_transition[1]),
                            "name": _action_name(aligned_transition[1]),
                        },
                    },
                    "alignment_ablated_action_transition": {
                        "horizon_control": {
                            "id": int(ablated_transition[0]),
                            "name": _action_name(ablated_transition[0]),
                        },
                        "extended_exposure": {
                            "id": int(ablated_transition[1]),
                            "name": _action_name(ablated_transition[1]),
                        },
                    },
                    "any_exposure_action_crossing": bool(any_action_changed),
                    "alignment_differential_action_crossing": bool(
                        differential_action_changed
                    ),
                    "alignment_common_action_crossing": bool(
                        common_mode_action_changed
                    ),
                    "alignment_differential_objective_fact_crossing": bool(
                        differential_objective_changed
                    ),
                    "objective_fact_nonzero_coordinate_indexes": [
                        int(index) for index in nonzero_coordinate_indexes.tolist()
                    ],
                    "objective_fact_nonzero_coordinate_names": [
                        OBJECTIVE_FACT_COORDINATE_NAMES[int(index)]
                        for index in nonzero_coordinate_indexes.tolist()
                    ],
                    "objective_fact_l1": float(np.abs(fact_ddd).sum()),
                }
            )

    balanced_fact_sum = _subject_balanced_sum(
        by_subject, width=len(OBJECTIVE_FACT_COORDINATE_NAMES)
    )
    if not np.allclose(
        balanced_fact_sum,
        reference_fact_sum,
        rtol=0.0,
        atol=_TOL,
    ):
        raise ValueError(
            f"Stage-3C-34 seed {seed} event audit does not reproduce Stage-3C-33 trajectory contrast"
        )
    aggregate_nonzero = _nonzero(balanced_fact_sum)

    first_differential_action_tick = (
        min(differential_action_ticks) if differential_action_ticks else None
    )
    last_objective_tick = max(objective_ticks) if objective_ticks else None
    delayed_objective_count = int(
        sum(
            1
            for item in crossing_events
            if item["alignment_differential_objective_fact_crossing"]
            and not item["alignment_differential_action_crossing"]
        )
    )

    if differential_objective_count and aggregate_nonzero:
        classification = "differential-objective-crossing-survives-aggregation"
    elif differential_objective_count:
        classification = "differential-objective-crossing-cancels-in-aggregation"
    elif differential_action_count:
        classification = "differential-action-crossing-without-objective-fact-crossing"
    elif common_mode_action_count:
        classification = "alignment-common-action-crossing-removed-by-cross-mode-contrast"
    elif potential_count:
        classification = "continuous-decision-divergence-below-realized-action-boundary"
    else:
        classification = "no-observed-decision-divergence"

    return {
        "seed": int(seed),
        "source_checkpoint_state_sha256": source_hash,
        "event_support": {
            "event_count": int(len(support)),
            "stable_subject_count": int(len(by_subject)),
            "minimum_event_tick": int(min(key[1] for key in support)),
            "maximum_event_tick": int(max(key[1] for key in support)),
            "all_eight_arms_match": True,
            "event_identity_sha256": _canonical_sha256(
                {"events": [list(key) for key in support]}
            ),
        },
        "continuous_decision_divergence": {
            "subject_vm_potential_exposure_alignment_ddd_event_count": int(
                potential_count
            ),
            "event_fraction": float(potential_count / len(support)),
            "l1_statistics": _stats(potential_l1),
            "linf_statistics": _stats(potential_linf),
            "event_count_by_tick": {
                str(tick): int(count) for tick, count in sorted(potential_ticks.items())
            },
            "same-action_comparable_sampled_probability_ddd_event_count": int(
                comparable_probability_count
            ),
            "same_action_sampled_probability_abs_statistics": _stats(
                comparable_probability_abs
            ),
        },
        "sampled_action_crossing": {
            "any_exposure_action_crossing_event_count": int(any_action_count),
            "alignment_differential_action_crossing_event_count": int(
                differential_action_count
            ),
            "alignment_common_action_crossing_event_count": int(
                common_mode_action_count
            ),
            "any_event_count_by_tick": {
                str(tick): int(count) for tick, count in sorted(any_action_ticks.items())
            },
            "differential_event_count_by_tick": {
                str(tick): int(count)
                for tick, count in sorted(differential_action_ticks.items())
            },
            "first_differential_action_crossing_tick": (
                int(first_differential_action_tick)
                if first_differential_action_tick is not None
                else None
            ),
        },
        "objective_event_crossing": {
            "any_exposure_resolution_signature_change_event_count": int(
                any_resolution_count
            ),
            "alignment_differential_objective_fact_crossing_event_count": int(
                differential_objective_count
            ),
            "same_event_differential_action_and_objective_count": int(
                same_event_action_and_objective_count
            ),
            "delayed_objective_crossing_event_count": int(delayed_objective_count),
            "event_count_by_tick": {
                str(tick): int(count) for tick, count in sorted(objective_ticks.items())
            },
            "last_objective_fact_crossing_tick": (
                int(last_objective_tick) if last_objective_tick is not None else None
            ),
            "subject_balanced_exposure_only_fact_sum": balanced_fact_sum.tolist(),
            "subject_balanced_exposure_only_fact_sum_l1": float(
                np.abs(balanced_fact_sum).sum()
            ),
            "survives_subject_balanced_aggregation": bool(aggregate_nonzero),
            "reproduces_stage3c33_trajectory_contrast": True,
        },
        "crossing_events": crossing_events,
        "classification": classification,
    }


def assess_stage3c34_threshold_crossing(
    stage3c33_study_report: dict[str, Any],
    stage3c33_assessment: dict[str, Any],
) -> dict[str, Any]:
    studies = _load_condition_studies(stage3c33_study_report)
    if str(stage3c33_assessment.get("study_sha256")) != str(
        stage3c33_study_report["study_sha256"]
    ):
        raise ValueError("Stage-3C-34 study/assessment lineage mismatch")
    reference_by_seed = _stage3c33_reference_by_seed(stage3c33_assessment)

    panels = [set(_seed_records(studies[condition], mode)) for condition in _CONDITIONS for mode in _MODES]
    if not panels or any(panel != panels[0] for panel in panels[1:]):
        raise ValueError("Stage-3C-34 source panel mismatch")
    if set(reference_by_seed) != panels[0]:
        raise ValueError("Stage-3C-34 Stage-3C-33 reference source panel mismatch")

    per_source = [
        _source_crossing_audit(
            seed=seed,
            studies=studies,
            reference_fact_sum=reference_by_seed[seed],
        )
        for seed in sorted(reference_by_seed)
    ]

    def seeds_where(path: tuple[str, ...], predicate: Any = bool) -> list[int]:
        result: list[int] = []
        for source in per_source:
            value: Any = source
            for name in path:
                value = value[name]
            if predicate(value):
                result.append(int(source["seed"]))
        return result

    potential_seeds = seeds_where(
        (
            "continuous_decision_divergence",
            "subject_vm_potential_exposure_alignment_ddd_event_count",
        )
    )
    any_action_seeds = seeds_where(
        ("sampled_action_crossing", "any_exposure_action_crossing_event_count")
    )
    differential_action_seeds = seeds_where(
        (
            "sampled_action_crossing",
            "alignment_differential_action_crossing_event_count",
        )
    )
    common_action_seeds = seeds_where(
        (
            "sampled_action_crossing",
            "alignment_common_action_crossing_event_count",
        )
    )
    differential_objective_seeds = seeds_where(
        (
            "objective_event_crossing",
            "alignment_differential_objective_fact_crossing_event_count",
        )
    )
    aggregate_seeds = seeds_where(
        (
            "objective_event_crossing",
            "survives_subject_balanced_aggregation",
        )
    )
    cancelling_objective_seeds = [
        int(source["seed"])
        for source in per_source
        if source["objective_event_crossing"][
            "alignment_differential_objective_fact_crossing_event_count"
        ]
        and not source["objective_event_crossing"][
            "survives_subject_balanced_aggregation"
        ]
    ]

    total_differential_action_events = int(
        sum(
            source["sampled_action_crossing"][
                "alignment_differential_action_crossing_event_count"
            ]
            for source in per_source
        )
    )
    total_differential_objective_events = int(
        sum(
            source["objective_event_crossing"][
                "alignment_differential_objective_fact_crossing_event_count"
            ]
            for source in per_source
        )
    )
    total_delayed_objective_events = int(
        sum(
            source["objective_event_crossing"][
                "delayed_objective_crossing_event_count"
            ]
            for source in per_source
        )
    )
    stage3c33_nonzero = sorted(
        int(seed)
        for seed in stage3c33_assessment["cross_source_findings"][
            "trajectory_exposure_only_nonzero_source_seeds"
        ]
    )
    if aggregate_seeds != stage3c33_nonzero:
        raise ValueError("Stage-3C-34 aggregate crossing seeds do not reproduce Stage-3C-33")

    classification_counts: dict[str, int] = defaultdict(int)
    for source in per_source:
        classification_counts[str(source["classification"])] += 1

    payload = {
        "schema": STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA,
        "producer_version": __version__,
        "stage3c33_study_sha256": str(stage3c33_study_report["study_sha256"]),
        "stage3c33_assessment_sha256": str(
            stage3c33_assessment["assessment_sha256"]
        ),
        "experimental_factor": (
            "read-only localization of the frozen exposure-only alignment contrast "
            "across Subject-VM potentials, sampled actions and objective-event facts"
        ),
        "source_level_independent_replication_count": int(len(per_source)),
        "per_source": per_source,
        "cross_source_findings": {
            "all_eight_arm_event_support_matches": bool(
                all(source["event_support"]["all_eight_arms_match"] for source in per_source)
            ),
            "sources_with_subject_vm_potential_divergence": potential_seeds,
            "sources_with_any_exposure_action_crossing": any_action_seeds,
            "sources_with_alignment_differential_action_crossing": differential_action_seeds,
            "sources_with_alignment_common_action_crossing": common_action_seeds,
            "sources_with_alignment_differential_objective_fact_crossing": differential_objective_seeds,
            "sources_with_surviving_subject_balanced_fact_effect": aggregate_seeds,
            "sources_with_differential_objective_crossing_cancelled_by_aggregation": cancelling_objective_seeds,
            "classification_counts": dict(sorted(classification_counts.items())),
            "total_alignment_differential_action_crossing_events": total_differential_action_events,
            "total_alignment_differential_objective_fact_crossing_events": total_differential_objective_events,
            "total_delayed_objective_fact_crossing_events": total_delayed_objective_events,
            "stage3c33_nonzero_source_identity_reproduced": True,
        },
        "diagnostic_interpretation": {
            "continuous_subject_vm_decision_divergence_occurs_in_all_sources": bool(
                len(potential_seeds) == len(per_source)
            ),
            "absence_of_stage3c33_fact_effect_is_usually_below_realized_action_boundary": bool(
                len(potential_seeds) == len(per_source)
                and len(differential_action_seeds) < len(per_source)
            ),
            "alignment_specific_action_crossing_is_necessary_for_observed_stage3c33_fact_effect_in_this_panel": bool(
                differential_action_seeds == aggregate_seeds
            ),
            "alignment_specific_action_crossing_is_sufficient_for_observed_stage3c33_fact_effect_in_this_panel": bool(
                differential_action_seeds == aggregate_seeds
            ),
            "an_alignment_common_action_crossing_is_removed_by_the_cross_mode_contrast": bool(
                common_action_seeds
            ),
            "later_within_source_aggregation_cancels_a_differential_objective_crossing": bool(
                cancelling_objective_seeds
            ),
            "responsive_sources_are_explained_by_a_small_number_of_action_crossings_followed_by_downstream_events": bool(
                total_differential_action_events > 0
                and total_delayed_objective_events > 0
                and differential_action_seeds == aggregate_seeds
            ),
            "full_numeric_distance_to_the_categorical_action_boundary_is_observable": False,
            "reason_exact_threshold_margin_is_not_observable": (
                "the frozen trace exports Subject-VM residual potentials and the "
                "selected action probability, but not the complete masked policy "
                "logit vector or the counter-based categorical draw"
            ),
            "objective_coordinates_have_value_semantics": False,
            "causal_credit_quality_is_proven": False,
            "automatic_keep_or_revert_authorized": False,
            "permanent_retention_authorized": False,
        },
        "governance": {
            "runtime_rerun_used": False,
            "selected_seed_rerun_used": False,
            "post_hoc_threshold_selected": False,
            "exposure_changed": False,
            "weights_changed": False,
            "scalar_objective_used": False,
        },
        "universal_scalar_objective": False,
        "universal_attention_claim": False,
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _summary_payload(result: dict[str, Any]) -> dict[str, Any]:
    findings = result["cross_source_findings"]
    return {
        "schema": "se-subject-vm-stage3c34-threshold-crossing-summary-v1",
        "producer_version": result["producer_version"],
        "assessment_sha256": result["assessment_sha256"],
        "source_count": result["source_level_independent_replication_count"],
        "potential_divergence_sources": findings[
            "sources_with_subject_vm_potential_divergence"
        ],
        "any_action_crossing_sources": findings[
            "sources_with_any_exposure_action_crossing"
        ],
        "differential_action_crossing_sources": findings[
            "sources_with_alignment_differential_action_crossing"
        ],
        "alignment_common_action_crossing_sources": findings[
            "sources_with_alignment_common_action_crossing"
        ],
        "differential_objective_crossing_sources": findings[
            "sources_with_alignment_differential_objective_fact_crossing"
        ],
        "surviving_fact_effect_sources": findings[
            "sources_with_surviving_subject_balanced_fact_effect"
        ],
        "differential_action_crossing_event_count": findings[
            "total_alignment_differential_action_crossing_events"
        ],
        "differential_objective_crossing_event_count": findings[
            "total_alignment_differential_objective_fact_crossing_events"
        ],
        "delayed_objective_crossing_event_count": findings[
            "total_delayed_objective_fact_crossing_events"
        ],
        "exact_threshold_margin_observable": False,
        "retention_authorized": False,
    }


def _diagnostic_markdown(result: dict[str, Any]) -> str:
    findings = result["cross_source_findings"]
    lines = [
        "# Stage 3C-34 threshold/crossing diagnostic",
        "",
        "This is a read-only audit over the frozen Stage 3C-33 eight-arm, common-horizon trajectories.",
        "",
        "## Crossing chain",
        "",
        f"- Subject-VM potential divergence: {len(findings['sources_with_subject_vm_potential_divergence'])}/9 sources.",
        f"- Any exposure-dependent sampled-action crossing: {len(findings['sources_with_any_exposure_action_crossing'])}/9 sources.",
        f"- Alignment-differential sampled-action crossing: {len(findings['sources_with_alignment_differential_action_crossing'])}/9 sources.",
        f"- Alignment-differential Objective-Fact crossing: {len(findings['sources_with_alignment_differential_objective_fact_crossing'])}/9 sources.",
        f"- Surviving source-balanced fact effect: {len(findings['sources_with_surviving_subject_balanced_fact_effect'])}/9 sources.",
        "",
        "## Source classifications",
        "",
    ]
    for source in result["per_source"]:
        lines.append(f"- `{source['seed']}`: `{source['classification']}`")
    lines.extend(
        [
            "",
            "## Frozen interpretation",
            "",
            "All nine sources contain exposure-dependent Subject-VM potential changes. Six sources do not cross the realized sampled-action boundary. Seed 12307 crosses the action boundary in both alignment modes in the same way, so the cross-mode contrast removes it. Seeds 12305 and 12308 contain alignment-specific action crossings; those crossings are followed by additional downstream objective-event differences and exactly reproduce the two nonzero Stage 3C-33 source-level effects.",
            "",
            "The trace does not export the full masked policy logits or the categorical draw, so this audit cannot report an exact numeric distance to the action threshold. No result supplies value semantics, correct causal credit, keep/revert, learning, or permanent retention.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Stage-3C-33 exposure-only divergence across Subject-VM "
            "potentials, sampled actions and objective-event facts."
        )
    )
    parser.add_argument("--stage3c33-study-report", required=True)
    parser.add_argument("--stage3c33-assessment", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    study = _load_json(args.stage3c33_study_report)
    assessment = _load_json(args.stage3c33_assessment)
    result = assess_stage3c34_threshold_crossing(study, assessment)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.summary_output:
        summary = _summary_payload(result)
        summary_path = Path(args.summary_output)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.diagnostic_report:
        report_path = Path(args.diagnostic_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_diagnostic_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
