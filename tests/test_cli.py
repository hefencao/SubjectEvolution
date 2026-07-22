from __future__ import annotations

import json
from pathlib import Path
import sys

from subject_evolution.cli import main


def test_cli_writes_the_effective_experiment_mode(monkeypatch, tmp_path) -> None:
    raw = json.loads(Path("configs/mvp_small.json").read_text(encoding="utf-8"))
    raw["run"].update(ticks=1, metrics_period=1, checkpoint_period=99)
    raw["world"].update(initial_entities=32, max_entities=48)
    source = tmp_path / "source.json"
    source.write_text(json.dumps(raw), encoding="utf-8")
    output = tmp_path / "run"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "subject-evolution",
            "--config",
            str(source),
            "--output",
            str(output),
            "--experiment-mode",
            "entertainment",
        ],
    )

    main()

    effective = json.loads((output / "config.json").read_text(encoding="utf-8"))
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    assert effective["run"]["experiment_mode"] == "entertainment"
    assert metadata["experiment_mode"] == "entertainment"
    assert metadata["scientific_validity"]["structural_evolution_provenance_valid"] is False
