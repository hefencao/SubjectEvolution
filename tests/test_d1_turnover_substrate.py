from __future__ import annotations

import json
from pathlib import Path

from se.experiments.d1_turnover_substrate import build_config


def test_turnover_config_uses_full_filename_manifest_sidecar(tmp_path: Path) -> None:
    template = Path("studies/d1l_turnover_substrate_v1/protocol/source_template.json")
    output = tmp_path / "source_config.json"
    legacy = tmp_path / "source_config.manifest.json"
    legacy.write_text("stale\n", encoding="utf-8")
    manifest = build_config(
        template,
        output=output,
        initial_entities=160,
        initial_energy=2.4,
        maintenance_cost=0.015,
        harvest_multiplier=1.0,
        resource_regeneration=0.018,
        reproduction_threshold=2.0,
        reproduction_cost=0.6,
        target_tick=240,
        metrics_period=30,
        checkpoint_period=120,
    )
    sidecar = tmp_path / "source_config.json.manifest.json"
    assert sidecar.is_file()
    assert not legacy.exists()
    assert manifest["manifest_path"] == str(sidecar)
    assert json.loads(sidecar.read_text(encoding="utf-8"))["config_sha256"] == manifest["config_sha256"]
