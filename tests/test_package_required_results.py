from __future__ import annotations

import json
from pathlib import Path
import zipfile

from scripts.package_required_results import build_bundle


def test_compact_bundle_is_deterministic_and_omits_checkpoints(tmp_path: Path) -> None:
    study = tmp_path / "studies/demo"
    analysis = tmp_path / "analyses/demo"
    runtime = tmp_path / "runs/base/demo/seed_1"
    study.mkdir(parents=True)
    analysis.mkdir(parents=True)
    runtime.mkdir(parents=True)
    (study / "DESIGN.md").write_text("design\n", encoding="utf-8")
    (analysis / "paired_results.json").write_text("{}\n", encoding="utf-8")
    (runtime / "resolved_config.json").write_text("{}\n", encoding="utf-8")
    (runtime / "checkpoint_00000001.sechk").write_bytes(b"checkpoint")
    external = tmp_path.parent / f"{tmp_path.name}_results"
    first = external / "first.zip"
    second = external / "second.zip"
    kwargs = dict(
        project_root=tmp_path,
        study_root=study,
        analysis_roots=[analysis],
        runtime_roots=[runtime.parent.parent],
        include_checkpoints=False,
    )
    build_bundle(output=first, **kwargs)
    build_bundle(output=second, **kwargs)
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        assert "studies/demo/DESIGN.md" in names
        assert "analyses/demo/paired_results.json" in names
        assert "runs/base/demo/seed_1/resolved_config.json" in names
        assert not any(name.endswith(".sechk") for name in names)
        manifest = json.loads(archive.read("RESULT_BUNDLE_MANIFEST.json"))
        assert manifest["capability"] == "result-review-and-next-step-planning"


def test_replay_bundle_can_include_checkpoints(tmp_path: Path) -> None:
    study = tmp_path / "studies/demo"
    runtime = tmp_path / "runs/base/demo/seed_1"
    study.mkdir(parents=True)
    runtime.mkdir(parents=True)
    (study / "DESIGN.md").write_text("design\n", encoding="utf-8")
    (runtime / "checkpoint_00000001.sechk").write_bytes(b"checkpoint")
    output = tmp_path.parent / f"{tmp_path.name}_results" / "replay.zip"
    manifest = build_bundle(
        project_root=tmp_path,
        study_root=study,
        analysis_roots=[],
        runtime_roots=[runtime.parent.parent],
        output=output,
        include_checkpoints=True,
    )
    assert manifest["capability"] == "exact-checkpoint-replay"
    with zipfile.ZipFile(output) as archive:
        assert "runs/base/demo/seed_1/checkpoint_00000001.sechk" in archive.namelist()


def test_compact_bundle_rejects_project_internal_output(tmp_path: Path) -> None:
    study = tmp_path / "studies/demo"
    study.mkdir(parents=True)
    (study / "DESIGN.md").write_text("design\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="outside the project tree"):
        build_bundle(
            project_root=tmp_path,
            study_root=study,
            analysis_roots=[],
            runtime_roots=[],
            output=tmp_path / "result.zip",
            include_checkpoints=False,
        )
