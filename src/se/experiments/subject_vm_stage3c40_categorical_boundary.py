"""Stage 3C-40 exact categorical action-boundary study.

The study replays the frozen reference and disjoint rank-two source panels with
only the two matched-horizon Stage-3C-33 conditions used by the boundary audit:
3-tick and 6-tick temporary exposure at an 11-tick horizon.  Every branch uses
the already-qualified observation-only categorical sampling trace.  Sampling,
random streams, exposure values, source panels and runtime semantics are fixed.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
from typing import Any

from .. import __version__
from .subject_vm_short_paired_study import _canonical_sha256, _write_json
from .subject_vm_stage3c32_alignment_intervention import (
    Stage3C32InterventionParameters,
    run_stage3c32_alignment_intervention,
)
from .subject_vm_stage3c33_exposure_propagation import (
    STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA,
)

STAGE3C40_CATEGORICAL_BOUNDARY_STUDY_SCHEMA = (
    "se-subject-vm-stage3c40-categorical-boundary-study-v1"
)
_CONDITIONS = {
    "horizon-control": 3,
    "extended-exposure": 6,
}


@dataclass(frozen=True)
class Stage3C40Parameters:
    common_horizon_ticks: int = 11
    baseline_exposure_ticks: int = 3
    extended_exposure_ticks: int = 6
    backend: str = "auto"

    def validate(self) -> None:
        if self.baseline_exposure_ticks < 1:
            raise ValueError("Stage-3C-40 baseline exposure must be positive")
        if self.extended_exposure_ticks <= self.baseline_exposure_ticks:
            raise ValueError("Stage-3C-40 extended exposure must exceed baseline")
        if self.common_horizon_ticks <= self.extended_exposure_ticks:
            raise ValueError("Stage-3C-40 common horizon must exceed exposure")
        if self.backend not in {"cpu", "auto"}:
            raise ValueError("Stage-3C-40 supports CPU or auto execution")


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(path)
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=False)


def _source_signature(study: dict[str, Any]) -> list[dict[str, Any]]:
    result = [
        {
            "seed": int(item["seed"]),
            "checkpoint_file_sha256": str(item["checkpoint_file_sha256"]),
            "checkpoint_state_sha256": str(item["checkpoint_state_sha256"]),
            "checkpoint_config_sha256": str(item["checkpoint_config_sha256"]),
            "checkpoint_tick": int(item["checkpoint_tick"]),
        }
        for item in study.get("source_identities", [])
    ]
    return sorted(result, key=lambda item: item["seed"])


def _trace_manifest_count(study: dict[str, Any]) -> int:
    count = 0
    if not bool(study.get("categorical_sampling_trace_enabled")):
        raise ValueError("Stage-3C-40 condition trace is not enabled")
    for mode in ("aligned", "alignment-ablated"):
        for record in study["modes"][mode]["seed_records"]:
            manifests = record.get("categorical_sampling_trace_manifests")
            if not isinstance(manifests, dict):
                raise ValueError("Stage-3C-40 trace manifest record is missing")
            for role in ("guarded-live", "read-only-control"):
                path = manifests.get(role)
                if not path or not Path(path).is_file():
                    raise ValueError("Stage-3C-40 trace manifest file is missing")
                count += 1
    return count


def _panel_parent(
    *,
    panel: str,
    rank2_study_report: Path,
    stage3c31_assessment: Path,
    panel_root: Path,
    parameters: Stage3C40Parameters,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    conditions: dict[str, dict[str, Any]] = {}
    signature: list[dict[str, Any]] | None = None
    for condition, exposure in _CONDITIONS.items():
        path = (panel_root / condition / "study_report.json").resolve()
        nested = _load_json(path)
        recorded = str(nested.get("study_sha256", ""))
        unsigned = dict(nested)
        unsigned.pop("study_sha256", None)
        if not recorded or recorded != _canonical_sha256(unsigned):
            raise ValueError(f"Stage-3C-40 {panel}/{condition} checksum mismatch")
        current = _source_signature(nested)
        if signature is None:
            signature = current
        elif current != signature:
            raise ValueError("Stage-3C-40 source identity differs by condition")
        conditions[condition] = {
            "role": (
                "matched-horizon-baseline"
                if condition == "horizon-control"
                else "isolate-temporary-exposure"
            ),
            "horizon_ticks": int(parameters.common_horizon_ticks),
            "exposure_ticks": int(exposure),
            "study_report": str(path),
            "study_sha256": recorded,
            "source_signature": current,
            "trace_manifest_count": _trace_manifest_count(nested),
        }
    assert signature is not None
    parent: dict[str, Any] = {
        "schema": STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA,
        "producer_version": __version__,
        "rank2_study_report": str(rank2_study_report.resolve()),
        "stage3c31_assessment": str(stage3c31_assessment.resolve()),
        "parameters": {
            "common_horizon_ticks": int(parameters.common_horizon_ticks),
            "baseline_exposure_ticks": int(parameters.baseline_exposure_ticks),
            "extended_exposure_ticks": int(parameters.extended_exposure_ticks),
            "backend": parameters.backend,
            "categorical_sampling_trace": True,
        },
        "conditions": conditions,
        "factor_isolation": {
            "horizon_control_to_extended_exposure_changes_only_exposure": True,
            "common_horizon_ticks": int(parameters.common_horizon_ticks),
            "baseline_exposure_ticks": int(parameters.baseline_exposure_ticks),
            "extended_exposure_ticks": int(parameters.extended_exposure_ticks),
            "frozen_baseline_omitted_from_stage3c40_boundary_audit": True,
        },
        "shared_source_checkpoint_across_all_eight_arms": True,
        "same_runtime_alignment_code_path_in_all_conditions": True,
        "categorical_sampling_trace_enabled": True,
        "categorical_sampling_trace_is_observation_only": True,
        "forced_rollback": True,
        "adaptive_exposure_extension": False,
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    parent["study_sha256"] = _canonical_sha256(parent)
    _write_json(panel_root / "study_report.json", parent)
    return parent, signature


def assemble_stage3c40_categorical_boundary_study(
    *,
    reference_rank2_study_report: str | Path,
    reference_stage3c31_assessment: str | Path,
    replication_rank2_study_report: str | Path,
    replication_stage3c31_assessment: str | Path,
    trace_integrity_assessment: str | Path,
    output_dir: str | Path,
    parameters: Stage3C40Parameters = Stage3C40Parameters(),
) -> dict[str, Any]:
    parameters.validate()
    root = Path(output_dir).expanduser().resolve()
    integrity_path = Path(trace_integrity_assessment).expanduser().resolve()
    integrity = _load_json(integrity_path)
    if not bool(integrity.get("passed")):
        raise ValueError("Stage-3C-40 requires a passing categorical trace integrity gate")
    panel_inputs = {
        "reference": (
            Path(reference_rank2_study_report).expanduser().resolve(),
            Path(reference_stage3c31_assessment).expanduser().resolve(),
        ),
        "replication": (
            Path(replication_rank2_study_report).expanduser().resolve(),
            Path(replication_stage3c31_assessment).expanduser().resolve(),
        ),
    }
    panels: dict[str, dict[str, Any]] = {}
    signatures: dict[str, list[dict[str, Any]]] = {}
    for panel, (rank2_path, stage31_path) in panel_inputs.items():
        parent, signature = _panel_parent(
            panel=panel,
            rank2_study_report=rank2_path,
            stage3c31_assessment=stage31_path,
            panel_root=root / panel,
            parameters=parameters,
        )
        signatures[panel] = signature
        panels[panel] = {
            "rank2_study_report": str(rank2_path),
            "stage3c31_assessment": str(stage31_path),
            "study_report": str((root / panel / "study_report.json").resolve()),
            "study_sha256": str(parent["study_sha256"]),
            "source_signature": [
                {
                    "seed": item["seed"],
                    "checkpoint_state_sha256": item["checkpoint_state_sha256"],
                    "checkpoint_config_sha256": item["checkpoint_config_sha256"],
                    "checkpoint_tick": item["checkpoint_tick"],
                }
                for item in signature
            ],
            "trace_manifest_count": sum(
                int(parent["conditions"][name]["trace_manifest_count"])
                for name in _CONDITIONS
            ),
        }
    reference_seeds = {item["seed"] for item in signatures["reference"]}
    replication_seeds = {item["seed"] for item in signatures["replication"]}
    if len(reference_seeds) != 9 or len(replication_seeds) != 9:
        raise ValueError("Stage-3C-40 requires two nine-source panels")
    if reference_seeds & replication_seeds:
        raise ValueError("Stage-3C-40 source panels must remain disjoint")
    payload: dict[str, Any] = {
        "schema": STAGE3C40_CATEGORICAL_BOUNDARY_STUDY_SCHEMA,
        "producer_version": __version__,
        "parameters": asdict(parameters),
        "trace_integrity_assessment": str(integrity_path),
        "trace_integrity_assessment_sha256": str(integrity["assessment_sha256"]),
        "panels": panels,
        "source_panels_are_disjoint": True,
        "categorical_sampling_trace_enabled": True,
        "categorical_sampling_trace_is_observation_only": True,
        "runtime_sampling_semantics_changed": False,
        "random_stream_changed": False,
        "exposure_or_horizon_changed_from_stage3c33": False,
        "post_hoc_source_selection": False,
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
    }
    payload["study_sha256"] = _canonical_sha256(payload)
    _write_json(root / "study_report.json", payload)
    return payload


def run_stage3c40_categorical_boundary_study(
    *,
    reference_rank2_study_report: str | Path,
    reference_stage3c31_assessment: str | Path,
    replication_rank2_study_report: str | Path,
    replication_stage3c31_assessment: str | Path,
    trace_integrity_assessment: str | Path,
    output_dir: str | Path,
    parameters: Stage3C40Parameters = Stage3C40Parameters(),
    overwrite: bool = False,
) -> dict[str, Any]:
    parameters.validate()
    root = Path(output_dir).expanduser().resolve()
    _prepare_output(root, overwrite=overwrite)
    panel_inputs = {
        "reference": (reference_rank2_study_report, reference_stage3c31_assessment),
        "replication": (replication_rank2_study_report, replication_stage3c31_assessment),
    }
    for panel, (rank2, stage31) in panel_inputs.items():
        for condition, exposure in _CONDITIONS.items():
            run_stage3c32_alignment_intervention(
                rank2_study_report=rank2,
                stage3c31_assessment=stage31,
                output_dir=root / panel / condition,
                parameters=Stage3C32InterventionParameters(
                    horizon_ticks=parameters.common_horizon_ticks,
                    rollback_after_ticks=exposure,
                    backend=parameters.backend,
                    categorical_sampling_trace=True,
                ),
                overwrite=False,
            )
    return assemble_stage3c40_categorical_boundary_study(
        reference_rank2_study_report=reference_rank2_study_report,
        reference_stage3c31_assessment=reference_stage3c31_assessment,
        replication_rank2_study_report=replication_rank2_study_report,
        replication_stage3c31_assessment=replication_stage3c31_assessment,
        trace_integrity_assessment=trace_integrity_assessment,
        output_dir=root,
        parameters=parameters,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="运行或组装 Stage 3C-40 精确 categorical boundary trace study。"
    )
    parser.add_argument("--reference-rank2-study-report", required=True)
    parser.add_argument("--reference-stage3c31-assessment", required=True)
    parser.add_argument("--replication-rank2-study-report", required=True)
    parser.add_argument("--replication-stage3c31-assessment", required=True)
    parser.add_argument("--trace-integrity-assessment", required=True)
    parser.add_argument("--backend", choices=("cpu", "auto"), default="auto")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--assemble-existing", action="store_true")
    args = parser.parse_args()
    parameters = Stage3C40Parameters(backend=args.backend)
    function = (
        assemble_stage3c40_categorical_boundary_study
        if args.assemble_existing
        else run_stage3c40_categorical_boundary_study
    )
    kwargs = dict(
        reference_rank2_study_report=args.reference_rank2_study_report,
        reference_stage3c31_assessment=args.reference_stage3c31_assessment,
        replication_rank2_study_report=args.replication_rank2_study_report,
        replication_stage3c31_assessment=args.replication_stage3c31_assessment,
        trace_integrity_assessment=args.trace_integrity_assessment,
        output_dir=args.output,
        parameters=parameters,
    )
    if not args.assemble_existing:
        kwargs["overwrite"] = args.overwrite
    result = function(**kwargs)
    print(json.dumps({"study_sha256": result["study_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C40_CATEGORICAL_BOUNDARY_STUDY_SCHEMA",
    "Stage3C40Parameters",
    "assemble_stage3c40_categorical_boundary_study",
    "run_stage3c40_categorical_boundary_study",
]
