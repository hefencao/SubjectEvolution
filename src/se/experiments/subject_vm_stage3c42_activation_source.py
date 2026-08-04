"""Stage 3C-42 targeted activation-contribution trace study.

The study replays only the source identities frozen before this stage:
reference crossing sources 12305/12308, reference alignment-common source
12307, and the replication panel's highest Stage-3C-41 opportunity source
12401.  The selected top-five event identities per source are inherited from
Stage 3C-40.  Runtime semantics, checkpoints, exposure, alignment modes and
sampling remain unchanged; only the already-qualified observation traces are
enabled for the selected subjects.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
from typing import Any

from .. import __version__
from ..analysis.subject_vm_paired_evaluation import build_plan, run_plan
from ..analysis.subject_vm_stage3c23_dual_readout_rank import _validate_study
from ..analysis.subject_vm_stage3c31_alignment_ablation import (
    STAGE3C31_ALIGNMENT_ABLATION_SCHEMA,
    _validate_assessment_checksum,
)
from ..analysis.subject_vm_stage3c40_categorical_boundary import (
    STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA,
)
from ..analysis.subject_vm_stage3c41_pressure_source import (
    STAGE3C41_PRESSURE_SOURCE_ASSESSMENT_SCHEMA,
)
from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.trace import (
    ASSOCIATION_ALIGNMENT_CYCLIC_DONOR,
    ASSOCIATION_ALIGNMENT_IDENTITY,
)
from .subject_vm_short_paired_study import _canonical_sha256, _sha256_file, _write_json

STAGE3C42_ACTIVATION_SOURCE_STUDY_SCHEMA = (
    "se-subject-vm-stage3c42-activation-source-study-v1"
)
_ALIGNMENT_PORT = 30
_ALIGNMENT_MODES = {
    "aligned": ASSOCIATION_ALIGNMENT_IDENTITY,
    "alignment-ablated": ASSOCIATION_ALIGNMENT_CYCLIC_DONOR,
}
_CONDITIONS = {"horizon-control": 3, "extended-exposure": 6}
_SELECTED_SEEDS = {"reference": (12305, 12307, 12308), "replication": (12401,)}


@dataclass(frozen=True)
class Stage3C42Parameters:
    common_horizon_ticks: int = 11
    baseline_exposure_ticks: int = 3
    extended_exposure_ticks: int = 6
    backend: str = "auto"

    def validate(self) -> None:
        if self.baseline_exposure_ticks != 3:
            raise ValueError("Stage-3C-42 baseline exposure is frozen at 3 ticks")
        if self.extended_exposure_ticks != 6:
            raise ValueError("Stage-3C-42 extended exposure is frozen at 6 ticks")
        if self.common_horizon_ticks != 11:
            raise ValueError("Stage-3C-42 horizon is frozen at 11 ticks")
        if self.backend not in {"cpu", "auto"}:
            raise ValueError("Stage-3C-42 supports CPU or auto execution")


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


def _validate_inputs(
    *,
    rank2: dict[str, Any],
    stage3c31: dict[str, Any],
    stage3c40: dict[str, Any],
    stage3c41: dict[str, Any],
    integrity: dict[str, Any],
) -> None:
    _validate_study(rank2, second_port=7)
    _validate_checksum(rank2, field="study_sha256", label="Stage-3C-42 rank-two study")
    if stage3c31.get("schema") != STAGE3C31_ALIGNMENT_ABLATION_SCHEMA:
        raise ValueError("Stage-3C-42 requires Stage-3C-31 assessment")
    _validate_assessment_checksum(stage3c31, label="Stage-3C-31 assessment")
    if str(stage3c31.get("rank2_study_sha256")) != str(rank2["study_sha256"]):
        raise ValueError("Stage-3C-42 Stage-3C-31/rank-two lineage mismatch")
    if stage3c40.get("schema") != STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA:
        raise ValueError("Stage-3C-42 requires Stage-3C-40 assessment")
    _validate_checksum(
        stage3c40, field="assessment_sha256", label="Stage-3C-40 assessment"
    )
    if stage3c41.get("schema") != STAGE3C41_PRESSURE_SOURCE_ASSESSMENT_SCHEMA:
        raise ValueError("Stage-3C-42 requires Stage-3C-41 assessment")
    _validate_checksum(
        stage3c41, field="assessment_sha256", label="Stage-3C-41 assessment"
    )
    if str(stage3c41.get("stage3c40_assessment_sha256")) != str(
        stage3c40["assessment_sha256"]
    ):
        raise ValueError("Stage-3C-42 Stage-3C-40/41 lineage mismatch")
    if not bool(integrity.get("stage3c42_authorized_next")):
        raise ValueError("Stage-3C-42 activation trace integrity gate did not authorize study")
    _validate_checksum(
        integrity,
        field="assessment_sha256",
        label="Stage-3C-42 activation trace integrity",
    )
    if bool(integrity.get("runtime_semantics_changed")):
        raise ValueError("Stage-3C-42 cannot use a semantics-changing trace")


def _selected_events(
    stage3c40: dict[str, Any], *, panel: str, seed: int
) -> list[dict[str, int]]:
    records = [
        item
        for item in stage3c40["panels"][panel]["per_source"]
        if int(item["seed"]) == int(seed)
    ]
    if len(records) != 1:
        raise ValueError("Stage-3C-42 selected source is missing or ambiguous")
    opportunities = records[0].get("top_boundary_opportunities", [])
    if len(opportunities) != 5:
        raise ValueError("Stage-3C-42 requires frozen top-five opportunities")
    return [
        {
            "subject_id": int(item["subject_id"]),
            "tick": int(item["tick"]),
            "event_id": int(item["event_id"]),
        }
        for item in opportunities
    ]


def _source_record(rank2: dict[str, Any], seed: int) -> dict[str, Any]:
    records = [item for item in rank2.get("seeds", []) if int(item["seed"]) == seed]
    if len(records) != 1:
        raise ValueError("Stage-3C-42 selected rank-two source is missing or ambiguous")
    record = records[0]
    source = Path(record["source_checkpoint"]).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if _sha256_file(source) != str(record["source_checkpoint_file_sha256"]):
        raise ValueError("Stage-3C-42 source checkpoint file checksum mismatch")
    metadata, _ = read_checkpoint_bundle(source)
    if str(metadata["state_sha256"]) != str(record["source_checkpoint_state_sha256"]):
        raise ValueError("Stage-3C-42 source checkpoint state mismatch")
    return record


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(path)
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=False)


def run_stage3c42_activation_source_study(
    *,
    reference_rank2_study_report: str | Path,
    reference_stage3c31_assessment: str | Path,
    replication_rank2_study_report: str | Path,
    replication_stage3c31_assessment: str | Path,
    stage3c40_assessment: str | Path,
    stage3c41_assessment: str | Path,
    activation_trace_integrity: str | Path,
    output_dir: str | Path,
    parameters: Stage3C42Parameters = Stage3C42Parameters(),
    overwrite: bool = False,
) -> dict[str, Any]:
    parameters.validate()
    paths = {
        "reference_rank2": Path(reference_rank2_study_report).expanduser().resolve(),
        "reference_stage3c31": Path(reference_stage3c31_assessment).expanduser().resolve(),
        "replication_rank2": Path(replication_rank2_study_report).expanduser().resolve(),
        "replication_stage3c31": Path(replication_stage3c31_assessment).expanduser().resolve(),
        "stage3c40": Path(stage3c40_assessment).expanduser().resolve(),
        "stage3c41": Path(stage3c41_assessment).expanduser().resolve(),
        "integrity": Path(activation_trace_integrity).expanduser().resolve(),
    }
    stage3c40 = _load_json(paths["stage3c40"])
    stage3c41 = _load_json(paths["stage3c41"])
    integrity = _load_json(paths["integrity"])
    panel_inputs = {
        "reference": (
            _load_json(paths["reference_rank2"]),
            _load_json(paths["reference_stage3c31"]),
        ),
        "replication": (
            _load_json(paths["replication_rank2"]),
            _load_json(paths["replication_stage3c31"]),
        ),
    }
    for rank2, stage31 in panel_inputs.values():
        _validate_inputs(
            rank2=rank2,
            stage3c31=stage31,
            stage3c40=stage3c40,
            stage3c41=stage3c41,
            integrity=integrity,
        )

    root = Path(output_dir).expanduser().resolve()
    _prepare_output(root, overwrite=overwrite)
    backend = "cpu" if parameters.backend == "auto" else parameters.backend
    sources: list[dict[str, Any]] = []
    manifest_count = 0

    for panel, selected_seeds in _SELECTED_SEEDS.items():
        rank2, _stage31 = panel_inputs[panel]
        for seed in selected_seeds:
            source_record = _source_record(rank2, seed)
            source = Path(source_record["source_checkpoint"]).expanduser().resolve()
            events = _selected_events(stage3c40, panel=panel, seed=seed)
            subjects = tuple(sorted({item["subject_id"] for item in events}))
            source_tick = int(source_record["source_tick"])
            source_output: dict[str, Any] = {
                "panel": panel,
                "seed": seed,
                "source_checkpoint": str(source),
                "source_checkpoint_file_sha256": str(
                    source_record["source_checkpoint_file_sha256"]
                ),
                "source_checkpoint_state_sha256": str(
                    source_record["source_checkpoint_state_sha256"]
                ),
                "source_tick": source_tick,
                "selected_events": events,
                "selected_subject_ids": list(subjects),
                "conditions": {},
            }
            for condition, exposure in _CONDITIONS.items():
                condition_output: dict[str, Any] = {}
                for mode_name, runtime_mode in _ALIGNMENT_MODES.items():
                    mode_root = root / panel / f"seed_{seed}" / condition / mode_name
                    plan = build_plan(
                        source,
                        horizon_ticks=parameters.common_horizon_ticks,
                        finalize_pending_transients_at_export=True,
                        rollback_after_ticks_override=exposure,
                        association_coordinate_alignment_mode_override=runtime_mode,
                        association_coordinate_alignment_port_override=_ALIGNMENT_PORT,
                        association_coordinate_alignment_origin_tick_override=source_tick,
                    )
                    plan_path = mode_root / "paired_plan.json"
                    _write_json(plan_path, plan)
                    result = run_plan(
                        plan,
                        source_checkpoint=source,
                        output_dir=mode_root / "paired",
                        backend=backend,
                        categorical_sampling_trace=True,
                        categorical_sampling_trace_subject_ids=subjects,
                        subject_vm_activation_contribution_trace=True,
                        subject_vm_activation_contribution_trace_subject_ids=subjects,
                    )
                    categorical = result["categorical_sampling_trace_manifests"]
                    activation = result[
                        "subject_vm_activation_contribution_trace_manifests"
                    ]
                    if not all(categorical.values()) or not all(activation.values()):
                        raise ValueError("Stage-3C-42 trace manifest is missing")
                    manifest_count += len(categorical) + len(activation)
                    condition_output[mode_name] = {
                        "plan": str(plan_path),
                        "plan_sha256": str(plan["plan_sha256"]),
                        "paired_export": str(result["export"]),
                        "categorical_sampling_trace_manifests": categorical,
                        "activation_contribution_trace_manifests": activation,
                        "guarded_live_checkpoint": str(result["guarded_live_checkpoint"]),
                        "read_only_control_checkpoint": str(
                            result["read_only_control_checkpoint"]
                        ),
                    }
                source_output["conditions"][condition] = condition_output
            sources.append(source_output)

    payload: dict[str, Any] = {
        "schema": STAGE3C42_ACTIVATION_SOURCE_STUDY_SCHEMA,
        "producer_version": __version__,
        "parameters": asdict(parameters),
        "input_paths": {name: str(path) for name, path in paths.items()},
        "input_checksums": {
            "stage3c40_assessment": str(stage3c40["assessment_sha256"]),
            "stage3c41_assessment": str(stage3c41["assessment_sha256"]),
            "activation_trace_integrity": str(integrity["assessment_sha256"]),
        },
        "selection_contract": {
            "reference_seeds": list(_SELECTED_SEEDS["reference"]),
            "replication_seeds": list(_SELECTED_SEEDS["replication"]),
            "events_per_source": 5,
            "selection_source": "Stage-3C-40 frozen top-five boundary opportunities",
            "selection_changed_after_trace_observation": False,
        },
        "sources": sources,
        "trace_manifest_count": manifest_count,
        "categorical_sampling_trace_enabled": True,
        "activation_contribution_trace_enabled": True,
        "trace_is_observation_only": True,
        "runtime_semantics_changed": False,
        "random_stream_changed": False,
        "source_panel_changed": False,
        "exposure_or_horizon_changed": False,
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["study_sha256"] = _canonical_sha256(payload)
    _write_json(root / "study_report.json", payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="运行 Stage 3C-42 REST activation contribution 来源审计 trace study。"
    )
    parser.add_argument("--reference-rank2-study-report", required=True)
    parser.add_argument("--reference-stage3c31-assessment", required=True)
    parser.add_argument("--replication-rank2-study-report", required=True)
    parser.add_argument("--replication-stage3c31-assessment", required=True)
    parser.add_argument("--stage3c40-assessment", required=True)
    parser.add_argument("--stage3c41-assessment", required=True)
    parser.add_argument("--activation-trace-integrity", required=True)
    parser.add_argument("--backend", choices=("cpu", "auto"), default="auto")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = run_stage3c42_activation_source_study(
        reference_rank2_study_report=args.reference_rank2_study_report,
        reference_stage3c31_assessment=args.reference_stage3c31_assessment,
        replication_rank2_study_report=args.replication_rank2_study_report,
        replication_stage3c31_assessment=args.replication_stage3c31_assessment,
        stage3c40_assessment=args.stage3c40_assessment,
        stage3c41_assessment=args.stage3c41_assessment,
        activation_trace_integrity=args.activation_trace_integrity,
        output_dir=args.output,
        parameters=Stage3C42Parameters(backend=args.backend),
        overwrite=args.overwrite,
    )
    print(json.dumps({"study_sha256": result["study_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C42_ACTIVATION_SOURCE_STUDY_SCHEMA",
    "Stage3C42Parameters",
    "run_stage3c42_activation_source_study",
]
