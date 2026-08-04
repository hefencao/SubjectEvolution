"""Deterministically package ThoughtEvent T3 results and validation evidence."""
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
        project / "protocols/decisions/subject_vm_thought_event_t3_recall_v1.json",
        project / "studies/d1z_subject_vm_thought_event_t3_recall_v1/README.md",
        project / "studies/d1z_subject_vm_thought_event_t3_recall_v1/study.json",
        project / "studies/d1z_subject_vm_thought_event_t3_recall_v1/workflow.toml",
        analysis / "study/study_report.json",
        analysis / "thought_event_t3_recall.json",
        analysis / "thought_event_t3_summary.md",
    ]
    study_root = analysis / "study"
    for path in study_root.rglob("*"):
        if path.is_file() and path.name in {
            "seed_record.json",
            "thought_events.npz",
            "bootstrap_profiles.json",
        }:
            required.append(path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing T3 artifacts: " + ", ".join(missing))

    candidates = {path.relative_to(project).as_posix(): path for path in required}
    for rel in (
        ".validation/FINAL_TEST_REPORT.json",
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
