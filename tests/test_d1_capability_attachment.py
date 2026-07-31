from __future__ import annotations

import json
from pathlib import Path

import pytest

from se.cfg import load_config
from se.experiments.d1_capability_attachment import build_config
from se.runtime.reproduction import inherited_reproduction_investment_enabled

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies" / "d1o_budgeted_offspring_investment_v1"
TEMPLATE = (
    ROOT
    / "studies"
    / "d1n_staged_turnover_qualification_v1"
    / "frozen"
    / "qualification"
    / "source_config.json"
)
BUDGET = STUDY / "frozen" / "budget" / "capability_budget.json"
CAPABILITY = STUDY / "protocol" / "capability.json"


def test_budgeted_attachment_changes_only_reproduction_expression(tmp_path: Path) -> None:
    output = tmp_path / "source_config.json"
    manifest = build_config(
        template=TEMPLATE,
        budget_path=BUDGET,
        capability_path=CAPABILITY,
        output=output,
    )
    cfg = load_config(output)
    assert inherited_reproduction_investment_enabled(cfg)
    assert cfg.entities.reproduction_investment_levels == (0.75, 0.85, 0.95, 1.05)
    assert sum(cfg.entities.reproduction_investment_levels) / 4 == pytest.approx(0.9)
    assert cfg.entities.maintenance_cost == pytest.approx(0.01)
    assert cfg.environment.resource_regeneration == pytest.approx((0.027,) * 4)
    assert cfg.environment.harvest_channel_multipliers == pytest.approx((1.3,) * 4)
    assert manifest["physical_substrate_unchanged"]
    assert set(manifest["changed_paths"]) == {
        "entities.reproduction_schema",
        "entities.reproduction_investment_levels",
    }
    assert manifest["cost_and_maturation_validation"]["recurring_cost_per_entity_tick"] == 0.0
    assert Path(f"{output}.manifest.json").is_file()
    assert not output.with_suffix(".manifest.json").exists()


def test_attachment_rejects_population_mean_debit_shift(tmp_path: Path) -> None:
    spec = json.loads(CAPABILITY.read_text())
    spec["offspring_investment_levels"] = [0.8, 0.9, 1.0, 1.1]
    changed = tmp_path / "capability.json"
    changed.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="mean endowment"):
        build_config(
            template=TEMPLATE,
            budget_path=BUDGET,
            capability_path=changed,
            output=tmp_path / "source_config.json",
        )


def test_d1o_workflow_exposes_only_source_qualification_steps() -> None:
    workflow = (STUDY / "workflow.toml").read_text(encoding="utf-8")
    assert "94101,94102,94103" in workflow
    assert "[steps.paired-plan]" not in workflow
    assert "[steps.paired-run]" not in workflow
    assert "se-d1-reproduction-investment" not in workflow
    assert "source_config.json.manifest.json" not in workflow
    assert '"{generated_config}.manifest.json"' in workflow
