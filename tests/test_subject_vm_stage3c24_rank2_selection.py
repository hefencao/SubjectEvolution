from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from se.analysis.subject_vm_stage3c23_dual_readout_rank import (
    assess_stage3c23_dual_readout_rank,
)
from se.analysis.subject_vm_stage3c24_rank2_selection import (
    STAGE3C24_RANK2_SELECTION_SCHEMA,
    assess_stage3c24_rank2_selection,
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
def stage3c24_inputs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("stage3c24")
    rank1 = _run(root, second_port=11)
    # The compact three-source test screen selects port 5; the frozen nine-source
    # workflow selects port 7. Stage 3C-24 follows the Stage 3C-23 lineage.
    rank2 = _run(root, second_port=5)
    stage3c23 = assess_stage3c23_dual_readout_rank(*rank1, *rank2)
    return rank1, rank2, stage3c23


def test_stage3c24_separates_score_ties_from_identity_coverage(
    stage3c24_inputs,
) -> None:
    rank1, rank2, stage3c23 = stage3c24_inputs
    result = assess_stage3c24_rank2_selection(*rank1, *rank2, stage3c23)

    assert result["schema"] == STAGE3C24_RANK2_SELECTION_SCHEMA
    isolation = result["isolation_contract"]
    assert isolation["same_candidate_opportunity_in_all_sources"]
    assert isolation["stored_selections_and_scores_exactly_reconstructed"]

    rank1_rows = result["rank1_duplicate_coordinate"]["per_source"]
    rank2_rows = result["rank2_selected_coordinate"]["per_source"]
    assert [len(row["eligible_event_ids"]) for row in rank1_rows] == [112, 112, 112]
    assert [len(row["eligible_event_ids"]) for row in rank2_rows] == [112, 112, 112]
    assert all(
        row["score_margin"]["exact_best_tie_query_count"] > 0
        for row in rank1_rows
    )
    assert all(
        row["score_margin"]["exact_best_tie_query_count"] == 0
        for row in rank2_rows
    )
    assert all(
        row["score_margin"]["best_second_score_margin"]["minimum"] > 0.0
        for row in rank2_rows
    )

    comparison = result["comparison"]
    assert comparison["candidate_opportunity_equal_in_all_sources"]
    assert comparison["rank2_selected_set_is_strict_subset_in_all_sources"]
    assert comparison["rank2_adds_any_new_selected_event_identity"] is False
    assert comparison["rank2_reduces_unique_identity_coverage_in_all_sources"]
    assert comparison["rank2_increases_selection_gini_in_all_sources"]
    assert comparison[
        "rank2_reduces_inverse_simpson_effective_coverage_in_all_sources"
    ]
    assert comparison["rank2_eliminates_exact_best_ties_in_all_sources"]
    assert result["diagnostic_interpretation"][
        "rank_two_increases_selected_event_identity_diversity"
    ] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c24_rejects_stage3c23_lineage_mismatch(stage3c24_inputs) -> None:
    rank1, rank2, stage3c23 = stage3c24_inputs
    broken = deepcopy(stage3c23)
    broken["rank2_study_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="lineage mismatch"):
        assess_stage3c24_rank2_selection(*rank1, *rank2, broken)
