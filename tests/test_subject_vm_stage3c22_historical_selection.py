from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from se.analysis.subject_vm_stage3c21_subject_event_readout import (
    assess_stage3c21_subject_event_readout,
)
from se.analysis.subject_vm_stage3c22_historical_selection import (
    STAGE3C22_HISTORICAL_SELECTION_SCHEMA,
    assess_stage3c22_historical_selection,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)

CONFIG = "configs/mvp_short_subject_vm_stage3c21_subject_event_readout_study.json"


def _run(root: Path, *, input_port: int):
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
            bootstrap_readout_input_port=input_port,
            association_tie_break="latest",
            association_candidate_limit=1,
        ),
        output_dir=root / f"port_{input_port}",
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    return report, component, diagnostics


@pytest.fixture(scope="module")
def stage3c22_inputs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("stage3c22")
    constant = _run(root, input_port=0)
    uncertainty = _run(root, input_port=11)
    stage3c21 = assess_stage3c21_subject_event_readout(
        *constant, *uncertainty
    )
    return constant, uncertainty, stage3c21


def test_stage3c22_separates_candidate_opportunity_from_selected_coverage(
    stage3c22_inputs,
) -> None:
    constant, uncertainty, stage3c21 = stage3c22_inputs
    result = assess_stage3c22_historical_selection(
        *constant, *uncertainty, stage3c21
    )

    assert result["schema"] == STAGE3C22_HISTORICAL_SELECTION_SCHEMA
    isolation = result["isolation_contract"]
    assert isolation[
        "same_delay_valid_nonzero_and_above_threshold_candidate_opportunity"
    ]
    assert isolation["stored_selections_exactly_reconstructed"]

    constant_rows = result["constant_readout"]["per_source"]
    uncertainty_rows = result["uncertainty_readout"]["per_source"]
    assert [
        row["candidate_opportunity"]["above_threshold_reference_count"]
        for row in constant_rows
    ] == [432, 432, 432]
    assert [
        row["candidate_opportunity"]["above_threshold_reference_count"]
        for row in uncertainty_rows
    ] == [432, 432, 432]
    assert [
        row["selected_identity_coverage"][
            "unique_selected_historical_event_count"
        ]
        for row in constant_rows
    ] == [112, 112, 112]
    assert [
        row["selected_identity_coverage"][
            "unique_selected_historical_event_count"
        ]
        for row in uncertainty_rows
    ] == [94, 88, 93]
    assert all(
        row["reuse_concentration"]["maximum_historical_event_reuse"] == 1
        for row in constant_rows
    )
    assert all(
        row["reuse_concentration"]["maximum_historical_event_reuse"] == 3
        for row in uncertainty_rows
    )
    assert all(
        row["reuse_concentration"]["eligible_union_selection_gini"] == 0.0
        for row in constant_rows
    )
    assert all(
        row["reuse_concentration"]["eligible_union_selection_gini"] > 0.0
        for row in uncertainty_rows
    )

    comparison = result["comparison"]
    assert comparison["candidate_opportunity_equal_in_all_sources"]
    assert comparison["uncertainty_selected_set_is_strict_subset_in_all_sources"]
    assert comparison["uncertainty_adds_any_new_selected_event_identity"] is False
    assert comparison["uncertainty_reduces_unique_identity_coverage_in_all_sources"]
    assert comparison["uncertainty_increases_maximum_reuse_in_all_sources"]
    assert comparison[
        "selected_objective_fact_centered_rank_preserved_in_all_sources"
    ]
    assert comparison["exact_same_query_selection_fraction"]["maximum"] < 1.0
    assert result["diagnostic_interpretation"][
        "subject_event_geometry_increases_selected_event_identity_diversity"
    ] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c22_rejects_stage3c21_lineage_mismatch(stage3c22_inputs) -> None:
    constant, uncertainty, stage3c21 = stage3c22_inputs
    broken = deepcopy(stage3c21)
    broken["constant_study_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="lineage mismatch"):
        assess_stage3c22_historical_selection(
            *constant, *uncertainty, broken
        )
