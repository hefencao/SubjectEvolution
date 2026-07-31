#!/usr/bin/env python3
"""Create a deterministic compact archive of the files needed for review.

The bundle is intentionally smaller than a replay archive. It always includes
study definitions and derived analyses, plus selected run metadata. Exact
checkpoints are included only when explicitly requested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

_METADATA_NAMES = {
    "resolved_config.json",
    "run_manifest.json",
    "final_report.json",
    "summary.json",
    "multi_seed_summary.json",
    "progress_summary.json",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file()) if root.exists() else []


def _collect_runtime(root: Path, *, include_checkpoints: bool) -> list[Path]:
    files: list[Path] = []
    for path in _iter_files(root):
        if path.name in _METADATA_NAMES:
            files.append(path)
        elif include_checkpoints and path.suffix == ".sechk":
            files.append(path)
    return files


def build_bundle(
    *,
    project_root: Path,
    study_root: Path,
    analysis_roots: list[Path],
    runtime_roots: list[Path],
    output: Path,
    include_checkpoints: bool,
) -> dict[str, object]:
    project_root = project_root.resolve()
    output = output.resolve()
    try:
        output.relative_to(project_root)
    except ValueError:
        pass
    else:
        raise ValueError("result bundle output must be outside the project tree")
    selected: dict[str, Path] = {}

    def add(path: Path) -> None:
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"bundle input is outside project root: {path}") from exc
        if resolved == output:
            return
        selected[rel.as_posix()] = resolved

    for path in _iter_files(study_root):
        add(path)
    for root in analysis_roots:
        for path in _iter_files(root):
            add(path)
    for root in runtime_roots:
        for path in _collect_runtime(root, include_checkpoints=include_checkpoints):
            add(path)

    files: list[dict[str, object]] = []
    payloads: dict[str, bytes] = {}
    for rel, path in sorted(selected.items()):
        data = path.read_bytes()
        payloads[rel] = data
        files.append({"path": rel, "size": len(data), "sha256": _sha256(data)})

    manifest = {
        "schema": "se-required-result-bundle-v1",
        "study_root": study_root.resolve().relative_to(project_root).as_posix(),
        "include_checkpoints": include_checkpoints,
        "capability": (
            "exact-checkpoint-replay"
            if include_checkpoints
            else "result-review-and-next-step-planning"
        ),
        "files": files,
        "omitted": (
            []
            if include_checkpoints
            else ["checkpoint bytes (*.sechk); hashes remain in paired plans/results"]
        ),
    }
    manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data)
        info = zipfile.ZipInfo("RESULT_BUNDLE_MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(info, manifest_data)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--study-root", required=True)
    parser.add_argument("--analysis-root", action="append", default=[])
    parser.add_argument("--runtime-root", action="append", default=[])
    parser.add_argument("--output", required=True)
    parser.add_argument("--include-checkpoints", action="store_true")
    args = parser.parse_args()
    project_root = Path(args.project_root)
    manifest = build_bundle(
        project_root=project_root,
        study_root=Path(args.study_root),
        analysis_roots=[Path(value) for value in args.analysis_root],
        runtime_roots=[Path(value) for value in args.runtime_root],
        output=Path(args.output),
        include_checkpoints=bool(args.include_checkpoints),
    )
    print(json.dumps({"output": str(Path(args.output)), "file_count": len(manifest["files"]), "capability": manifest["capability"]}))


if __name__ == "__main__":
    main()
