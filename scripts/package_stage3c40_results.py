"""Deterministically package Stage 3C-40 traces, reports and validation evidence."""
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
        project / "protocols/decisions/subject_graph_vm_stage3c40_categorical_boundary_v1.json",
        project / "studies/d1z_subject_vm_stage3c40_categorical_boundary_v1/README.md",
        project / "studies/d1z_subject_vm_stage3c40_categorical_boundary_v1/study.json",
        project / "studies/d1z_subject_vm_stage3c40_categorical_boundary_v1/workflow.toml",
        analysis / "stage3c40_categorical_boundary.json",
        analysis / "stage3c40_study_summary.json",
        analysis / "stage3c40_diagnostic_report.md",
        analysis / "stage3c40/study_report.json",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("missing Stage 3C-40 artifacts: " + ", ".join(missing))

    candidates: dict[str, Path] = {}
    for path in required:
        candidates[path.relative_to(project).as_posix()] = path
    for path in analysis.rglob("*"):
        if not path.is_file():
            continue
        rel_analysis = path.relative_to(analysis)
        if "frozen-baseline" in rel_analysis.parts:
            continue
        if path.suffix in {".sechk", ".pyc", ".pyo"}:
            continue
        if "__pycache__" in rel_analysis.parts:
            continue
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
