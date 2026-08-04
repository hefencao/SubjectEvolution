"""Deterministically package Stage 3C-42 results, traces and validation evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

_FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def _add(zf: zipfile.ZipFile, path: Path, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname, date_time=_FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    zf.writestr(info, path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--analysis-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    project = Path(args.project).resolve()
    analysis = (project / args.analysis_root).resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    required = [
        project / "protocols/decisions/subject_graph_vm_stage3c42_activation_source_v1.json",
        project / "studies/d1z_subject_vm_stage3c42_activation_source_v1/README.md",
        project / "studies/d1z_subject_vm_stage3c42_activation_source_v1/study.json",
        project / "studies/d1z_subject_vm_stage3c42_activation_source_v1/workflow.toml",
        analysis / "stage3c42/study_report.json",
        analysis / "stage3c42_activation_source.json",
        analysis / "stage3c42_study_summary.json",
        analysis / "stage3c42_diagnostic_report.md",
    ]
    for name in (
        "reference_rank2_study_report.json",
        "reference_stage3c31_alignment_ablation.json",
        "replication_rank2_study_report.json",
        "replication_stage3c31_alignment_ablation.json",
        "stage3c40_categorical_boundary.json",
        "stage3c41_pressure_source.json",
        "subject_vm_activation_contribution_trace_integrity.json",
    ):
        required.append(analysis / "inputs" / name)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing Stage 3C-42 artifacts: " + ", ".join(missing))

    candidates = {path.relative_to(project).as_posix(): path for path in required}
    trace_root = analysis / "stage3c42"
    for path in trace_root.rglob("*"):
        if not path.is_file() or path.name == "study_report.json":
            continue
        if path.suffix in {".sechk", ".csv"}:
            continue
        if path.name in {
            "categorical_sampling_trace.jsonl",
            "categorical_sampling_trace_manifest.json",
            "subject_vm_activation_contribution_trace.jsonl",
            "subject_vm_activation_contribution_trace_manifest.json",
            "branch_identity.json",
            "paired_plan.json",
            "paired_evaluation_export.json",
        }:
            candidates[path.relative_to(project).as_posix()] = path
    for rel in (
        ".validation/FINAL_TEST_REPORT.json",
        ".validation/conda/CONDA_EDITABLE_VALIDATION_REPORT.json",
        ".validation/conda/FINAL_TEST_REPORT.json",
        ".validation/RELEASE_CHECK_REPORT.json",
        ".validation/PATCH_REPLAY_REPORT.json",
        ".validation/SCIENTIFIC_FREEZE_SUMMARY.json",
        ".validation/RELEASE_HANDOFF.json",
    ):
        path = project / rel
        if path.is_file():
            candidates[rel] = path

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for arcname in sorted(candidates):
            _add(zf, candidates[arcname], arcname)
    with zipfile.ZipFile(output) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"corrupt packaged file: {bad}")
    print(output)


if __name__ == "__main__":
    main()
