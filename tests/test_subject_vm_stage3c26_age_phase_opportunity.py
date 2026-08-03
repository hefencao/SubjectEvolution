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
    assess_stage3c25_winner_basin,
)
from se.analysis.subject_vm_stage3c26_age_phase_opportunity import (
    STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA,
    assess_stage3c26_age_phase_opportunity,
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
def stage3c26_inputs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("stage3c26")
    rank1 = _run(root, second_port=11)
    rank2 = _run(root, second_port=5)
    stage3c23 = assess_stage3c23_dual_readout_rank(*rank1, *rank2)
    stage3c24 = assess_stage3c24_rank2_selection(*rank1, *rank2, stage3c23)
    stage3c25 = assess_stage3c25_winner_basin(*rank2, stage3c24)
    return rank2, stage3c25


def test_stage3c26_separates_boundary_forcing_age_and_opportunity(
    stage3c26_inputs,
) -> None:
    rank2, stage3c25 = stage3c26_inputs
    result = assess_stage3c26_age_phase_opportunity(*rank2, stage3c25)

    assert result["schema"] == STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA
    findings = result["cross_source_findings"]
    assert findings[
        "sixteen_source_boundary_assignments_are_forced_in_all_sources"
    ]
    assert findings[
        "age_one_has_the_highest_or_tied_multi_candidate_selection_rate_in_all_sources"
    ]
    assert findings[
        "reused_winners_are_earlier_than_single_use_and_unselected_events_in_all_sources"
    ]
    assert findings[
        "reused_winner_opportunity_normalized_rate_is_at_least_single_use_in_all_sources"
    ]

    for row in result["per_source"]:
        assert row["requested_query_count"] == 128
        assert row["no_candidate_request_count"] == 16
        assert row["assigned_query_count"] == 112
        assert row["forced_single_candidate_query_count"] == 16
        assert row["multi_candidate_assigned_query_count"] == 96
        assert row["source_boundary"][
            "all_phase_zero_events_receive_a_forced_selection"
        ]
        assert row["historical_age"][
            "age_one_rate_is_at_least_every_older_age"
        ]
        assert row["reconstructed_score_selection_mismatch_count"] == 0

    interpretation = result["diagnostic_interpretation"]
    assert interpretation[
        "source_boundary_forcing_contributes_to_phase_zero_coverage_and_reuse"
    ]
    assert interpretation[
        "recency_preference_persists_after_forced_queries_are_removed"
    ]
    assert interpretation["raw_opportunity_count_alone_fully_explains_winner_reuse"] is False
    assert result["runtime_or_checkpoint_schema_changed"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c26_rejects_stage3c25_lineage_mismatch(stage3c26_inputs) -> None:
    rank2, stage3c25 = stage3c26_inputs
    broken = deepcopy(stage3c25)
    broken["rank2_study_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="lineage mismatch"):
        assess_stage3c26_age_phase_opportunity(*rank2, broken)
