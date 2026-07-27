from __future__ import annotations

import json
from pathlib import Path
import sys

from se.cmd import multi_seed as multi_command
from se.cmd import run as run_command


ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = ROOT / "configs" / "d1b_selective_harvest_smoke.json"


def _small_config(tmp_path: Path) -> Path:
    data = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    data["run"].update(
        {
            "ticks": 4,
            "metrics_period": 2,
            "checkpoint_period": 99,
            "evolution_evaluation_period": 2,
            "subject_structure_diagnostics_enabled": False,
            "subject_structure_diagnostics_schema": "disabled",
            "environment_atlas_diagnostics_enabled": False,
            "environment_atlas_diagnostics_schema": "disabled",
            "environment_atlas_scales": [],
            "spatial_stress_diagnostics_enabled": False,
            "spatial_stress_diagnostics_schema": "disabled",
        }
    )
    data["world"].update({"initial_entities": 16, "max_entities": 24})
    path = tmp_path / "small.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_se_seed_and_exact_checkpoint_overrides(tmp_path: Path, monkeypatch) -> None:
    config = _small_config(tmp_path)
    output = tmp_path / "single"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "se",
            "--config",
            str(config),
            "--output",
            str(output),
            "--backend",
            "cpu",
            "--seed",
            "23456",
            "--checkpoint-ticks",
            "1,3",
            "--until-tick",
            "3",
        ],
    )
    run_command.main()
    resolved = json.loads((output / "resolved_config.json").read_text())
    assert resolved["run"]["seed"] == 23456
    assert resolved["run"]["checkpoint_ticks"] == [1, 3]
    assert (output / "checkpoint_00000001.sechk").is_file()
    assert (output / "checkpoint_00000003.sechk").is_file()


def test_se_multi_writes_union_of_exact_checkpoints_for_every_seed(
    tmp_path: Path, monkeypatch
) -> None:
    config = _small_config(tmp_path)
    output = tmp_path / "multi"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "se-multi",
            "--config",
            str(config),
            "--seeds",
            "101,202",
            "--output",
            str(output),
            "--backend",
            "cpu",
            "--checkpoint-ticks",
            "1,3",
            "--until-tick",
            "3",
        ],
    )
    multi_command.main()
    for seed in (101, 202):
        run = output / f"seed_{seed}"
        assert (run / "checkpoint_00000001.sechk").is_file()
        assert (run / "checkpoint_00000003.sechk").is_file()
        resolved = json.loads((run / "resolved_config.json").read_text())
        assert resolved["run"]["seed"] == seed
        assert resolved["run"]["checkpoint_ticks"] == [1, 3]
