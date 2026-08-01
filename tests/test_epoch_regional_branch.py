from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.checkpointing import read_checkpoint_bundle
from se.epochs import (
    build_regional_branch,
    freeze_epoch_base,
    load_epoch_registry,
    regional_branch_plan,
)
from se.runtime.sim import Simulation


REGISTRY = Path("protocols/epochs/subject_epochs_v1.json")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _checkpoint(tmp_path: Path) -> Path:
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=2, full_checkpoint_enabled=False),
    )
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    simulation.run(until_tick=2)
    path = tmp_path / "source.sechk"
    simulation.save_full_checkpoint(path)
    return path


def _epoch_base(tmp_path: Path, checkpoint: Path) -> Path:
    qualification = tmp_path / "qualification.json"
    qualification.write_text(
        json.dumps(
            {
                "schema": "test-qualification-v1",
                "passed": True,
                "epoch_id": "epoch-1-entity-subject-prototype",
                "contract_id": "interest-feedback-network-qualification-v1",
                "source_checkpoint_sha256": _sha(checkpoint),
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "epoch_base"
    freeze_epoch_base(
        registry_path=REGISTRY,
        epoch_id="epoch-1-entity-subject-prototype",
        checkpoint_path=checkpoint,
        qualification_path=qualification,
        output_dir=output,
    )
    return output


def test_epoch_registry_declares_subject_milestones() -> None:
    registry = load_epoch_registry(REGISTRY)
    epochs = {entry["epoch_id"]: entry for entry in registry["epochs"]}
    assert (
        epochs["epoch-1-entity-subject-prototype"]["entry_contract"]["contract_id"]
        == "interest-feedback-network-qualification-v1"
    )
    assert (
        epochs["epoch-2-group-subject-prototype"]["entry_contract"]["contract_id"]
        == "effective-group-rules-qualification-v1"
    )


def test_epoch_base_rejects_unqualified_checkpoint(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path)
    qualification = tmp_path / "qualification.json"
    qualification.write_text(
        json.dumps(
            {
                "passed": False,
                "epoch_id": "epoch-1-entity-subject-prototype",
                "contract_id": "interest-feedback-network-qualification-v1",
                "source_checkpoint_sha256": _sha(checkpoint),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="explicitly pass"):
        freeze_epoch_base(
            registry_path=REGISTRY,
            epoch_id="epoch-1-entity-subject-prototype",
            checkpoint_path=checkpoint,
            qualification_path=qualification,
            output_dir=tmp_path / "rejected",
        )


def test_regional_branch_prunes_entities_and_remains_runnable(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path)
    base = _epoch_base(tmp_path, checkpoint)
    _, source_record = read_checkpoint_bundle(checkpoint)
    source_entities = source_record["simulation"]["entities"]
    alive_rows = np.flatnonzero(source_entities.alive)
    assert alive_rows.size > 8
    # Select the half-world containing more live entities.
    left = source_entities.x[alive_rows] < source_record["config"].world.width * 0.5
    bounds = (0.0, 0.0, 0.5, 1.0) if int(left.sum()) >= int((~left).sum()) else (0.5, 0.0, 1.0, 1.0)
    plan = regional_branch_plan(epoch_base=base, bounds=bounds)
    assert 8 <= plan["selected_alive"] < plan["source_alive"]
    assert plan["branch_semantics"]["physical_grid_cropped"] is False

    output = tmp_path / "regional.sechk"
    report = build_regional_branch(
        epoch_base=base,
        bounds=bounds,
        output_checkpoint=output,
        work_dir=tmp_path / "branch_work",
        minimum_entities=8,
    )
    assert report["branch_ready"] is True
    _, branch_record = read_checkpoint_bundle(output)
    branch_entities = branch_record["simulation"]["entities"]
    assert int(branch_entities.alive.sum()) == plan["selected_alive"]
    branch_social = branch_record["simulation"]["social"]
    valid_targets = branch_social.target[branch_social.target >= 0]
    assert np.all(branch_entities.alive[valid_targets])
    assert branch_record["config"].world == source_record["config"].world
    assert any(
        item.get("schema") == "regional-active-set-branch-v1"
        for item in branch_record["checkpoint_lineage"]
    )

    resumed = Simulation.from_checkpoint(
        output,
        tmp_path / "resumed",
        backend="cpu",
        until_tick=int(branch_record["simulation"]["tick"]) + 1,
    )
    final = resumed.run(until_tick=resumed.tick + 1)
    assert final["tick"] == int(branch_record["simulation"]["tick"]) + 1


def test_epoch_zero_base_allows_null_entry_contract(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path)
    qualification = tmp_path / "epoch0_qualification.json"
    qualification.write_text(
        json.dumps(
            {
                "passed": True,
                "epoch_id": "epoch-0-ecological-carriers",
                "contract_id": None,
                "source_checkpoint_sha256": _sha(checkpoint),
            }
        ),
        encoding="utf-8",
    )
    result = freeze_epoch_base(
        registry_path=REGISTRY,
        epoch_id="epoch-0-ecological-carriers",
        checkpoint_path=checkpoint,
        qualification_path=qualification,
        output_dir=tmp_path / "epoch0",
    )
    assert result["epoch_id"] == "epoch-0-ecological-carriers"
    assert result["qualification"]["contract_id"] is None
