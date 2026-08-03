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
    assess_stage3c26_age_phase_opportunity,
)
from se.analysis.subject_vm_stage3c27_token_kinematics import (
    assess_stage3c27_token_kinematics,
)
from se.analysis.subject_vm_stage3c28_recurrent_basin import (
    STAGE3C28_RECURRENT_BASIN_SCHEMA,
    assess_stage3c28_recurrent_basin,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)

CONFIG = "configs/mvp_short_subject_vm_stage3c25_winner_basin_audit.json"


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
def stage3c28_inputs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("stage3c28")
    rank1 = _run(root, second_port=11)
    rank2 = _run(root, second_port=5)
    stage3c23 = assess_stage3c23_dual_readout_rank(*rank1, *rank2)
    stage3c24 = assess_stage3c24_rank2_selection(*rank1, *rank2, stage3c23)
    stage3c25 = assess_stage3c25_winner_basin(*rank2, stage3c24)
    stage3c26 = assess_stage3c26_age_phase_opportunity(*rank2, stage3c25)
    stage3c27 = assess_stage3c27_token_kinematics(*rank2, stage3c26)
    return rank2, stage3c27


def test_stage3c28_separates_shared_codebook_from_subject_anchored_basin(
    stage3c28_inputs,
) -> None:
    rank2, stage3c27 = stage3c28_inputs
    result = assess_stage3c28_recurrent_basin(*rank2, stage3c27)

    assert result["schema"] == STAGE3C28_RECURRENT_BASIN_SCHEMA
    findings = result["cross_source_findings"]
    assert findings[
        "at_least_three_first_coordinate_values_are_shared_by_all_sources"
    ]
    assert findings[
        "same_tick_transition_agreement_has_no_consistent_large_excess_over_cross_tick_baseline"
    ]
    assert findings["second_coordinate_is_subject_anchored_in_all_sources"]
    assert findings[
        "winner_same_first_state_is_enriched_over_candidate_availability_in_all_sources"
    ]
    assert findings[
        "different_first_state_candidates_remain_available_for_at_least_85_percent_of_queries_in_all_sources"
    ]
    assert findings[
        "same_state_winner_is_nearest_second_coordinate_within_that_state_in_all_sources"
    ]
    assert findings["no_selected_winner_is_an_exact_full_visible_vector_repeat"]

    for row in result["per_source"]:
        assert row["requested_query_count"] == 128
        assert row["assigned_query_count"] == 112
        assert row["reconstructed_score_selection_mismatch_count"] == 0
        assert (
            row["subject_anchored_second_coordinate"]["intraclass_correlation"]
            >= 0.99
        )
        basin = row["recurrent_geometric_basin"]
        assert basin["winner_same_first_coordinate_fraction"] > basin[
            "same_first_coordinate_candidate_fraction"
        ]
        assert basin[
            "same_first_winner_is_nearest_second_within_state_fraction"
        ] == pytest.approx(1.0)
        assert basin["exact_full_visible_vector_winner_repeat_count"] == 0

    interpretation = result["diagnostic_interpretation"]
    assert interpretation[
        "shared_discrete_codebook_is_globally_synchronized_sampling_phase"
    ] is False
    assert interpretation["cross_subject_phase_synchrony_is_supported"] is False
    assert interpretation["second_coordinate_is_a_slow_subject_specific_anchor"]
    assert interpretation[
        "winner_reuse_is_consistent_with_within_subject_recurrent_geometric_basins"
    ]
    assert interpretation["winner_reuse_is_explained_by_exact_token_duplication"] is False
    assert result["runtime_or_checkpoint_schema_changed"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c28_rejects_stage3c27_lineage_mismatch(stage3c28_inputs) -> None:
    rank2, stage3c27 = stage3c28_inputs
    broken = deepcopy(stage3c27)
    broken["rank2_study_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="lineage mismatch"):
        assess_stage3c28_recurrent_basin(*rank2, broken)
