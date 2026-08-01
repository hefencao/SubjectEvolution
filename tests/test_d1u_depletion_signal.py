from __future__ import annotations

import json
from pathlib import Path

from se.analysis.depletion_signal_debug import contrast
from se.experiments.d1_depletion_signal_environment import prepare

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/d1u_depletion_pressure_terrain_signal_v1"


def test_d1u_prepare_changes_only_physical_signal_semantics(tmp_path: Path) -> None:
    output = tmp_path / "source_config.json"
    report = prepare(
        template=STUDY / "frozen/base/source_config.json",
        output=output,
        ticks=600,
    )
    assert report["genetic_coordinates_changed"] == 0
    assert report["resource_geometry_or_mean_flux_changed"] is False
    assert report["movement_load_formula_changed"] is False
    assert report["terrain_movement_formula_changed"] is False
    config = json.loads(output.read_text(encoding="utf-8"))
    assert config["entities"]["resource_contest_schema"] == (
        "rival-harvest-depletion-pressure-v2"
    )
    assert config["entities"]["resource_contest_energy_cost_per_pressure"] == 0.0
    assert config["entities"]["resource_contest_integrity_damage_per_pressure"] == 0.0
    assert config["information"]["resource_signal_observation_schema"] == (
        "post-harvest-current-v2"
    )
    assert config["environment"]["signal_propagation_schema"] == (
        "terrain-resisted-diffusion-v1"
    )


def test_frozen_d1t_backend_results_are_same_seed_config_but_not_same_claim() -> None:
    cpu = json.loads((STUDY / "frozen/cpu/mechanism_probe.json").read_text())
    accelerated = json.loads(
        (STUDY / "frozen/accelerated/mechanism_probe.json").read_text()
    )
    cpu_manifest = json.loads((STUDY / "frozen/cpu/run_manifest.json").read_text())
    accelerated_manifest = json.loads(
        (STUDY / "frozen/accelerated/run_manifest.json").read_text()
    )
    assert cpu_manifest["seed"] == accelerated_manifest["seed"] == 101011
    assert cpu_manifest["config_sha256"] == accelerated_manifest["config_sha256"]
    assert cpu["probe_mechanism_ready"] is True
    assert accelerated["probe_mechanism_ready"] is False


def test_backend_contrast_never_claims_scientific_parity(tmp_path: Path) -> None:
    cpu = tmp_path / "cpu.json"
    accelerated = tmp_path / "accelerated.json"
    cpu.write_text(json.dumps({"semantics_ready": True, "runs": [{"seed": 1, "config_sha256": "x", "execution_backend": "cpu", "alive": 10, "harvest_contest_events": 2}]}))
    accelerated.write_text(json.dumps({"semantics_ready": True, "runs": [{"seed": 1, "config_sha256": "x", "execution_backend": "gpu", "alive": 12, "harvest_contest_events": 3}]}))
    report = contrast(cpu=cpu, accelerated=accelerated, output=tmp_path / "out.json")
    assert report["both_semantics_ready"] is True
    assert report["backend_parity_claim"] is False
    assert report["authorization"]["formal_scientific_equivalence"] is False


def test_d1u_workflow_has_debug_contrast_but_no_formal_or_gene_steps() -> None:
    text = (STUDY / "workflow.toml").read_text(encoding="utf-8")
    assert "probe-cpu" in text
    assert "probe-accelerated" in text
    assert "backend-contrast" in text
    assert "gene-persistence" not in text
    assert "paired" not in text
    assert "structured-panel" not in text
