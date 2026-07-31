from __future__ import annotations

import json
from pathlib import Path

from se.experiments.d1_equilibrium_flux import prepare

TEMPLATE = Path("studies/d1q_integrated_equilibrium_retention_v1/frozen/d1p/source_config.json")


def test_equilibrium_flux_changes_only_shared_regeneration(tmp_path: Path) -> None:
    output = tmp_path / "equilibrium.json"
    report = prepare(template=TEMPLATE, output=output)
    before = json.loads(TEMPLATE.read_text())
    after = json.loads(output.read_text())
    assert after["environment"]["resource_regeneration"] == [0.00675] * 4
    before["environment"].pop("resource_regeneration")
    after["environment"].pop("resource_regeneration")
    assert after == before
    assert report["genetic_coordinates_changed"] == 0
    assert report["gene_specific_advantage_added"] is False
    sidecar = json.loads(Path(f"{output}.manifest.json").read_text())
    assert sidecar["schema"] == "integrated-equilibrium-resource-flux-v1"


def test_frozen_pilot_lock_authorizes_only_integrated_panel() -> None:
    lock = json.loads(
        Path(
            "studies/d1q_integrated_equilibrium_retention_v1/frozen/pilot/"
            "PILOT_QUALIFICATION_LOCK.json"
        ).read_text()
    )
    assert lock["health_ready"] is True
    assert lock["equilibrium_ready"] is True
    assert lock["authorization"] == {
        "integrated_panel_authorized": True,
        "gene_specific_adjustment_authorized": False,
        "selection_claim_authorized": False,
        "paired_experiment_authorized": False,
    }
    assert lock["cycle_aware_regime"]["assessment_span_ticks"] >= lock[
        "cycle_aware_regime"
    ]["longest_environmental_period_ticks"]


def test_frozen_pilot_lock_hashes_every_payload() -> None:
    import hashlib

    root = Path("studies/d1q_integrated_equilibrium_retention_v1/frozen/pilot")
    lock = json.loads((root / "PILOT_QUALIFICATION_LOCK.json").read_text())
    for item in lock["files"]:
        path = root / item["path"]
        assert path.stat().st_size == item["size"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
