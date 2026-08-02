from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_subject_graph_vm_contract_freezes_partitioned_unified_graph() -> None:
    contract = _load("protocols/epochs/subject_graph_vm_v1.json")
    assert contract["status"] == "stage-3c13-exposure-adequacy-implemented"
    assert contract["graph_model"]["identity"] == "one-unified-node-edge-identity-space"
    assert contract["graph_model"]["initial_regions"] == [
        "fast-sensorimotor",
        "persistent-state",
        "delayed-association",
        "integrative-drive",
    ]
    assert contract["routing"]["shared_graph"] is True
    assert contract["routing"]["same_tick_self_confirmation_forbidden"] is True
    assert contract["routing"]["unassigned_credit_allowed"] is True
    assert contract["implementation_stages"][1]["name"] == "inert-schema-storage"
    assert contract["current_stage"] == "3C-13"
    assert contract["stage_2_contract"]["plasticity"] is False
    assert contract["stage_3a_contract"]["persistent_node_edge_path"] is False
    assert contract["stage_3a_contract"]["plasticity"] is False
    assert contract["stage_3b1_contract"]["persistent_node_edge_path"] is False
    assert contract["stage_3b1_contract"]["objective_event_effect"] is False
    assert contract["stage_3b1_contract"]["plasticity"] is False
    assert contract["stage_3b2_contract"]["same_tick_candidate"] is False
    assert contract["stage_3b2_contract"]["mandatory_assignment"] is False
    assert contract["stage_3b2_contract"]["eligibility_modulation"] is False
    assert contract["stage_3b2_contract"]["plasticity"] is False
    assert contract["stage_3b3_contract"]["association_required"] is True
    assert contract["stage_3b3_contract"]["association_similarity_as_strength"] is False
    assert contract["stage_3b3_contract"]["specific_parameter_binding"] is False
    assert contract["stage_3b3_contract"]["eligibility_modulation"] is False
    assert contract["stage_3b3_contract"]["plasticity"] is False
    assert contract["stage_3c1_contract"]["universal_attention_claim"] is False
    assert contract["stage_3c1_contract"]["snapshot_before_current_activation_marks"] is True
    assert contract["stage_3c1_contract"]["same_tick_new_activity_target"] is False
    assert contract["stage_3c1_contract"]["parameter_update"] is False
    assert contract["stage_3c2_contract"]["stable_target_revalidation"] is True
    assert contract["stage_3c2_contract"]["per_subject_event_l1_budget"] is True
    assert contract["stage_3c2_contract"]["actual_parameter_write"] is False
    assert contract["stage_3c2_contract"]["applied_long_window_budget_ledger"] is False
    assert contract["stage_3c3_contract"]["exact_float32_compare_and_swap"] is True
    assert contract["stage_3c3_contract"]["all_or_none_per_event"] is True
    assert contract["stage_3c3_contract"]["rollback_verified"] is True
    assert contract["stage_3c3_contract"]["actual_parameter_write"] is False
    assert contract["stage_3c4_contract"]["default_enabled"] is False
    assert contract["stage_3c4_contract"]["explicit_opt_in"] is True
    assert contract["stage_3c4_contract"]["actual_parameter_write"] is True
    assert contract["stage_3c4_contract"]["write_permanent_after_commit"] is False
    assert contract["stage_3c4_contract"]["rollback_failure_locks_subject_writes"] is True
    assert contract["stage_3c5_contract"]["automatic_runtime_counterfactual"] is False
    assert contract["stage_3c5_contract"]["objective_scalar_score"] is False
    assert contract["stage_3c5_contract"]["automatic_keep_or_revert_decision"] is False
    assert contract["stage_3c5_contract"]["live_completion_requires_verified_rollback"] is True
    assert contract["stage_3c5_contract"]["new_parameter_write"] is False
    assert contract["stage_3c6_contract"]["source_checkpoint_must_be_quiescent"] is True
    assert contract["stage_3c6_contract"]["only_authorized_config_difference"] == "subject_vm.live_write.enabled"
    assert contract["stage_3c6_contract"]["componentwise_fact_differences"] is True
    assert contract["stage_3c6_contract"]["objective_scalar_score"] is False
    assert contract["stage_3c6_contract"]["automatic_keep_or_revert_decision"] is False
    assert contract["stage_3c6_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c7_contract"]["runtime_state_change"] is False
    assert contract["stage_3c7_contract"]["pairing_coverage_and_unpaired_reasons_reported"] is True
    assert contract["stage_3c7_contract"]["branch_divergence_componentwise"] is True
    assert contract["stage_3c7_contract"]["objective_scalar_score"] is False
    assert contract["stage_3c7_contract"]["automatic_keep_or_revert_decision"] is False
    assert contract["stage_3c7_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c8_contract"]["runtime_state_change"] is False
    assert contract["stage_3c8_contract"]["independent_replicate"] == "source-checkpoint-state"
    assert contract["stage_3c8_contract"]["within_source_subject_balancing"] is True
    assert contract["stage_3c8_contract"]["window_pseudoreplication"] is False
    assert contract["stage_3c8_contract"]["universal_scalar_objective"] is False
    assert contract["stage_3c8_contract"]["automatic_keep_or_revert_decision"] is False
    assert contract["stage_3c8_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c9_contract"]["control_admission_parity"] is True
    assert contract["stage_3c9_contract"]["fixed_bootstrap_graph_is_evolved_result"] is False
    assert contract["stage_3c9_contract"]["export_boundary_transient_finalization"] is True
    assert contract["stage_3c9_contract"]["incomplete_windows_are_evidence"] is False
    assert contract["stage_3c9_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c10_contract"]["trace_retention_coverage_reported"] is True
    assert (
        contract["stage_3c10_contract"][
            "paired_admission_contract_distinguished_from_post-divergence-transaction-path"
        ]
        is True
    )
    assert contract["stage_3c10_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c11_contract"]["runtime_state_change"] is False
    assert contract["stage_3c11_contract"]["single_changed_factor"] == "independent-source-count-3-to-9"
    assert contract["stage_3c11_contract"]["within_source_windows_are_independent_replicates"] is False
    assert contract["stage_3c11_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c12_contract"]["runtime_state_change"] is False
    assert contract["stage_3c12_contract"]["single_changed_factor"] == "branch-horizon-ticks-5-to-8"
    assert contract["stage_3c12_contract"]["identical_source_state_panel_required"] is True
    assert contract["stage_3c12_contract"]["exact_semantic_prefix_identity_required"] is True
    assert contract["stage_3c12_contract"]["complete_bounded_trace_coverage_required"] is True
    assert contract["stage_3c12_contract"]["within_source_windows_are_independent_replicates"] is False
    assert contract["stage_3c12_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c13_contract"]["runtime_state_change"] is False
    assert contract["stage_3c13_contract"]["single_changed_factor"] == (
        "rollback-after-ticks-2-to-3-with-control-horizon-synchronized"
    )
    assert contract["stage_3c13_contract"][
        "identical_source_state_and_config_required"
    ] is True
    assert contract["stage_3c13_contract"][
        "read_only_control_behavior_identity_required"
    ] is True
    assert contract["stage_3c13_contract"][
        "within_source_windows_are_independent_replicates"
    ] is False
    assert contract["stage_3c13_contract"]["permanent_write_authorized"] is False

    reproducibility = _load(
        "protocols/decisions/subject_graph_vm_component_reproducibility_v1.json"
    )
    assert reproducibility["replicate_hierarchy"]["highest_level_replicate"] == "independent-source-checkpoint"
    assert reproducibility["replicate_hierarchy"]["windows_are_independent_replicates"] is False
    assert reproducibility["componentwise_statistics"]["sign_counts_and_fractions"] is True
    assert reproducibility["output"]["universal_scalar_objective"] is False
    assert reproducibility["output"]["automatic_keep_or_revert_decision"] is False
    assert reproducibility["scientific_boundary"]["scientific_reproducibility_conclusion_automatic"] is False

    paired_integrity = _load(
        "protocols/decisions/subject_graph_vm_paired_evidence_integrity_v1.json"
    )
    assert paired_integrity["inputs"]["multiple_independent_source_checkpoints_supported"] is True
    assert paired_integrity["pairing_adequacy"]["unpaired_windows_preserved"] is True
    assert paired_integrity["integrity"]["rollback_failure_count_reported"] is True
    assert paired_integrity["integrity"]["branch_divergence_is_automatic_invalidity"] is False
    assert paired_integrity["output"]["scalar_score"] is False
    assert paired_integrity["output"]["automatic_keep_or_revert_decision"] is False
    assert paired_integrity["scientific_boundary"]["scientific_sufficiency_automatic"] is False

    evaluation = _load(
        "protocols/decisions/subject_graph_vm_objective_evaluation_window_v1.json"
    )
    assert evaluation["comparison_arms"]["automatic_within_runtime_counterfactual"] is False
    assert evaluation["objective_evidence"]["objective_scalar_score"] is False
    assert evaluation["objective_evidence"]["keep_or_revert_decision"] is False
    assert evaluation["window"]["live_completion_requires_verified_rollback"] is True
    assert evaluation["write_authority"]["new_parameter_write"] is False
    assert evaluation["scientific_boundary"]["causal_effect_claim"] is False

    guarded_write = _load(
        "protocols/decisions/subject_graph_vm_guarded_live_write_v1.json"
    )
    assert guarded_write["opt_in"]["default_enabled"] is False
    assert guarded_write["preconditions"]["shadow_rollback_verified"] is True
    assert guarded_write["budgets"]["overlapping_pending_target_forbidden"] is True
    assert guarded_write["rollback"]["rollback_failure_locks_future_writes_for_subject"] is True
    assert guarded_write["cost"]["entity_energy_debit"] is False
    assert guarded_write["scientific_boundary"]["learning_claim"] is False

    shadow_transaction = _load(
        "protocols/decisions/subject_graph_vm_shadow_transaction_v1.json"
    )
    assert shadow_transaction["compare_and_swap"]["comparison"] == "bit-identical expected and observed values"
    assert shadow_transaction["atomicity"]["partial_shadow_commit"] is False
    assert shadow_transaction["shadow_and_rollback"]["permanent_write_authorized"] is False
    assert shadow_transaction["cost"]["entity_energy_debit"] is False

    update_safety = _load(
        "protocols/decisions/subject_graph_vm_update_safety_v1.json"
    )
    assert update_safety["bootstrap_formula"]["objective_event_value"] is False
    assert update_safety["bootstrap_formula"]["universal_learning_rule_claim"] is False
    assert update_safety["target_revalidation"]["stable_target_id_required"] is True
    assert update_safety["write_authority"]["parameter_write"] is False
    assert update_safety["cumulative_budget"]["unexecuted_proposals_consume_long_window_budget"] is False

    target_binding = _load(
        "protocols/decisions/subject_graph_vm_target_binding_v1.json"
    )
    assert target_binding["bootstrap_bias"]["universal_attention_claim"] is False
    assert target_binding["candidate_timing"]["snapshot_before_current_activation_marks"] is True
    assert target_binding["write_authority"]["parameter_write"] is False

    modulation = _load(
        "protocols/decisions/subject_graph_vm_modulation_proposal_v1.json"
    )
    assert modulation["token_controls"]["cryptographic_hash"] is False
    assert modulation["proposal_math"]["association_similarity_as_strength"] is False
    assert modulation["causal_order"]["parameter_binding"] is False
    assert modulation["causal_order"]["parameter_update"] is False

    delayed_association = _load(
        "protocols/decisions/subject_graph_vm_delayed_association_v1.json"
    )
    assert delayed_association["representation"]["cryptographic_hash"] is False
    assert delayed_association["representation"]["request_coordinate_in_similarity"] is False
    assert delayed_association["candidate_selection"]["mandatory_assignment"] is False
    assert delayed_association["causal_order"]["parameter_update"] is False
    assert delayed_association["architecture_role"] == "bootstrap-fixed-content-address-baseline"
    assert delayed_association["universal_attention_claim"] is False

    local_eligibility = _load(
        "protocols/decisions/subject_graph_vm_local_eligibility_v1.json"
    )
    assert local_eligibility["representation"]["persistent_full_path"] is False
    assert local_eligibility["event_semantics"]["mandatory_assignment"] is False
    assert local_eligibility["causal_order"]["parameter_update"] is False

    token_trace = _load("protocols/decisions/subject_graph_vm_token_trace_v1.json")
    assert token_trace["representation"]["primary"] == "continuous-fixed-width-token"
    assert "executed node IDs" in token_trace["explicitly_not_persisted"]

    activation = _load("protocols/decisions/subject_graph_vm_activation_v1.json")
    assert activation["status"] == "accepted-engineering-stage-only"
    assert activation["accounting"]["physical_energy_debit"] is False
    assert activation["causal_order"]["same_phase_order_dependence"] is False
    assert contract["legacy_status"]["d1x_d1y"].startswith("rejected-as-primary")


def test_epoch_one_uses_functional_v2_contract_not_semantic_ledgers() -> None:
    registry = _load("protocols/epochs/subject_epochs_v1.json")
    epoch = next(
        item for item in registry["epochs"]
        if item["epoch_id"] == "epoch-1-entity-subject-prototype"
    )
    assert epoch["entry_contract"]["contract_id"] == "entity-subject-functional-qualification-v2"
    assert epoch["entry_contract"]["contract_file"] == "protocols/epochs/entity_subject_functional_qualification_v2.json"

    contract = _load(epoch["entry_contract"]["contract_file"])
    stages = {item["stage"] for item in contract["required_stages"]}
    assert {
        "delayed-history-use",
        "behavioral-control",
        "baseline-exceedance",
        "cost-compensation",
        "long-horizon-replication",
    } <= stages
    assert any("designer-defined material or knowledge" in item for item in contract["forbidden_shortcuts"])


def test_old_interest_contract_is_retained_only_as_superseded_baseline() -> None:
    old = _load("protocols/epochs/interest_feedback_network_qualification_v1.json")
    assert old["status"] == "superseded-as-primary-contract"
    assert old["superseded_by"] == "entity-subject-functional-qualification-v2"
    assert "fixed-cognition comparison baseline" in old["retained_use"]
