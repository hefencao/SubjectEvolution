"""Stage 3C-8 component-wise reproducibility assessment.

This external analysis consumes one or more Stage-3C-7 integrity assessments
that passed their engineering screen.  It resolves the referenced Stage-3C-6
paired exports, collapses windows within stable subjects, balances subjects
within each independent source checkpoint, and reports coordinate-wise sign,
dispersion, and central-interval stability across source replicates.

No coordinate is assigned engine-defined value.  The report contains no
universal scalar objective, automatic keep/revert decision, causal
authorization, or permanent parameter-retention authorization.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from ..subject_vm.config import SUBJECT_VM_MODULATION_FACT_WIDTH
from ..subject_vm.evaluation_export import PAIRED_WINDOW_EXPORT_SCHEMA
from ..subject_vm.trace import OBJECTIVE_EVENT_DELTA_NAMES
from .subject_vm_paired_evaluation import PAIRED_EVALUATION_EXPORT_SCHEMA
from .subject_vm_paired_evidence import (
    PAIRED_EVIDENCE_ASSESSMENT_SCHEMA,
    _validate_export,
)

COMPONENT_REPRODUCIBILITY_SCHEMA = (
    "se-subject-vm-component-reproducibility-assessment-v1"
)
COMPONENT_REPRODUCIBILITY_SOURCE_SCHEMA = (
    "se-subject-vm-component-reproducibility-source-v1"
)
COMPONENT_REPRODUCIBILITY_COORDINATE_SCHEMA = (
    "se-subject-vm-component-reproducibility-coordinate-v1"
)

OBJECTIVE_FACT_COORDINATE_NAMES = (
    *(f"objective_delta.{name}" for name in OBJECTIVE_EVENT_DELTA_NAMES),
    *(f"resolution_resource_delta.{index}" for index in range(4)),
    *(f"resolution_internal_resource_delta.{index}" for index in range(4)),
    "resolution_energy_cost",
)
if len(OBJECTIVE_FACT_COORDINATE_NAMES) != SUBJECT_VM_MODULATION_FACT_WIDTH:
    raise RuntimeError("subject_vm objective fact coordinate name width mismatch")

_COUNT_COORDINATE_NAMES = (
    "observation_count_difference_live_minus_control",
    "success_count_difference_live_minus_control",
    "failure_count_difference_live_minus_control",
)


@dataclass(frozen=True)
class ComponentReproducibilityParameters:
    """Descriptive coordinate-screen parameters, not a value function."""

    min_independent_sources: int = 3
    zero_tolerance: float = 1.0e-9
    central_interval_lower_quantile: float = 0.10
    central_interval_upper_quantile: float = 0.90
    min_dominant_nonzero_sign_fraction: float = 2.0 / 3.0

    def validate(self) -> None:
        if self.min_independent_sources < 2:
            raise ValueError("min_independent_sources must be at least two")
        if not np.isfinite(self.zero_tolerance) or self.zero_tolerance < 0.0:
            raise ValueError("zero_tolerance must be finite and nonnegative")
        lower = float(self.central_interval_lower_quantile)
        upper = float(self.central_interval_upper_quantile)
        if not (0.0 <= lower < upper <= 1.0):
            raise ValueError("central interval quantiles must satisfy 0 <= lower < upper <= 1")
        fraction = float(self.min_dominant_nonzero_sign_fraction)
        if not 0.5 <= fraction <= 1.0:
            raise ValueError(
                "min_dominant_nonzero_sign_fraction must be within [0.5, 1]"
            )


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate_integrity_assessment(payload: dict[str, Any]) -> None:
    if payload.get("schema") != PAIRED_EVIDENCE_ASSESSMENT_SCHEMA:
        raise ValueError("unsupported Stage-3C-7 paired evidence assessment schema")
    recorded = str(payload.get("assessment_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    if recorded != _canonical_sha256(unsigned):
        raise ValueError("Stage-3C-7 assessment checksum mismatch")
    screen = payload.get("adequacy_screen")
    if not isinstance(screen, dict) or screen.get("passed") is not True:
        raise ValueError("Stage-3C-8 requires a Stage-3C-7 assessment that passed")
    if screen.get("scientific_sufficiency_authorized") is not False:
        raise ValueError("Stage-3C-7 assessment unexpectedly authorizes sufficiency")
    if payload.get("objective_coordinate_weighting") is not None:
        raise ValueError("Stage-3C-7 assessment unexpectedly weights coordinates")
    if payload.get("scalar_score") is not False:
        raise ValueError("Stage-3C-7 assessment unexpectedly authorizes scalar score")
    if payload.get("automatic_keep_or_revert_decision") is not False:
        raise ValueError("Stage-3C-7 assessment unexpectedly authorizes keep/revert")
    if payload.get("causal_effect_authorized") is not False:
        raise ValueError("Stage-3C-7 assessment unexpectedly authorizes causal effect")
    runs = payload.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Stage-3C-7 assessment contains no runs")
    for run in runs:
        if not isinstance(run, dict) or run.get("hard_integrity_pass") is not True:
            raise ValueError("Stage-3C-7 assessment contains a failed run")
        if run.get("scalar_score") is not False:
            raise ValueError("Stage-3C-7 run unexpectedly authorizes scalar score")
        if run.get("automatic_keep_or_revert_decision") is not False:
            raise ValueError("Stage-3C-7 run unexpectedly authorizes keep/revert")
        if run.get("causal_effect_authorized") is not False:
            raise ValueError("Stage-3C-7 run unexpectedly authorizes causal effect")


def _resolve_export_path(
    *,
    run: dict[str, Any],
    assessment_path: Path,
    export_roots: Sequence[Path],
) -> Path:
    recorded = Path(str(run.get("export_path", "")))
    candidates: list[Path] = []
    if str(recorded):
        candidates.append(recorded)
        candidates.append(assessment_path.parent / recorded.name)
        candidates.extend(root / recorded.name for root in export_roots)
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if not resolved.is_file():
            continue
        try:
            payload = _load_json_object(resolved)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if str(payload.get("export_sha256", "")) == str(run.get("export_sha256", "")):
            return resolved
    raise ValueError(
        "unable to resolve Stage-3C-6 export with the checksum recorded by Stage-3C-7: "
        f"{run.get('export_path')}"
    )


def _validate_resolved_export(payload: dict[str, Any], run: dict[str, Any]) -> None:
    _validate_export(payload)
    if payload.get("schema") != PAIRED_EVALUATION_EXPORT_SCHEMA:
        raise ValueError("unsupported Stage-3C-6 paired export schema")
    if str(payload.get("export_sha256")) != str(run.get("export_sha256")):
        raise ValueError("resolved export checksum identity differs from Stage-3C-7 run")
    if str(payload.get("source", {}).get("checkpoint_state_sha256")) != str(
        run.get("source_checkpoint_state_sha256")
    ):
        raise ValueError("resolved export source state differs from Stage-3C-7 run")
    evidence = payload.get("window_evidence")
    if not isinstance(evidence, dict) or evidence.get("schema") != PAIRED_WINDOW_EXPORT_SCHEMA:
        raise ValueError("resolved export lacks Stage-3C-6 window evidence")


def _vector(pair: dict[str, Any], field: str, width: int) -> np.ndarray:
    value = np.asarray(pair.get(field), dtype=np.float64)
    if value.shape != (width,) or np.any(~np.isfinite(value)):
        raise ValueError(f"paired window field {field!r} has invalid shape or values")
    return value


def _subject_balanced_source_summary(
    *,
    assessment_path: Path,
    export_path: Path,
    run: dict[str, Any],
    export_payload: dict[str, Any],
) -> dict[str, Any]:
    pairs = list(export_payload["window_evidence"].get("pairs", []))
    if not pairs:
        raise ValueError("Stage-3C-8 requires at least one paired window per source")
    by_subject: dict[int, list[dict[str, Any]]] = {}
    for pair in pairs:
        live = pair.get("guarded_live")
        control = pair.get("read_only_control")
        if not isinstance(live, dict) or not isinstance(control, dict):
            raise ValueError("paired window lacks guarded-live/control records")
        live_subject = int(live.get("stable_subject_id", 0))
        control_subject = int(control.get("stable_subject_id", 0))
        if live_subject <= 0 or live_subject != control_subject:
            raise ValueError("paired window stable subject identity mismatch")
        by_subject.setdefault(live_subject, []).append(pair)

    subject_summaries: list[dict[str, Any]] = []
    subject_fact_means: list[np.ndarray] = []
    subject_abs_means: list[np.ndarray] = []
    subject_count_means: list[np.ndarray] = []
    all_fact_vectors: list[np.ndarray] = []
    all_abs_vectors: list[np.ndarray] = []
    all_count_vectors: list[np.ndarray] = []
    for subject_id, subject_pairs in sorted(by_subject.items()):
        facts = np.stack(
            [
                _vector(
                    pair,
                    "objective_fact_sum_difference_live_minus_control",
                    SUBJECT_VM_MODULATION_FACT_WIDTH,
                )
                for pair in subject_pairs
            ]
        )
        abs_facts = np.stack(
            [
                _vector(
                    pair,
                    "objective_fact_abs_sum_difference_live_minus_control",
                    SUBJECT_VM_MODULATION_FACT_WIDTH,
                )
                for pair in subject_pairs
            ]
        )
        counts = np.asarray(
            [
                [
                    int(pair["observation_count_difference_live_minus_control"]),
                    int(pair["success_count_difference_live_minus_control"]),
                    int(pair["failure_count_difference_live_minus_control"]),
                ]
                for pair in subject_pairs
            ],
            dtype=np.float64,
        )
        fact_mean = facts.mean(axis=0)
        abs_mean = abs_facts.mean(axis=0)
        count_mean = counts.mean(axis=0)
        subject_fact_means.append(fact_mean)
        subject_abs_means.append(abs_mean)
        subject_count_means.append(count_mean)
        all_fact_vectors.extend(facts)
        all_abs_vectors.extend(abs_facts)
        all_count_vectors.extend(counts)
        subject_summaries.append(
            {
                "stable_subject_id": subject_id,
                "paired_window_count": len(subject_pairs),
                "objective_fact_window_mean": fact_mean.tolist(),
                "objective_fact_window_median": np.median(facts, axis=0).tolist(),
                "objective_fact_abs_window_mean": abs_mean.tolist(),
                "count_difference_window_mean": count_mean.tolist(),
            }
        )

    source_fact = np.stack(subject_fact_means).mean(axis=0)
    source_abs = np.stack(subject_abs_means).mean(axis=0)
    source_counts = np.stack(subject_count_means).mean(axis=0)
    window_fact = np.stack(all_fact_vectors).mean(axis=0)
    window_abs = np.stack(all_abs_vectors).mean(axis=0)
    window_counts = np.stack(all_count_vectors).mean(axis=0)
    return {
        "schema": COMPONENT_REPRODUCIBILITY_SOURCE_SCHEMA,
        "source_checkpoint_state_sha256": str(run["source_checkpoint_state_sha256"]),
        "assessment_path": str(assessment_path),
        "assessment_sha256": str(_load_json_object(assessment_path)["assessment_sha256"]),
        "export_path": str(export_path),
        "export_sha256": str(run["export_sha256"]),
        "plan_sha256": str(run["plan_sha256"]),
        "paired_window_count": len(pairs),
        "stable_subject_count": len(subject_summaries),
        "subject_summaries": subject_summaries,
        "source_subject_balanced_objective_fact_mean": source_fact.tolist(),
        "source_subject_balanced_objective_fact_abs_mean": source_abs.tolist(),
        "source_subject_balanced_count_difference_mean": source_counts.tolist(),
        "diagnostic_window_weighted_objective_fact_mean": window_fact.tolist(),
        "diagnostic_window_weighted_objective_fact_abs_mean": window_abs.tolist(),
        "diagnostic_window_weighted_count_difference_mean": window_counts.tolist(),
        "source_replicate_unit": "independent-source-checkpoint",
        "within_source_window_pseudoreplication_prevented": True,
        "within_source_subject_balancing_applied": True,
    }


def _sign_counts(values: np.ndarray, tolerance: float) -> tuple[int, int, int]:
    positive = int(np.count_nonzero(values > tolerance))
    negative = int(np.count_nonzero(values < -tolerance))
    zero = int(values.size - positive - negative)
    return positive, negative, zero


def _coordinate_summary(
    *,
    name: str,
    values: np.ndarray,
    parameters: ComponentReproducibilityParameters,
) -> dict[str, Any]:
    if values.ndim != 1 or values.size == 0 or np.any(~np.isfinite(values)):
        raise ValueError("coordinate replicate values must be a finite nonempty vector")
    positive, negative, zero = _sign_counts(values, parameters.zero_tolerance)
    counts = {"positive": positive, "negative": negative, "near_zero": zero}
    maximum = max(counts.values())
    leaders = sorted(name_ for name_, count in counts.items() if count == maximum)
    dominant = leaders[0] if len(leaders) == 1 else "tied"
    dominant_nonzero_count = max(positive, negative)
    dominant_nonzero_fraction = float(dominant_nonzero_count / values.size)
    lower = float(
        np.quantile(values, parameters.central_interval_lower_quantile, method="linear")
    )
    upper = float(
        np.quantile(values, parameters.central_interval_upper_quantile, method="linear")
    )
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    interval_excludes_zero = bool(lower > parameters.zero_tolerance or upper < -parameters.zero_tolerance)
    sign_stability = bool(
        values.size >= parameters.min_independent_sources
        and dominant in {"positive", "negative"}
        and dominant_nonzero_fraction
        >= parameters.min_dominant_nonzero_sign_fraction
        and interval_excludes_zero
    )
    return {
        "schema": COMPONENT_REPRODUCIBILITY_COORDINATE_SCHEMA,
        "coordinate": name,
        "independent_source_count": int(values.size),
        "source_replicate_values": [float(item) for item in values.tolist()],
        "sign_counts": counts,
        "sign_fractions": {
            key: float(value / values.size) for key, value in counts.items()
        },
        "dominant_sign": dominant,
        "dominant_nonzero_sign_fraction": dominant_nonzero_fraction,
        "mean": float(np.mean(values)),
        "median": median,
        "sample_standard_deviation": (
            float(np.std(values, ddof=1)) if values.size > 1 else None
        ),
        "median_absolute_deviation": mad,
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "central_interval": {
            "lower_quantile": parameters.central_interval_lower_quantile,
            "upper_quantile": parameters.central_interval_upper_quantile,
            "lower": lower,
            "upper": upper,
            "excludes_zero_with_tolerance": interval_excludes_zero,
        },
        "descriptive_sign_and_interval_stability_screen": sign_stability,
        "screen_is_scientific_sufficiency": False,
        "coordinate_value_interpretation": None,
    }


def _summarize_matrix(
    *,
    names: Sequence[str],
    matrix: np.ndarray,
    parameters: ComponentReproducibilityParameters,
) -> list[dict[str, Any]]:
    if matrix.ndim != 2 or matrix.shape[1] != len(names):
        raise ValueError("source replicate matrix shape mismatch")
    return [
        _coordinate_summary(name=name, values=matrix[:, index], parameters=parameters)
        for index, name in enumerate(names)
    ]


def assess_component_reproducibility(
    assessment_paths: Iterable[str | Path],
    *,
    export_roots: Iterable[str | Path] = (),
    parameters: ComponentReproducibilityParameters | None = None,
) -> dict[str, Any]:
    """Report component-wise reproducibility without scalarizing coordinates."""
    params = parameters or ComponentReproducibilityParameters()
    params.validate()
    paths = [Path(path).expanduser().resolve() for path in assessment_paths]
    if not paths:
        raise ValueError("at least one Stage-3C-7 assessment is required")
    roots = [Path(path).expanduser().resolve() for path in export_roots]

    candidate_sources: list[dict[str, Any]] = []
    assessment_records: list[dict[str, Any]] = []
    for assessment_path in paths:
        payload = _load_json_object(assessment_path)
        _validate_integrity_assessment(payload)
        assessment_records.append(
            {
                "path": str(assessment_path),
                "assessment_sha256": str(payload["assessment_sha256"]),
                "adequacy_screen_passed": True,
                "run_count": len(payload["runs"]),
            }
        )
        for run in payload["runs"]:
            export_path = _resolve_export_path(
                run=run,
                assessment_path=assessment_path,
                export_roots=roots,
            )
            export_payload = _load_json_object(export_path)
            _validate_resolved_export(export_payload, run)
            candidate_sources.append(
                _subject_balanced_source_summary(
                    assessment_path=assessment_path,
                    export_path=export_path,
                    run=run,
                    export_payload=export_payload,
                )
            )

    by_source: dict[str, list[dict[str, Any]]] = {}
    for source in candidate_sources:
        by_source.setdefault(str(source["source_checkpoint_state_sha256"]), []).append(source)
    source_replicates: list[dict[str, Any]] = []
    duplicate_sources: dict[str, int] = {}
    for source_hash, records in sorted(by_source.items()):
        first = records[0]
        signature_fields = (
            "source_subject_balanced_objective_fact_mean",
            "source_subject_balanced_objective_fact_abs_mean",
            "source_subject_balanced_count_difference_mean",
            "paired_window_count",
            "stable_subject_count",
        )
        first_signature = _canonical_sha256(
            {field: first[field] for field in signature_fields}
        )
        for record in records[1:]:
            signature = _canonical_sha256(
                {field: record[field] for field in signature_fields}
            )
            if signature != first_signature:
                raise ValueError(
                    "duplicate source checkpoint produced conflicting reproducibility data"
                )
        if len(records) > 1:
            duplicate_sources[source_hash] = len(records)
        kept = dict(first)
        kept["duplicate_input_occurrence_count"] = len(records)
        kept["duplicate_assessment_paths"] = sorted(
            {str(record["assessment_path"]) for record in records[1:]}
        )
        source_replicates.append(kept)

    if len(source_replicates) < params.min_independent_sources:
        raise ValueError(
            "insufficient independent source checkpoints for Stage-3C-8: "
            f"{len(source_replicates)} < {params.min_independent_sources}"
        )

    fact_matrix = np.asarray(
        [item["source_subject_balanced_objective_fact_mean"] for item in source_replicates],
        dtype=np.float64,
    )
    abs_matrix = np.asarray(
        [
            item["source_subject_balanced_objective_fact_abs_mean"]
            for item in source_replicates
        ],
        dtype=np.float64,
    )
    count_matrix = np.asarray(
        [item["source_subject_balanced_count_difference_mean"] for item in source_replicates],
        dtype=np.float64,
    )
    objective = _summarize_matrix(
        names=OBJECTIVE_FACT_COORDINATE_NAMES,
        matrix=fact_matrix,
        parameters=params,
    )
    objective_abs = _summarize_matrix(
        names=tuple(f"absolute_activity.{name}" for name in OBJECTIVE_FACT_COORDINATE_NAMES),
        matrix=abs_matrix,
        parameters=params,
    )
    counts = _summarize_matrix(
        names=_COUNT_COORDINATE_NAMES,
        matrix=count_matrix,
        parameters=params,
    )
    payload = {
        "schema": COMPONENT_REPRODUCIBILITY_SCHEMA,
        "parameters": asdict(params),
        "parameters_are_descriptive_engineering_screen_only": True,
        "input_stage3c7_assessments": assessment_records,
        "independent_source_count": len(source_replicates),
        "duplicate_source_state_hash_counts": duplicate_sources,
        "replicate_hierarchy": {
            "highest_level_replicate": "independent-source-checkpoint",
            "within_source_first_level": "stable-subject",
            "within_subject_second_level": "paired-window",
            "source_summary": "mean-of-subject-window-means",
            "windows_are_independent_replicates": False,
            "subjects_are_independent_source_replicates": False,
        },
        "source_replicates": source_replicates,
        "objective_fact_sum_reproducibility": objective,
        "objective_fact_abs_sum_reproducibility": objective_abs,
        "count_difference_reproducibility": counts,
        "coordinates_with_descriptive_sign_and_interval_stability": [
            item["coordinate"]
            for item in objective
            if item["descriptive_sign_and_interval_stability_screen"]
        ],
        "coordinates_without_descriptive_sign_and_interval_stability": [
            item["coordinate"]
            for item in objective
            if not item["descriptive_sign_and_interval_stability_screen"]
        ],
        "coordinate_weighting": None,
        "universal_scalar_objective": False,
        "overall_benefit_score": None,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "scientific_reproducibility_conclusion_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess Subject VM Stage-3C-8 component-wise reproducibility."
    )
    parser.add_argument("--assessment", action="append", required=True, dest="assessments")
    parser.add_argument("--export-root", action="append", default=[], dest="export_roots")
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-independent-sources", type=int, default=3)
    parser.add_argument("--zero-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--central-interval-lower-quantile", type=float, default=0.10)
    parser.add_argument("--central-interval-upper-quantile", type=float, default=0.90)
    parser.add_argument(
        "--min-dominant-nonzero-sign-fraction", type=float, default=2.0 / 3.0
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    parameters = ComponentReproducibilityParameters(
        min_independent_sources=args.min_independent_sources,
        zero_tolerance=args.zero_tolerance,
        central_interval_lower_quantile=args.central_interval_lower_quantile,
        central_interval_upper_quantile=args.central_interval_upper_quantile,
        min_dominant_nonzero_sign_fraction=args.min_dominant_nonzero_sign_fraction,
    )
    payload = assess_component_reproducibility(
        args.assessments,
        export_roots=args.export_roots,
        parameters=parameters,
    )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()


__all__ = [
    "COMPONENT_REPRODUCIBILITY_SCHEMA",
    "COMPONENT_REPRODUCIBILITY_SOURCE_SCHEMA",
    "COMPONENT_REPRODUCIBILITY_COORDINATE_SCHEMA",
    "OBJECTIVE_FACT_COORDINATE_NAMES",
    "ComponentReproducibilityParameters",
    "assess_component_reproducibility",
]
