"""Stage 3C-33 predeclared exposure-length propagation panel.

The study keeps the Stage-3C-32 four-arm runtime alignment intervention and
adds one factor-isolating horizon control:

* frozen baseline: 3-tick exposure, 8-tick branch horizon;
* horizon control: 3-tick exposure, 11-tick branch horizon;
* extended exposure: 6-tick exposure, 11-tick branch horizon.

The horizon-control versus extended-exposure contrast therefore changes only
temporary live/control reservation duration.  The frozen-baseline versus
horizon-control contrast separately measures observation-horizon effects.
All conditions use the same rank-two source checkpoints and retain forced
rollback, score-free component-wise evaluation, and no retention authority.
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

STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA = (
    "se-subject-vm-stage3c33-exposure-propagation-study-v1"
)


@dataclass(frozen=True)
class Stage3C33ExposureParameters:
    frozen_baseline_horizon_ticks: int = 8
    common_horizon_ticks: int = 11
    baseline_exposure_ticks: int = 3
    extended_exposure_ticks: int = 6
    backend: str = "auto"
    categorical_sampling_trace: bool = False

    def validate(self) -> None:
        if int(self.baseline_exposure_ticks) < 1:
            raise ValueError("Stage-3C-33 baseline exposure must be positive")
        if int(self.extended_exposure_ticks) <= int(self.baseline_exposure_ticks):
            raise ValueError("Stage-3C-33 extended exposure must exceed baseline")
        if int(self.frozen_baseline_horizon_ticks) <= int(
            self.baseline_exposure_ticks
        ):
            raise ValueError("Stage-3C-33 frozen horizon must exceed exposure")
        if int(self.common_horizon_ticks) <= int(self.extended_exposure_ticks):
            raise ValueError("Stage-3C-33 common horizon must exceed extended exposure")
        if self.backend not in {"cpu", "auto"}:
            raise ValueError("Stage-3C-33 supports CPU or auto execution")


@dataclass(frozen=True)
class _Condition:
    name: str
    horizon_ticks: int
    exposure_ticks: int
    role: str


def _conditions(parameters: Stage3C33ExposureParameters) -> tuple[_Condition, ...]:
    return (
        _Condition(
            name="frozen-baseline",
            horizon_ticks=int(parameters.frozen_baseline_horizon_ticks),
            exposure_ticks=int(parameters.baseline_exposure_ticks),
            role="reproduce-stage3c32-baseline",
        ),
        _Condition(
            name="horizon-control",
            horizon_ticks=int(parameters.common_horizon_ticks),
            exposure_ticks=int(parameters.baseline_exposure_ticks),
            role="isolate-observation-horizon",
        ),
        _Condition(
            name="extended-exposure",
            horizon_ticks=int(parameters.common_horizon_ticks),
            exposure_ticks=int(parameters.extended_exposure_ticks),
            role="isolate-temporary-exposure",
        ),
    )


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
    result = []
    for item in study.get("source_identities", []):
        result.append(
            {
                "seed": int(item["seed"]),
                "checkpoint_file_sha256": str(item["checkpoint_file_sha256"]),
                "checkpoint_state_sha256": str(item["checkpoint_state_sha256"]),
                "checkpoint_config_sha256": str(item["checkpoint_config_sha256"]),
                "checkpoint_tick": int(item["checkpoint_tick"]),
            }
        )
    return sorted(result, key=lambda item: item["seed"])


def run_stage3c33_exposure_propagation(
    *,
    rank2_study_report: str | Path,
    stage3c31_assessment: str | Path,
    output_dir: str | Path,
    parameters: Stage3C33ExposureParameters = Stage3C33ExposureParameters(),
    overwrite: bool = False,
) -> dict[str, Any]:
    parameters.validate()
    root = Path(output_dir).expanduser().resolve()
    _prepare_output(root, overwrite=overwrite)

    condition_reports: dict[str, dict[str, Any]] = {}
    source_signature: list[dict[str, Any]] | None = None
    for condition in _conditions(parameters):
        condition_root = root / condition.name
        report = run_stage3c32_alignment_intervention(
            rank2_study_report=rank2_study_report,
            stage3c31_assessment=stage3c31_assessment,
            output_dir=condition_root,
            parameters=Stage3C32InterventionParameters(
                horizon_ticks=condition.horizon_ticks,
                rollback_after_ticks=condition.exposure_ticks,
                backend=parameters.backend,
                categorical_sampling_trace=bool(
                    parameters.categorical_sampling_trace
                ),
            ),
            overwrite=False,
        )
        report_path = condition_root / "study_report.json"
        if not report_path.is_file():
            raise RuntimeError("Stage-3C-33 nested Stage-3C-32 report is missing")
        persisted = _load_json(report_path)
        if persisted.get("study_sha256") != report.get("study_sha256"):
            raise ValueError("Stage-3C-33 nested study persistence mismatch")
        current_signature = _source_signature(report)
        if source_signature is None:
            source_signature = current_signature
        elif current_signature != source_signature:
            raise ValueError("Stage-3C-33 source checkpoint identity differs by condition")
        condition_reports[condition.name] = {
            "role": condition.role,
            "horizon_ticks": condition.horizon_ticks,
            "exposure_ticks": condition.exposure_ticks,
            "study_report": str(report_path.resolve()),
            "study_sha256": str(report["study_sha256"]),
            "source_signature": current_signature,
        }

    payload = {
        "schema": STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA,
        "producer_version": __version__,
        "rank2_study_report": str(Path(rank2_study_report).expanduser().resolve()),
        "stage3c31_assessment": str(
            Path(stage3c31_assessment).expanduser().resolve()
        ),
        "parameters": asdict(parameters),
        "conditions": condition_reports,
        "factor_isolation": {
            "frozen_baseline_to_horizon_control_changes_only_horizon": True,
            "horizon_control_to_extended_exposure_changes_only_exposure": True,
            "common_horizon_ticks": int(parameters.common_horizon_ticks),
            "baseline_exposure_ticks": int(parameters.baseline_exposure_ticks),
            "extended_exposure_ticks": int(parameters.extended_exposure_ticks),
        },
        "shared_source_checkpoint_across_all_twelve_arms": True,
        "same_runtime_alignment_code_path_in_all_conditions": True,
        "categorical_sampling_trace_enabled": bool(
            parameters.categorical_sampling_trace
        ),
        "categorical_sampling_trace_is_observation_only": True,
        "forced_rollback": True,
        "componentwise_score_free_evaluation": True,
        "adaptive_exposure_extension": False,
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["study_sha256"] = _canonical_sha256(payload)
    _write_json(root / "study_report.json", payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Stage-3C-33 frozen-baseline, horizon-control and "
            "extended-exposure four-arm panels."
        )
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--stage3c31-assessment", required=True)
    parser.add_argument("--frozen-baseline-horizon-ticks", type=int, default=8)
    parser.add_argument("--common-horizon-ticks", type=int, default=11)
    parser.add_argument("--baseline-exposure-ticks", type=int, default=3)
    parser.add_argument("--extended-exposure-ticks", type=int, default=6)
    parser.add_argument("--backend", choices=("cpu", "auto"), default="auto")
    parser.add_argument("--categorical-sampling-trace", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_stage3c33_exposure_propagation(
        rank2_study_report=args.rank2_study_report,
        stage3c31_assessment=args.stage3c31_assessment,
        output_dir=args.output,
        parameters=Stage3C33ExposureParameters(
            frozen_baseline_horizon_ticks=args.frozen_baseline_horizon_ticks,
            common_horizon_ticks=args.common_horizon_ticks,
            baseline_exposure_ticks=args.baseline_exposure_ticks,
            extended_exposure_ticks=args.extended_exposure_ticks,
            backend=args.backend,
            categorical_sampling_trace=args.categorical_sampling_trace,
        ),
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
