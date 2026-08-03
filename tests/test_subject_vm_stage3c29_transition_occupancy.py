from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from se.analysis.subject_vm_stage3c22_historical_selection import _canonical_sha256
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
    assess_stage3c28_recurrent_basin,
)
from se.analysis.subject_vm_stage3c29_transition_occupancy import (
    STAGE3C29_TRANSITION_OCCUPANCY_SCHEMA,
    assess_stage3c29_transition_occupancy,
)
from se.analysis.subject_vm_stage3c30_weight_robustness import (
    SECOND_COORDINATE_WEIGHT_PANEL,
    STAGE3C30_WEIGHT_ROBUSTNESS_SCHEMA,
    assess_stage3c30_weight_robustness,
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
def stage3c29_inputs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("stage3c29")
    rank1 = _run(root, second_port=11)
    rank2 = _run(root, second_port=5)
    stage3c23 = assess_stage3c23_dual_readout_rank(*rank1, *rank2)
    stage3c24 = assess_stage3c24_rank2_selection(*rank1, *rank2, stage3c23)
    stage3c25 = assess_stage3c25_winner_basin(*rank2, stage3c24)
    stage3c26 = assess_stage3c26_age_phase_opportunity(*rank2, stage3c25)
    stage3c27 = assess_stage3c27_token_kinematics(*rank2, stage3c26)
    stage3c28 = assess_stage3c28_recurrent_basin(*rank2, stage3c27)
    stage3c29 = assess_stage3c29_transition_occupancy(*rank2, stage3c28)
    return rank2, stage3c28, stage3c29


def test_stage3c29_conditions_transition_and_locality_on_opportunity(
    stage3c29_inputs,
) -> None:
    rank2, stage3c28, _stage3c29 = stage3c29_inputs
    result = assess_stage3c29_transition_occupancy(*rank2, stage3c28)

    assert result["schema"] == STAGE3C29_TRANSITION_OCCUPANCY_SCHEMA
    findings = result["cross_source_findings"]
    assert findings[
        "exact_transition_class_replay_is_consistently_enriched_in_all_sources"
    ] is False
    assert findings[
        "nearest_second_coordinate_within_state_has_higher_opportunity_conditioned_selection_rate_in_all_sources"
    ]
    assert findings[
        "selected_candidate_has_lower_second_coordinate_step_mismatch_median_in_all_sources"
    ]

    for row in result["per_source"]:
        assert row["requested_query_count"] == 128
        assert row["assigned_query_count"] == 112
        assert row["forced_single_candidate_query_count"] == 16
        assert row["multi_candidate_query_count"] == 96
        assert row["reconstructed_score_selection_mismatch_count"] == 0
        basin = row["opportunity_conditioned_basin"]
        assert basin[
            "nearest_same_state_selection_rate_given_opportunity"
        ] == pytest.approx(1.0)
        assert basin[
            "non_nearest_same_state_selection_rate_given_opportunity"
        ] == pytest.approx(0.0)
        assert basin["same_state_winner_second_distance_rank"]["median"] == 1.0
        assert basin["nearest_vs_non_nearest_same_state_selection_rate_ratio"] is None
        assert basin[
            "nearest_vs_non_nearest_same_state_selection_rate_ratio_is_unbounded"
        ] is True
        drift = row["subject_anchor_drift"]
        assert drift["selected_second_coordinate_step_mismatch"]["median"] < drift[
            "unselected_second_coordinate_step_mismatch"
        ]["median"]

    interpretation = result["diagnostic_interpretation"]
    assert interpretation[
        "basin_occupancy_is_explained_by_stable_exact_transition_class_replay"
    ] is False
    assert interpretation[
        "subject_anchored_second_coordinate_locality_remains_predictive_after_opportunity_conditioning"
    ]
    assert result["runtime_or_checkpoint_schema_changed"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False
    json.dumps(result, ensure_ascii=False, allow_nan=False)


def test_stage3c29_rejects_tampered_stage3c28_checksum(stage3c29_inputs) -> None:
    rank2, stage3c28, _stage3c29 = stage3c29_inputs
    broken = deepcopy(stage3c28)
    broken["diagnostic_interpretation"][
        "winner_reuse_is_explained_by_exact_token_duplication"
    ] = True
    with pytest.raises(ValueError, match="checksum mismatch"):
        assess_stage3c29_transition_occupancy(*rank2, broken)


def test_stage3c29_rejects_stage3c28_lineage_mismatch(stage3c29_inputs) -> None:
    rank2, stage3c28, _stage3c29 = stage3c29_inputs
    broken = deepcopy(stage3c28)
    broken["rank2_study_sha256"] = "0" * 64
    broken.pop("assessment_sha256")
    broken["assessment_sha256"] = _canonical_sha256(broken)
    with pytest.raises(ValueError, match="lineage mismatch"):
        assess_stage3c29_transition_occupancy(*rank2, broken)


def test_stage3c30_separates_rank_collapse_from_positive_weight_robustness(
    stage3c29_inputs,
) -> None:
    rank2, _stage3c28, stage3c29 = stage3c29_inputs
    result = assess_stage3c30_weight_robustness(*rank2, stage3c29)

    assert result["schema"] == STAGE3C30_WEIGHT_ROBUSTNESS_SCHEMA
    assert result["second_coordinate_weight_panel"] == list(
        SECOND_COORDINATE_WEIGHT_PANEL
    )
    findings = result["cross_source_findings"]
    assert findings["rank_collapse_changes_selected_identity_in_all_sources"]
    assert findings[
        "rank_collapse_preserves_same_state_winner_fraction_exactly_in_all_sources"
    ]
    assert findings[
        "every_positive_weight_preserves_nearest_second_coordinate_ordering_in_all_sources"
    ]
    assert findings[
        "minimum_positive_weight_agreement_exceeds_rank_collapse_agreement_in_all_sources"
    ]

    for row in result["per_source"]:
        assert row["requested_query_count"] == 128
        assert row["assigned_query_count"] == 112
        assert row["forced_single_candidate_query_count"] == 16
        assert row["multi_candidate_query_count"] == 96
        assert row["reconstructed_score_selection_mismatch_count"] == 0
        factors = row["weight_factors"]
        assert factors["1"]["winner_agreement_with_baseline_fraction"] == 1.0
        assert factors["0"]["changed_winner_count"] > 0
        assert all(
            factors[f"{weight:g}"][
                "candidate_evaluation_count_matches_baseline_opportunity"
            ]
            for weight in SECOND_COORDINATE_WEIGHT_PANEL
        )
        assert row["source_summary"][
            "positive_weight_minimum_nearest_second_coordinate_fraction"
        ] == 1.0

    interpretation = result["diagnostic_interpretation"]
    assert interpretation[
        "first_coordinate_state_basin_persists_after_second_coordinate_rank_collapse"
    ]
    assert interpretation[
        "second_coordinate_is_required_to_resolve_within_state_winner_identity"
    ]
    assert interpretation["exact_positive_second_coordinate_weight_is_fine_tuned"] is False
    assert result["runtime_or_checkpoint_schema_changed"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False
    json.dumps(result, ensure_ascii=False, allow_nan=False)


def test_stage3c30_rejects_tampered_stage3c29_checksum(stage3c29_inputs) -> None:
    rank2, _stage3c28, stage3c29 = stage3c29_inputs
    broken = deepcopy(stage3c29)
    broken["diagnostic_interpretation"][
        "subject_anchored_second_coordinate_locality_remains_predictive_after_opportunity_conditioning"
    ] = False
    with pytest.raises(ValueError, match="checksum mismatch"):
        assess_stage3c30_weight_robustness(*rank2, broken)


def test_stage3c30_rejects_stage3c29_lineage_mismatch(stage3c29_inputs) -> None:
    rank2, _stage3c28, stage3c29 = stage3c29_inputs
    broken = deepcopy(stage3c29)
    broken["rank2_study_sha256"] = "0" * 64
    broken.pop("assessment_sha256")
    broken["assessment_sha256"] = _canonical_sha256(broken)
    with pytest.raises(ValueError, match="lineage mismatch"):
        assess_stage3c30_weight_robustness(*rank2, broken)
