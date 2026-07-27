from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from se.cfg import load_config
from se.experiments.d2_compositional_capability import (
    BRANCHES,
    execute_compositional_capability,
)

ROOT = Path(__file__).resolve().parents[1]


def test_compositional_capability_runner_keeps_genes_and_costs_in_both_branches(
    tmp_path: Path,
) -> None:
    cfg = load_config(ROOT / "configs" / "d2i_compositional_harvest_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=2,
            metrics_period=1,
            evolution_evaluation_period=1,
            checkpoint_period=99,
            checkpoint_ticks=(),
        ),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    result = execute_compositional_capability(
        cfg,
        (101,),
        tmp_path / "result",
        backend="cpu",
        until_tick=2,
    )
    assert result["schema"] == "d2-compositional-capability-results-v1"
    assert result["plan"]["branches"] == {
        name: list(values) for name, values in BRANCHES.items()
    }
    assert result["plan"]["same_v2_genome_in_both_branches"] is True
    assert result["plan"]["coupling_structure_cost_retained_when_neutral"] is True
    pair = result["pairs"][0]
    assert set(pair["branches"]) == set(BRANCHES)
    active = pair["branches"]["composition-active"]
    neutral = pair["branches"]["coupling-neutral"]
    assert active["coupling_output_active"] is True
    assert neutral["coupling_output_active"] is False
    assert neutral["coupling_structure_cost_retained"] is True
    assert (
        neutral["interventions"]
        == ["neutralize-functional-module-coupling-output"]
    )
    assert "functional_module_mediated_signal_abs_mean" in active["final"]
    assert neutral["final"]["functional_module_mediated_signal_abs_mean"] == 0.0
    assert result["summary"]["decision_scope"] == (
        "descriptive-generative-capability-not-pass-fail-gate"
    )
    usage = result["summary"]["mechanism_usage"]
    assert usage["neutral_zero_in_every_seed"] is True
    assert usage["active_in_every_seed"] is True
