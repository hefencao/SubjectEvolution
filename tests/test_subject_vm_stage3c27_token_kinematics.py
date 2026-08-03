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
    STAGE3C27_TOKEN_KINEMATICS_SCHEMA,
    assess_stage3c27_token_kinematics,
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
def stage3c27_inputs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("stage3c27")
    rank1 = _run(root, second_port=11)
    rank2 = _run(root, second_port=5)
    stage3c23 = assess_stage3c23_dual_readout_rank(*rank1, *rank2)
    stage3c24 = assess_stage3c24_rank2_selection(*rank1, *rank2, stage3c23)
    stage3c25 = assess_stage3c25_winner_basin(*rank2, stage3c24)
    stage3c26 = assess_stage3c26_age_phase_opportunity(*rank2, stage3c25)
    return rank2, stage3c26


def test_stage3c27_separates_strict_geometry_from_latest_tie_break(
    stage3c27_inputs,
) -> None:
    rank2, stage3c26 = stage3c27_inputs
    result = assess_stage3c27_token_kinematics(*rank2, stage3c26)

    assert result["schema"] == STAGE3C27_TOKEN_KINEMATICS_SCHEMA
    findings = result["cross_source_findings"]
    assert findings[
        "sixteen_source_boundary_assignments_are_forced_in_all_sources"
    ]
    assert findings[
        "strict_geometry_accounts_for_at_least_99_percent_of_multi_candidate_age_one_selections"
    ]
    assert findings[
        "exact_latest_tie_break_contributes_less_than_one_percent_of_multi_candidate_queries"
    ]
    assert findings[
        "strict_age_one_local_step_median_is_lower_than_older_geometry_in_all_sources"
    ]
    assert findings[
        "unchanged_first_readout_coordinate_predicts_age_one_selection_at_least_90_percent_in_all_sources"
    ]
    assert findings[
        "changed_first_readout_coordinate_predicts_older_selection_at_least_80_percent_in_all_sources"
    ]

    for row in result["per_source"]:
        assert row["requested_query_count"] == 128
        assert row["no_candidate_request_count"] == 16
        assert row["assigned_query_count"] == 112
        assert row["forced_single_candidate_query_count"] == 16
        assert row["multi_candidate_query_count"] == 96
        assert row["reconstructed_score_selection_mismatch_count"] == 0
        assert row["kinematic_groups"][
            "older_to_strict_age_one_local_step_median_ratio"
        ] > 50.0
        assert row["all_constant_coordinates_unchanged"]

    interpretation = result["diagnostic_interpretation"]
    assert interpretation["latest_tie_break_is_the_primary_age_one_basin_driver"] is False
    assert interpretation["local_token_geometry_is_the_primary_multi_candidate_age_one_driver"]
    assert interpretation[
        "first_readout_state_persistence_and_recurrence_contribute_to_selected_age"
    ]
    assert result["runtime_or_checkpoint_schema_changed"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c27_rejects_stage3c26_lineage_mismatch(stage3c27_inputs) -> None:
    rank2, stage3c26 = stage3c27_inputs
    broken = deepcopy(stage3c26)
    broken["rank2_study_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="lineage mismatch"):
        assess_stage3c27_token_kinematics(*rank2, broken)
