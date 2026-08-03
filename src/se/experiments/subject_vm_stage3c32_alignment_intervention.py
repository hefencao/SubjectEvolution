"""Stage 3C-32 shared-checkpoint runtime alignment intervention panel.

The experiment consumes the frozen Stage-3C-23 rank-two source checkpoints.
For every independent source it runs two explicit association-address modes
through the same runtime path:

* tickwise subject identity alignment;
* tickwise cyclic subject-donor alignment ablation.

Each mode contains the ordinary guarded-live/read-only-control pair.  All four
branches therefore share one source checkpoint, branch horizon, random stream,
storage layout, rollback contract and component-wise score-free evaluation.
No branch authorizes permanent retention or an automatic keep/revert choice.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import shutil
from typing import Any

from .. import __version__
from ..analysis.subject_vm_component_reproducibility import (
    assess_component_reproducibility,
)
from ..analysis.subject_vm_paired_evaluation import build_plan, run_plan
from ..analysis.subject_vm_paired_evidence import assess_exports
from ..analysis.subject_vm_stage3c10_diagnostics import assess_stage3c10_diagnostics
from ..analysis.subject_vm_stage3c23_dual_readout_rank import _validate_study
from ..analysis.subject_vm_stage3c31_alignment_ablation import (
    STAGE3C31_ALIGNMENT_ABLATION_SCHEMA,
    _validate_assessment_checksum,
)
from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.trace import (
    ASSOCIATION_ALIGNMENT_CYCLIC_DONOR,
    ASSOCIATION_ALIGNMENT_IDENTITY,
)
from .subject_vm_short_paired_study import _canonical_sha256, _sha256_file, _write_json

STAGE3C32_ALIGNMENT_INTERVENTION_STUDY_SCHEMA = (
    "se-subject-vm-stage3c32-alignment-intervention-study-v1"
)
_ALIGNMENT_PORT = 30
_ALIGNMENT_MODES = {
    "aligned": ASSOCIATION_ALIGNMENT_IDENTITY,
    "alignment-ablated": ASSOCIATION_ALIGNMENT_CYCLIC_DONOR,
}


@dataclass(frozen=True)
class Stage3C32InterventionParameters:
    horizon_ticks: int = 8
    rollback_after_ticks: int = 3
    backend: str = "auto"

    def validate(self) -> None:
        if int(self.horizon_ticks) < int(self.rollback_after_ticks) + 1:
            raise ValueError("Stage-3C-32 horizon must exceed rollback exposure")
        if int(self.rollback_after_ticks) < 1:
            raise ValueError("Stage-3C-32 rollback exposure must be positive")
        if self.backend not in {"cpu", "auto"}:
            raise ValueError("Stage-3C-32 supports CPU or auto execution")


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate_study_checksum(study: dict[str, Any]) -> None:
    recorded = str(study.get("study_sha256", ""))
    unsigned = dict(study)
    unsigned.pop("study_sha256", None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError("Stage-3C-32 rank-two study checksum mismatch")


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(path)
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=False)


def _mode_seed_record(
    *,
    seed: int,
    source_record: dict[str, Any],
    plan_path: Path,
    plan: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    export_path = Path(result["export"]).resolve()
    export_payload = _load_json(export_path)
    evidence = export_payload["window_evidence"]
    return {
        "seed": int(seed),
        "source_checkpoint": str(Path(source_record["source_checkpoint"]).resolve()),
        "source_checkpoint_file_sha256": str(
            source_record["source_checkpoint_file_sha256"]
        ),
        "source_checkpoint_state_sha256": str(
            source_record["source_checkpoint_state_sha256"]
        ),
        "source_tick": int(source_record["source_tick"]),
        "final_tick": int(plan["final_tick"]),
        "bootstrap_lineage": source_record["bootstrap_lineage"],
        "plan": str(plan_path.resolve()),
        "plan_sha256": str(plan["plan_sha256"]),
        "guarded_live_checkpoint": str(
            Path(result["guarded_live_checkpoint"]).resolve()
        ),
        "read_only_control_checkpoint": str(
            Path(result["read_only_control_checkpoint"]).resolve()
        ),
        "transient_finalization": result["transient_finalization"],
        "export": str(export_path),
        "export_sha256": str(export_payload["export_sha256"]),
        "paired_window_count": int(evidence["paired_window_count"]),
        "unpaired_guarded_live_count": len(evidence["unpaired_guarded_live"]),
        "unpaired_read_only_control_count": len(
            evidence["unpaired_read_only_control"]
        ),
    }


def run_stage3c32_alignment_intervention(
    *,
    rank2_study_report: str | Path,
    stage3c31_assessment: str | Path,
    output_dir: str | Path,
    parameters: Stage3C32InterventionParameters = Stage3C32InterventionParameters(),
    overwrite: bool = False,
) -> dict[str, Any]:
    parameters.validate()
    rank2_path = Path(rank2_study_report).expanduser().resolve()
    stage3c31_path = Path(stage3c31_assessment).expanduser().resolve()
    rank2 = _load_json(rank2_path)
    stage3c31 = _load_json(stage3c31_path)
    _validate_study(rank2, second_port=7)
    _validate_study_checksum(rank2)
    if stage3c31.get("schema") != STAGE3C31_ALIGNMENT_ABLATION_SCHEMA:
        raise ValueError("Stage-3C-32 requires the frozen Stage-3C-31 assessment")
    _validate_assessment_checksum(stage3c31, label="Stage-3C-31 assessment")
    if str(stage3c31.get("rank2_study_sha256")) != str(rank2["study_sha256"]):
        raise ValueError("Stage-3C-32 Stage-3C-31/rank-two lineage mismatch")
    if bool(stage3c31.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-32 cannot consume retention-authorizing evidence")

    root = Path(output_dir).expanduser().resolve()
    _prepare_output(root, overwrite=overwrite)
    resolved_backend = "cpu" if parameters.backend == "auto" else parameters.backend
    source_records = list(rank2.get("seeds", ()))
    if len(source_records) < 3:
        raise ValueError("Stage-3C-32 requires independent source replication")

    per_mode_records: dict[str, list[dict[str, Any]]] = {
        mode: [] for mode in _ALIGNMENT_MODES
    }
    export_paths: dict[str, list[Path]] = {mode: [] for mode in _ALIGNMENT_MODES}
    source_identities: list[dict[str, Any]] = []

    for source_record in source_records:
        seed = int(source_record["seed"])
        source = Path(source_record["source_checkpoint"]).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if _sha256_file(source) != str(
            source_record["source_checkpoint_file_sha256"]
        ):
            raise ValueError("Stage-3C-32 source checkpoint file checksum mismatch")
        metadata, _ = read_checkpoint_bundle(source)
        if str(metadata["state_sha256"]) != str(
            source_record["source_checkpoint_state_sha256"]
        ):
            raise ValueError("Stage-3C-32 source checkpoint state mismatch")
        source_tick = int(metadata["tick"])
        source_identities.append(
            {
                "seed": seed,
                "checkpoint": str(source),
                "checkpoint_file_sha256": _sha256_file(source),
                "checkpoint_state_sha256": str(metadata["state_sha256"]),
                "checkpoint_config_sha256": str(metadata["config_sha256"]),
                "checkpoint_tick": source_tick,
            }
        )

        seed_root = root / f"seed_{seed}"
        for mode_name, runtime_mode in _ALIGNMENT_MODES.items():
            mode_root = seed_root / mode_name
            plan = build_plan(
                source,
                horizon_ticks=int(parameters.horizon_ticks),
                finalize_pending_transients_at_export=True,
                rollback_after_ticks_override=int(parameters.rollback_after_ticks),
                association_coordinate_alignment_mode_override=runtime_mode,
                association_coordinate_alignment_port_override=_ALIGNMENT_PORT,
                association_coordinate_alignment_origin_tick_override=source_tick,
            )
            plan_path = mode_root / "paired_plan.json"
            _write_json(plan_path, plan)
            run_result = run_plan(
                plan,
                source_checkpoint=source,
                output_dir=mode_root / "paired",
                backend=resolved_backend,
            )
            record = _mode_seed_record(
                seed=seed,
                source_record=source_record,
                plan_path=plan_path,
                plan=plan,
                result=run_result,
            )
            per_mode_records[mode_name].append(record)
            export_paths[mode_name].append(Path(record["export"]))

    mode_reports: dict[str, dict[str, Any]] = {}
    for mode_name in _ALIGNMENT_MODES:
        mode_root = root / mode_name
        mode_root.mkdir(parents=True, exist_ok=True)
        integrity = assess_exports(export_paths[mode_name])
        integrity_path = mode_root / "paired_evidence_assessment.json"
        _write_json(integrity_path, integrity)
        reproducibility = None
        reproducibility_path = mode_root / "component_reproducibility.json"
        if bool(integrity["adequacy_screen"]["passed"]):
            reproducibility = assess_component_reproducibility([integrity_path])
            _write_json(reproducibility_path, reproducibility)
        diagnostics = assess_stage3c10_diagnostics(
            per_mode_records[mode_name],
            component_reproducibility=reproducibility,
        )
        diagnostics_path = mode_root / "stage3c10_diagnostics.json"
        _write_json(diagnostics_path, diagnostics)
        mode_reports[mode_name] = {
            "runtime_alignment_mode": _ALIGNMENT_MODES[mode_name],
            "seed_records": per_mode_records[mode_name],
            "paired_evidence_assessment": str(integrity_path.resolve()),
            "paired_evidence_assessment_sha256": integrity["assessment_sha256"],
            "component_reproducibility": (
                str(reproducibility_path.resolve())
                if reproducibility is not None
                else None
            ),
            "component_reproducibility_sha256": (
                reproducibility["assessment_sha256"]
                if reproducibility is not None
                else None
            ),
            "stage3c10_diagnostics": str(diagnostics_path.resolve()),
            "stage3c10_diagnostics_sha256": diagnostics["diagnostics_sha256"],
            "engineering_screen_passed": bool(
                integrity["adequacy_screen"]["passed"]
            ),
        }

    payload = {
        "schema": STAGE3C32_ALIGNMENT_INTERVENTION_STUDY_SCHEMA,
        "producer_version": __version__,
        "rank2_study_report": str(rank2_path),
        "rank2_study_sha256": str(rank2["study_sha256"]),
        "stage3c31_assessment": str(stage3c31_path),
        "stage3c31_assessment_sha256": str(stage3c31["assessment_sha256"]),
        "parameters": asdict(parameters),
        "alignment_port": _ALIGNMENT_PORT,
        "source_identities": source_identities,
        "modes": mode_reports,
        "four_arm_design": [
            "aligned/read-only-control",
            "aligned/guarded-live",
            "alignment-ablated/read-only-control",
            "alignment-ablated/guarded-live",
        ],
        "shared_source_checkpoint_across_all_four_arms": True,
        "same_runtime_alignment_code_path_in_both_modes": True,
        "branch_specific_persistent_storage_added": False,
        "forced_rollback": True,
        "componentwise_score_free_evaluation": True,
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["study_sha256"] = _canonical_sha256(payload)
    _write_json(root / "study_report.json", payload)
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Stage-3C-32 aligned and cyclic-donor runtime intervention pairs "
            "from the same frozen rank-two source checkpoints."
        )
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--stage3c31-assessment", required=True)
    parser.add_argument("--horizon-ticks", type=int, default=8)
    parser.add_argument("--rollback-after-ticks", type=int, default=3)
    parser.add_argument("--backend", choices=("cpu", "auto"), default="auto")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    run_stage3c32_alignment_intervention(
        rank2_study_report=args.rank2_study_report,
        stage3c31_assessment=args.stage3c31_assessment,
        output_dir=args.output,
        parameters=Stage3C32InterventionParameters(
            horizon_ticks=args.horizon_ticks,
            rollback_after_ticks=args.rollback_after_ticks,
            backend=args.backend,
        ),
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
