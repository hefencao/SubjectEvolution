from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from se.analysis.protocol_audit import build_protocol_audit
from se.cfg import load_config
from se.experiments.d3_processing_response_panel import (
    SampleSupportRequirements,
    execute_processing_response_panel,
)

ROOT = Path(__file__).resolve().parents[1]
D3E = ROOT / "configs" / "mvp_short_d3e_spatial_processing_longrun.json"
SCALE1P5 = ROOT / "configs" / "mvp_short_d3g_spatial_processing_scale1p5_longrun.json"
SCALE2 = ROOT / "configs" / "mvp_short_d3g_spatial_processing_scale2_longrun.json"


def _small_cfg(*, ticks: int = 8):
    cfg = load_config(D3E)
    return replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=ticks,
            metrics_period=4,
            checkpoint_period=4,
            evolution_evaluation_period=4,
            full_checkpoint_enabled=False,
            long_run_diagnostics_enabled=False,
            long_run_diagnostics_schema="disabled",
            spatial_stress_diagnostics_enabled=False,
            spatial_stress_diagnostics_schema="disabled",
            subject_structure_diagnostics_enabled=False,
            subject_structure_diagnostics_schema="disabled",
            environment_atlas_diagnostics_enabled=False,
            environment_atlas_diagnostics_schema="disabled",
            environment_atlas_scales=(),
        ),
        world=replace(cfg.world, initial_entities=64, max_entities=128),
    )


def test_d3g_preregistered_checkpoint_panel_keeps_nested_sample_support(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=8)
    requirements = SampleSupportRequirements(
        minimum_alive=1,
        minimum_alive_entity_ticks=1,
        minimum_eligible_entity_ticks=1,
        minimum_resource_moves=1,
        minimum_unique_entities=1,
        minimum_effective_lineages=1.0,
        maximum_largest_lineage_fraction=1.0,
        evolutionary_minimum_births_per_initial_entity=0.0,
        evolutionary_minimum_mean_generation=0.0,
        evolutionary_minimum_max_generation=0,
    )
    payload = execute_processing_response_panel(
        cfg,
        (60001,),
        tmp_path / "panel",
        checkpoint_ticks=(2, 4),
        response_window=4,
        observation_period=2,
        backend="cpu",
        requirements=requirements,
    )
    assert payload["schema"] == "d3-processing-response-panel-results-v2"
    assert payload["panel_count"] == 2
    assert payload["completed_panel_count"] == 2
    assert payload["audit_completeness"][
        "every_predeclared_checkpoint_accounted_for"
    ]
    for panel in payload["panels"]:
        assert panel["status"] == "completed"
        assert panel["shared_checkpoint_state"]
        assert len(panel["branches"]) == 4
        for branch in panel["branches"]:
            assert branch["sample_windows"]
            assert branch["sample_support"]["alive_entity_ticks"] > 0
            assert branch["sample_support"]["unique_entities"] > 0
            assert branch["interval_ledgers"]["external_resource"]["valid"]
            recycling = branch["interval_ledgers"]["external_recycling"]
            assert recycling["valid"]
            assert max(abs(value) for value in recycling["corrected_external_residual"]) < 1.0e-8
        contrasts = panel["matched_orientation_contrasts"]
        assert contrasts["schema"] == "matched-orientation-active-neutral-contrast-v1"
        assert set(branch["branch"] for branch in panel["branches"]) == {
            "original-support",
            "reversed-support",
            "neutral-support",
            "reversed-neutral-support",
        }
    assert payload["audit_completeness"][
        "outcome_conditioned_checkpoint_selection"
    ] is False
    audit = build_protocol_audit(D3E)
    assert audit["schema"] == "structural-measurement-protocol-audit-v29"
    protocol = audit["functional_module_protocol"][
        "processing_response_sample_support_protocol"
    ]
    assert protocol["all_predeclared_checkpoints_retained"]
    assert protocol["movement_events_independent_replicates"] is False
    assert protocol["sampling_gate_feedback_to_world"] is False


def test_scale_configs_preserve_density_and_cell_resolution() -> None:
    base = load_config(D3E)
    for path in (SCALE1P5, SCALE2):
        scale = load_config(path)
        assert scale.world.width / scale.world.grid_x == base.world.width / base.world.grid_x
        assert scale.world.height / scale.world.grid_y == base.world.height / base.world.grid_y
        assert (
            scale.world.initial_entities / (scale.world.width * scale.world.height)
            == base.world.initial_entities / (base.world.width * base.world.height)
        )
        assert (
            scale.world.max_entities / (scale.world.width * scale.world.height)
            == base.world.max_entities / (base.world.width * base.world.height)
        )
