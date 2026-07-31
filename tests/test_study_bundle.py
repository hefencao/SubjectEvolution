from __future__ import annotations

import json
from pathlib import Path
import subprocess
import shutil
import zipfile

import pytest

from se.analysis.study_bundle import (
    export_study_result,
    freeze_legacy_decision,
    import_study_result,
    migrate_runtime_artifacts,
    migrate_stage_layout,
    verify_study,
)
from se.cfg import load_config
from se.workspace import sha256_file


ROOT = Path(__file__).resolve().parents[1]
D3T = ROOT / "studies/d3t_spatial_processing_conversion_v1"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_frozen_d3t_chain_is_portable_and_complete() -> None:
    report = verify_study(D3T / "study.json", workspace=ROOT)
    assert report["passed"] is True
    assert report["frozen_stage_count"] == 3
    assert report["latest_stage"] == "confirmation"

    screen = json.loads((D3T / "frozen/screen/stage.lock.json").read_text())
    replication = json.loads(
        (D3T / "frozen/replication/stage.lock.json").read_text()
    )
    confirmation = json.loads(
        (D3T / "frozen/confirmation/stage.lock.json").read_text()
    )
    assert screen["source_binding"]["mode"] == "paired-plan-source-hash-binding"
    assert replication["source_binding"]["mode"] == "exact-candidate"
    assert confirmation["source_binding"]["mode"] == "exact-candidate"
    assert confirmation["decision"] == "confirmed-acute"
    assert confirmation["terminal"] is True
    for stage in (screen, replication, confirmation):
        assert stage["schema"] == "se-study-stage-freeze-v2"
        assert all("original_path" not in ref for ref in stage["evidence"].values())
        assert all(
            str(ref["path"]).startswith("runs/base/")
            and not Path(str(ref["path"])).is_absolute()
            for ref in stage["external_runtime_artifacts"]
        )




def _copy_d3t_workspace(tmp_path: Path) -> Path:
    target = tmp_path / "studies/d3t_spatial_processing_conversion_v1"
    shutil.copytree(D3T, target)
    decision_target = tmp_path / "protocols/decisions"
    decision_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "protocols/decisions", decision_target)
    return target


def test_result_bundle_export_is_deterministic_and_self_describing(tmp_path: Path) -> None:
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    one = export_study_result(D3T / "study.json", output=first, workspace=ROOT)
    two = export_study_result(D3T / "study.json", output=second, workspace=ROOT)
    assert one["sha256"] == two["sha256"]
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as bundle:
        names = set(bundle.namelist())
        manifest = json.loads(bundle.read("bundle.json"))
    assert "study.json" in names
    assert "DESIGN.md" in names
    assert "RUN_CHAIN.md" in names
    assert "commands/20_confirmation_source_plan.sh" in names
    assert "protocol/candidate.json" in names
    assert "frozen/confirmation/stage.lock.json" in names
    assert manifest["schema"] == "se-study-result-bundle-v1"
    assert manifest["latest_stage"] == "confirmation"
    assert manifest["design_and_runbook_included"] is True
    assert manifest["sufficient_for_decision_import"] is True
    assert manifest["sufficient_for_checkpoint_replay"] is False


def test_result_bundle_import_appends_stage_and_rebuilds_summary(tmp_path: Path) -> None:
    target = _copy_d3t_workspace(tmp_path)
    shutil.rmtree(target / "frozen/confirmation")
    from se.analysis.study_bundle import rebuild_chain_lock

    rebuild_chain_lock(target / "study.json", workspace=tmp_path)
    stale_summary = (target / "RUN_CHAIN.md").read_text(encoding="utf-8")
    assert "| confirmation |" not in stale_summary

    archive = tmp_path / "result.zip"
    export_study_result(D3T / "study.json", output=archive, workspace=ROOT)
    before_check = (target / "RUN_CHAIN.md").read_bytes()
    check = import_study_result(
        target / "study.json", bundle=archive, workspace=tmp_path, check_only=True
    )
    assert check["schema"] == "se-study-result-import-check-v1"
    assert check["would_modify_study"] is True
    assert (target / "RUN_CHAIN.md").read_bytes() == before_check

    report = import_study_result(
        target / "study.json", bundle=archive, workspace=tmp_path
    )
    assert report["previous_stage_count"] == 2
    assert report["imported_stage_count"] == 3
    assert report["latest_stage"] == "confirmation"
    assert report["sufficient_for_checkpoint_replay"] is False
    assert "| confirmation |" in (target / "RUN_CHAIN.md").read_text(encoding="utf-8")
    assert verify_study(target / "study.json", workspace=tmp_path)["passed"] is True


def test_legacy_frozen_only_bundle_is_accepted_against_matching_protocols(
    tmp_path: Path,
) -> None:
    target = _copy_d3t_workspace(tmp_path)
    report = import_study_result(
        target / "study.json",
        bundle=D3T / "frozen",
        workspace=tmp_path,
        check_only=True,
    )
    assert report["legacy_frozen_only"] is True
    assert report["latest_stage"] == "confirmation"
    assert report["would_modify_study"] is False


def test_result_bundle_import_rejects_existing_stage_rewrite_atomically(tmp_path: Path) -> None:
    target = _copy_d3t_workspace(tmp_path)
    before_frozen = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in (target / "frozen").rglob("*")
        if path.is_file()
    }
    before_summary = (target / "RUN_CHAIN.md").read_bytes()
    bundle = tmp_path / "bundle"
    shutil.copytree(D3T / "frozen", bundle)
    lock_path = bundle / "screen/stage.lock.json"
    lock = json.loads(lock_path.read_text())
    lock["decision"] = "stop"
    _write_json(lock_path, lock)
    with pytest.raises(ValueError, match="rewrite or remove existing frozen stage"):
        import_study_result(target / "study.json", bundle=bundle, workspace=tmp_path)
    after_frozen = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in (target / "frozen").rglob("*")
        if path.is_file()
    }
    assert after_frozen == before_frozen
    assert (target / "RUN_CHAIN.md").read_bytes() == before_summary


def test_result_bundle_import_rejects_zip_traversal(tmp_path: Path) -> None:
    target = _copy_d3t_workspace(tmp_path)
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.json", "{}")
    with pytest.raises(ValueError, match="unsafe study result archive member"):
        import_study_result(target / "study.json", bundle=archive, workspace=tmp_path)
    assert not (tmp_path.parent / "outside.json").exists()


def test_legacy_decision_survives_unrelated_baseline_append(tmp_path: Path) -> None:
    source_candidate = ROOT / "studies/d3o_resource_affinity_v1/protocol/candidate.json"
    candidate_path = tmp_path / "studies/example/protocol/candidate.json"
    candidate_path.parent.mkdir(parents=True)
    shutil.copy2(source_candidate, candidate_path)
    canonical = json.loads(
        (ROOT / "protocols/decisions/exploration_candidate_ledger.json").read_text()
    )
    target_entry = next(
        entry
        for entry in canonical["entries"]
        if entry["candidate_id"] == "resource-affinity-acute-effect"
    )
    unrelated = next(
        entry
        for entry in canonical["entries"]
        if entry["candidate_id"] == "elastic-capacity-use-acute-effect-v1"
    )
    ledger_path = tmp_path / "protocols/decisions/exploration_candidate_ledger.json"
    _write_json(ledger_path, {"schema": canonical["schema"], "entries": [target_entry]})
    study_path = tmp_path / "studies/example/study.json"
    _write_json(
        study_path,
        {
            "schema": "se-study-bundle-v1",
            "study_id": "example",
            "candidate_id": "resource-affinity-acute-effect",
            "summary": "legacy result",
            "candidate_spec": {
                "path": "studies/example/protocol/candidate.json",
                "signature_sha256": target_entry["candidate_signature_sha256"],
                "content_sha256": sha256_file(candidate_path),
            },
        },
    )
    freeze_legacy_decision(
        study_path=study_path,
        ledger_path=ledger_path,
        stage="screen",
        workspace=tmp_path,
    )
    assert verify_study(study_path, workspace=tmp_path)["passed"] is True

    _write_json(
        ledger_path,
        {"schema": canonical["schema"], "entries": [target_entry, unrelated]},
    )
    assert verify_study(study_path, workspace=tmp_path)["passed"] is True


def test_verify_is_read_only_for_tampered_chain(tmp_path: Path) -> None:
    source = ROOT / "studies/d3o_resource_affinity_v1"
    target = tmp_path / "studies/d3o_resource_affinity_v1"
    shutil.copytree(source, target)
    protocols = tmp_path / "protocols/decisions"
    protocols.mkdir(parents=True)
    shutil.copy2(
        ROOT / "protocols/decisions/exploration_candidate_ledger.json",
        protocols / "exploration_candidate_ledger.json",
    )
    chain_path = target / "frozen/chain.lock.json"
    chain = json.loads(chain_path.read_text())
    chain["latest_stage"] = "confirmation"
    _write_json(chain_path, chain)

    tampered_bytes = chain_path.read_bytes()
    run_chain_path = target / "RUN_CHAIN.md"
    run_chain_bytes = run_chain_path.read_bytes()

    report = verify_study(target / "study.json", workspace=tmp_path)
    assert report["passed"] is False
    assert "frozen chain lock does not match stage evidence" in report["failures"]
    assert chain_path.read_bytes() == tampered_bytes
    assert run_chain_path.read_bytes() == run_chain_bytes
    assert verify_study(target / "study.json", workspace=tmp_path)["passed"] is False
    assert chain_path.read_bytes() == tampered_bytes

def test_stage_layout_migration_splits_runtime_and_analysis(tmp_path: Path) -> None:
    study_dir = tmp_path / "studies/example"
    _write_json(
        study_dir / "study.json",
        {
            "schema": "se-study-bundle-v1",
            "study_id": "example",
            "candidate_id": "example-candidate",
            "workspace_layout": {
                "source_runs": "runs/base/example/<stage>",
                "intervention_runs": "runs/interventions/example/<stage>",
                "analyses": "analyses/example/<stage>",
            },
        },
    )
    source = tmp_path / "analyses/legacy_source"
    paired = tmp_path / "analyses/legacy_paired"
    _write_json(source / "exploration_plan.json", {"schema": "source-plan"})
    _write_json(source / "multi_seed_plan.json", {"schema": "multi-plan"})
    _write_json(source / "long_run_analysis.json", {"schema": "analysis"})
    checkpoint = source / "seed_1/checkpoint_00000010.sechk"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    (checkpoint.parent / "progress.jsonl").write_text("{}\n", encoding="utf-8")

    evidence_files = {
        "paired_plan": paired / "paired_exploration_plan.json",
        "results": paired / "paired_exploration_results.json",
        "assessment": paired / "paired_exploration_assessment.json",
        "decision": paired / "candidate_decision.json",
    }
    for role, path in evidence_files.items():
        _write_json(path, {"schema": role})
    branch = paired / "seed_1/intervention/final_summary.json"
    _write_json(branch, {"tick": 20})
    _write_json(paired / "paired_exploration_results.md.json", {"derived": True})

    evidence = {
        "source_plan": {
            "frozen_path": "source_plan.json",
            "sha256": sha256_file(source / "exploration_plan.json"),
        }
    }
    evidence.update(
        {
            role: {"frozen_path": f"{role}.json", "sha256": sha256_file(path)}
            for role, path in evidence_files.items()
        }
    )
    _write_json(
        study_dir / "frozen/screen/stage.lock.json",
        {
            "schema": "se-study-stage-freeze-v2",
            "study_id": "example",
            "stage": "screen",
            "evidence": evidence,
            "external_runtime_artifacts": [
                {
                    "role": "source-checkpoint",
                    "seed": 1,
                    "tick": 10,
                    "path": "runs/base/example/screen/seed_1/checkpoint_00000010.sechk",
                    "sha256": sha256_file(checkpoint),
                }
            ],
        },
    )

    report = migrate_stage_layout(
        study_dir / "study.json",
        stage="screen",
        legacy_source_root=source,
        legacy_paired_root=paired,
        workspace=tmp_path,
    )
    assert report["validated_checkpoint_count"] == 1
    assert (tmp_path / "runs/base/example/screen/seed_1/progress.jsonl").is_file()
    assert (tmp_path / "runs/interventions/example/screen/seed_1/intervention/final_summary.json").is_file()
    assert (tmp_path / "analyses/example/screen/source/long_run_analysis.json").is_file()
    assert (tmp_path / "analyses/example/screen/paired_exploration_results.json").is_file()
    assert source.is_dir() and paired.is_dir()


def test_all_historical_studies_have_explicit_evidence_completeness() -> None:
    study_paths = sorted((ROOT / "studies").glob("*/study.json"))
    assert len(study_paths) == 6
    for study_path in study_paths:
        report = verify_study(study_path, workspace=ROOT)
        assert report["passed"] is True, (study_path, report["failures"])
        study = json.loads(study_path.read_text(encoding="utf-8"))
        assert study["candidate_spec"]["content_sha256"]
        if study_path.parent != D3T:
            lock = study_path.parent / "frozen/legacy/screen.lock.json"
            payload = json.loads(lock.read_text(encoding="utf-8"))
            assert payload["evidence_completeness"] == "legacy-decision-only"
            assert payload["missing_evidence_was_reconstructed"] is False
            assert payload["unavailable_evidence"]
            assert not (study_path.parent / "commands").exists()

def test_runtime_migration_is_content_addressed(tmp_path: Path) -> None:
    study_dir = tmp_path / "studies/example"
    _write_json(
        study_dir / "study.json",
        {
            "schema": "se-study-bundle-v1",
            "study_id": "example",
            "candidate_id": "example-candidate",
        },
    )
    legacy = tmp_path / "legacy/seed_1/checkpoint_00000010.sechk"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"checkpoint-one")
    expected_sha = sha256_file(legacy)
    _write_json(
        study_dir / "frozen/screen/stage.lock.json",
        {
            "schema": "se-study-stage-freeze-v2",
            "study_id": "example",
            "stage": "screen",
            "external_runtime_artifacts": [
                {
                    "role": "source-checkpoint",
                    "seed": 1,
                    "tick": 10,
                    "path": "runs/base/example/screen/seed_1/checkpoint_00000010.sechk",
                    "legacy_location_hint": "analyses/example/seed_1/checkpoint_00000010.sechk",
                    "sha256": expected_sha,
                }
            ],
        },
    )

    report = migrate_runtime_artifacts(
        study_dir / "study.json",
        search_roots=[tmp_path / "legacy"],
        workspace=tmp_path,
        materialize="copy",
    )
    target = tmp_path / "runs/base/example/screen/seed_1/checkpoint_00000010.sechk"
    assert report["all_verified"] is True
    assert target.read_bytes() == b"checkpoint-one"
    assert report["artifacts"][0]["path"] == target.relative_to(tmp_path).as_posix()


def test_runtime_migration_aborts_before_partial_write(tmp_path: Path) -> None:
    study_dir = tmp_path / "studies/example"
    _write_json(
        study_dir / "study.json",
        {
            "schema": "se-study-bundle-v1",
            "study_id": "example",
            "candidate_id": "example-candidate",
        },
    )
    legacy = tmp_path / "legacy/seed_1/checkpoint_00000010.sechk"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"checkpoint-one")
    _write_json(
        study_dir / "frozen/screen/stage.lock.json",
        {
            "schema": "se-study-stage-freeze-v2",
            "study_id": "example",
            "stage": "screen",
            "external_runtime_artifacts": [
                {
                    "role": "source-checkpoint",
                    "seed": 1,
                    "tick": 10,
                    "path": "runs/base/example/screen/seed_1/checkpoint_00000010.sechk",
                    "sha256": sha256_file(legacy),
                },
                {
                    "role": "source-checkpoint",
                    "seed": 2,
                    "tick": 10,
                    "path": "runs/base/example/screen/seed_2/checkpoint_00000010.sechk",
                    "sha256": "0" * 64,
                },
            ],
        },
    )

    with pytest.raises(ValueError, match="migration is incomplete"):
        migrate_runtime_artifacts(
            study_dir / "study.json",
            search_roots=[tmp_path / "legacy"],
            workspace=tmp_path,
        )
    assert not (tmp_path / "runs").exists()


def test_workspace_layout_and_runbook_boundaries() -> None:
    assert not (ROOT / "protocols/candidates").exists()
    assert not (ROOT / "configs/mvp_d3n_exploration_screen.json").exists()
    assert (D3T / "protocol/candidate.json").is_file()
    assert (D3T / "protocol/source_screen.json").is_file()
    assert (ROOT / "runs/README.md").is_file()
    assert (ROOT / "analyses/README.md").is_file()
    assert (ROOT / "state/README.md").is_file()

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".vscode/" in gitignore
    assert "runs/*" in gitignore
    assert "analyses/*" in gitignore

    for readme in ROOT.rglob("README.md"):
        text = readme.read_text(encoding="utf-8")
        assert "```bash" not in text, f"commands must not be duplicated in {readme}"

    command_files = sorted((D3T / "commands").glob("*.sh"))
    assert command_files
    assert [path.name[:2] for path in command_files] == sorted(
        path.name[:2] for path in command_files
    )
    assert all(
        path.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
        for path in command_files
    )
    for path in command_files:
        subprocess.run(["bash", "-n", str(path)], check=True)


def test_study_source_configs_are_valid_and_protocol_locked() -> None:
    configs = [
        D3T / "protocol/source_screen.json",
        D3T / "protocol/source_replication.json",
        D3T / "protocol/source_confirmation.json",
        D3T / "protocol/scale_robustness.json",
    ]
    loaded = [load_config(path) for path in configs]
    assert all(config.world.initial_entities > 0 for config in loaded)
    screen, replication, confirmation, robustness = loaded
    assert screen.world.width == replication.world.width == confirmation.world.width
    assert screen.run.ticks == replication.run.ticks == confirmation.run.ticks == 480
    assert robustness.world.width != replication.world.width
