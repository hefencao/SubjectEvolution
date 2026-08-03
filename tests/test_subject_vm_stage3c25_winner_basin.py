from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from se.analysis.subject_vm_stage3c23_dual_readout_rank import (
    assess_stage3c23_dual_readout_rank,
)
from se.analysis.subject_vm_stage3c24_rank2_selection import (
    assess_stage3c24_rank2_selection,
)
from se.analysis.subject_vm_stage3c25_winner_basin import (
    STAGE3C25_WINNER_BASIN_SCHEMA,
    assess_stage3c25_winner_basin,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)

CONFIG = "configs/mvp_short_subject_vm_stage3c23_dual_readout_rank_study.json"


def _run(root: Path, *, second_port: int):
    report = run_short_paired_study(
        CONFIG,
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=8,
            bootstrap_subjects=16,
            backend="cpu",
            rollback_after_ticks=3,
            bootstrap_target_family="edge_forward_gate",
            bootstrap_edge_carrier_enabled=True,
            bootstrap_readout_input_port=11,
            bootstrap_second_readout_input_port=second_port,
            association_tie_break="latest",
            association_candidate_limit=1,
        ),
        output_dir=root / f"port_{second_port}",
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    return report, component, diagnostics


@pytest.fixture(scope="module")
def stage3c25_inputs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("stage3c25")
    rank1 = _run(root, second_port=11)
    rank2 = _run(root, second_port=5)
    stage3c23 = assess_stage3c23_dual_readout_rank(*rank1, *rank2)
    stage3c24 = assess_stage3c24_rank2_selection(
        *rank1, *rank2, stage3c23
    )
    return rank2, stage3c24


def test_stage3c25_separates_margin_fragility_from_winner_basin_reuse(
    stage3c25_inputs,
) -> None:
    rank2, stage3c24 = stage3c25_inputs
    result = assess_stage3c25_winner_basin(*rank2, stage3c24)

    assert result["schema"] == STAGE3C25_WINNER_BASIN_SCHEMA
    assert result["isolation_contract"][
        "stored_winner_ids_and_scores_exactly_reconstructed"
    ]
    findings = result["cross_source_findings"]
    assert findings[
        "reused_winner_normalized_margin_median_exceeds_single_use_in_all_sources"
    ]
    assert findings[
        "reused_winner_fraction_at_or_below_1e6_is_lower_in_all_sources"
    ]
    assert findings[
        "all_reused_winners_span_distinct_exact_query_vectors_in_all_sources"
    ]
    assert findings[
        "reused_winners_have_more_eligible_opportunities_in_all_sources"
    ]

    for row in result["per_source"]:
        assert row["assigned_query_count"] == 112
        assert row["multi_candidate_assigned_query_count"] == 96
        assert row["query_geometry"][
            "all_assigned_queries_have_distinct_exact_visible_vectors"
        ]
        assert row["winner_reuse"]["reused_winner_count"] > 0
        assert row["winner_reuse"][
            "all_reused_winners_span_distinct_visible_query_vectors"
        ]

    interpretation = result["diagnostic_interpretation"]
    assert interpretation[
        "winner_reuse_is_concentrated_in_the_smallest_normalized_margins"
    ] is False
    assert interpretation[
        "winner_reuse_is_caused_by_exact_duplicate_query_vectors"
    ] is False
    assert interpretation[
        "winner_reuse_is_consistent_with_opportunity_conditioned_deterministic_candidate_basins"
    ]
    assert result["runtime_or_checkpoint_schema_changed"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c25_rejects_stage3c24_lineage_mismatch(stage3c25_inputs) -> None:
    rank2, stage3c24 = stage3c25_inputs
    broken = deepcopy(stage3c24)
    broken["rank2_study_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="lineage mismatch"):
        assess_stage3c25_winner_basin(*rank2, broken)
