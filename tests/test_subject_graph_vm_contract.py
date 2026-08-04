from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_subject_graph_vm_contract_freezes_partitioned_unified_graph() -> None:
    contract = _load("protocols/epochs/subject_graph_vm_v1.json")
    assert contract["status"] == "stage-3c42-frozen-thought-event-t2-qualified"
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
    assert contract["current_stage"] == "ThoughtEvent-T2"
    design = contract["thought_event_language_design_contract"]
    assert design["status"] == "t2-qualified-for-t3-mechanism-smoke-only"
    assert design["t1_unified_arena_implemented"] is True
    assert design["t1_runtime_parent_count"] == 0
    assert design["t2_read_only_audit_completed"] is True
    assert design["t3_mechanism_smoke_authorized"] is True
    assert design["thought_chain_claim_authorized"] is False
    assert design["single_thought_representation"] is True
    assert design["rethink_action_authorized"] is False
    assert design["confidence_halt_gate_authorized"] is False
    assert design["forward_recall_implemented"] is False
    assert design["communication_interface_implemented"] is False
    assert design["language_region_owns_semantics"] is False
    assert design["cross_seed_alignment_requires_functional_relational_evidence"] is True
    assert design["huffman_like_encoding_is_hypothesis_not_contract"] is True
    t1 = contract["thought_event_t1_contract"]
    assert t1["default_enabled"] is False
    assert t1["same_graph_token_as_stage3_trace"] is True
    assert t1["action_and_objective_fact_excluded"] is True
    assert t1["enabled_configuration_checkpoint_clone_branch_identity_member"] is True
    assert t1["forward_recall"] is False
    t2 = contract["thought_event_t2_contract"]
    assert t2["seed_count"] == 9
    assert t2["duplicate_coordinate_control_centered_rank"] == 1
    assert t2["rank_two_candidate_centered_rank"] == 2
    assert t2["t3_mechanism_smoke_authorized"] is True
    assert t2["thought_chain_claim_authorized"] is False
    assert contract["stage_3c36_contract"]["candidate_support_identity_required"] is True
    assert contract["stage_3c36_contract"]["frozen_result"]["exact_tie_origin_resolved"] is False
    assert contract["stage_3c36_contract"]["gate_relaxation_authorized"] is False
    trace = contract["categorical_sampling_trace_contract"]
    assert trace["task_type"] == "ENGINEERING"
    assert trace["runtime_semantics_changed"] is False
    assert trace["checkpoint_state_changed"] is False
    assert trace["branch_identity_changed"] is False
    assert trace["stage3c40_read_only_boundary_unlocked"] is True
    assert trace["scientific_conclusion_authorized"] is False
    activation_trace = contract["activation_contribution_trace_contract"]
    assert activation_trace["task_type"] == "ENGINEERING"
    assert activation_trace["runtime_semantics_changed"] is False
    assert activation_trace["checkpoint_state_changed"] is False
    assert activation_trace["branch_identity_changed"] is False
    assert activation_trace["random_stream_consumed_by_trace"] is False
    assert activation_trace["node_edge_output_reconstruction_required"] is True
    assert activation_trace["temporary_write_lineage_required"] is True
    assert activation_trace["stage3c42_read_only_boundary_unlocked"] is True
    assert activation_trace["scientific_conclusion_authorized"] is False
    assert activation_trace["no_action_authorized"] is False
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
    assert contract["stage_3c14_contract"]["runtime_state_change"] is False
    assert contract["stage_3c14_contract"]["association_similarity_control_ports_excluded"] is True
    assert contract["stage_3c14_contract"][
        "identical_pre_bootstrap_source_state_and_config_required"
    ] is True
    assert contract["stage_3c14_contract"][
        "within_source_windows_are_independent_replicates"
    ] is False
    assert contract["stage_3c14_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c15_contract"]["runtime_state_change"] is False
    assert contract["stage_3c15_contract"]["source_checkpoint_mutated"] is False
    assert contract["stage_3c15_contract"]["probe_branch_persisted"] is False
    assert contract["stage_3c15_contract"][
        "local_sensitivity_and_eligibility_reachability_separated"
    ] is True
    assert contract["stage_3c15_contract"]["delayed_edge_context_required"] is True
    assert contract["stage_3c15_contract"]["bandwidth_clamp_state_reported"] is True
    assert contract["stage_3c15_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c16_contract"]["runtime_state_change"] is False
    assert contract["stage_3c16_contract"]["single_changed_factor"] == (
        "bootstrap-edge-0-local-eligibility-carrier-disabled-to-enabled"
    )
    assert contract["stage_3c16_contract"]["target_family_fixed"] == "edge_forward_gate"
    assert contract["stage_3c16_contract"][
        "read_only_control_behavior_identity_required"
    ] is True
    assert contract["stage_3c16_contract"][
        "carrier_off_unreachable_baseline_is_stage3c8_replicate"
    ] is False
    assert contract["stage_3c16_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c17_contract"]["runtime_persistent_state_change"] is False
    assert contract["stage_3c17_contract"]["single_changed_factor"] == "equal-similarity-temporal-tie-break-latest-to-oldest"
    assert contract["stage_3c17_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c18_contract"]["single_changed_factor"] == "association-candidate-limit-one-to-two"
    assert contract["stage_3c18_contract"]["same_event_delta_budget"] is True
    assert contract["stage_3c18_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c19_contract"]["runtime_state_change"] is False
    assert contract["stage_3c19_contract"]["checkpoint_schema_change"] is False
    assert contract["stage_3c19_contract"]["association_visible_coordinates_only"] is True
    assert contract["stage_3c19_contract"]["tokens_or_pairs_are_independent_replicates"] is False
    assert contract["stage_3c19_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c20_contract"]["runtime_persistent_state_change"] is False
    assert contract["stage_3c20_contract"]["checkpoint_schema_change"] is False
    assert contract["stage_3c20_contract"]["single_changed_factor"] == (
        "fixed-bootstrap-node0-state-to-visible-token-port29"
    )
    assert contract["stage_3c20_contract"]["association_visible_port"] == 29
    assert contract["stage_3c20_contract"][
        "read_only_objective_behavior_identity_required"
    ] is True
    assert contract["stage_3c20_contract"][
        "within_source_tokens_subjects_or_windows_are_independent_replicates"
    ] is False
    assert contract["stage_3c20_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c21_contract"]["runtime_persistent_state_change"] is False
    assert contract["stage_3c21_contract"]["checkpoint_schema_change"] is False
    assert contract["stage_3c21_contract"]["single_changed_factor"] == (
        "readout-only-node8-input-port-constant-one-0-to-uncertainty-mean-11"
    )
    assert contract["stage_3c22_contract"]["runtime_state_change"] is False
    assert contract["stage_3c22_contract"]["checkpoint_schema_change"] is False
    assert contract["stage_3c22_contract"][
        "stored_selection_exact_reconstruction_required"
    ] is True
    assert contract["stage_3c22_contract"][
        "within_source_events_subjects_or_windows_are_independent_replicates"
    ] is False
    assert contract["stage_3c22_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c23_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c23_contract"]["single_changed_factor"] == (
        "readout-only-node9-input-port-uncertainty-11-to-local-resource-ratio-3-7"
    )
    assert contract["stage_3c23_contract"]["common_primary_readout_port"] == 29
    assert contract["stage_3c23_contract"]["second_readout_port"] == 30
    assert contract["stage_3c23_contract"]["readout_changes_action_output"] is False
    assert contract["stage_3c23_contract"][
        "read_only_objective_behavior_identity_required"
    ] is True
    assert contract["stage_3c23_contract"][
        "within_source_tokens_subjects_or_windows_are_independent_replicates"
    ] is False
    assert contract["stage_3c23_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c24_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c24_contract"]["stored_selection_and_score_reconstruction_required"] is True
    assert contract["stage_3c24_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c25_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c25_contract"]["margin_scale_separation_required"] is True
    assert contract["stage_3c25_contract"]["exact_query_vector_reuse_check_required"] is True
    assert contract["stage_3c25_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c28_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c28_contract"]["rank_two_readout_fixed"] is True
    assert contract["stage_3c28_contract"]["stored_selection_and_score_reconstruction_required"] is True
    assert contract["stage_3c28_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c29_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c29_contract"]["rank_two_readout_fixed"] is True
    assert contract["stage_3c29_contract"]["stage3c28_checksum_and_lineage_required"] is True
    assert contract["stage_3c29_contract"]["forced_single_candidate_queries_excluded"] is True
    assert contract["stage_3c29_contract"][
        "within_source_queries_candidates_events_subjects_or_windows_are_independent_replicates"
    ] is False
    assert contract["stage_3c29_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c30_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c30_contract"]["rank_two_readout_fixed"] is True
    assert contract["stage_3c30_contract"][
        "authoritative_raw_candidate_opportunity_fixed"
    ] is True
    assert contract["stage_3c30_contract"][
        "stage3c29_checksum_and_lineage_required"
    ] is True
    assert contract["stage_3c30_contract"][
        "candidate_evaluation_count_matched_per_weight_arm"
    ] is True
    assert contract["stage_3c30_contract"]["coordinate_weight_has_value_semantics"] is False
    assert contract["stage_3c30_contract"]["learned_weight_authorized"] is False
    assert contract["stage_3c30_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c31_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c31_contract"]["rank_two_readout_fixed"] is True
    assert contract["stage_3c31_contract"]["within_first_state_competitions_only"] is True
    assert contract["stage_3c31_contract"]["stage3c30_checksum_and_lineage_required"] is True
    assert contract["stage_3c31_contract"]["per_tick_second_coordinate_marginal_preserved"] is True
    assert contract["stage_3c31_contract"]["candidate_evaluation_count_matched"] is True
    assert contract["stage_3c31_contract"]["objective_fact_vectors_unchanged_and_reported_componentwise"] is True
    assert contract["stage_3c31_contract"]["learned_weight_authorized"] is False
    assert contract["stage_3c31_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c32_contract"]["runtime_or_checkpoint_schema_change"] is True
    assert contract["stage_3c32_contract"]["rank_two_source_checkpoint_fixed"] is True
    assert contract["stage_3c32_contract"]["stage3c31_checksum_and_lineage_required"] is True
    assert contract["stage_3c32_contract"]["four_arm_shared_checkpoint_design"] is True
    assert contract["stage_3c32_contract"]["same_alignment_sort_copy_code_path"] is True
    assert contract["stage_3c32_contract"]["per_tick_second_coordinate_marginal_preserved"] is True
    assert contract["stage_3c32_contract"]["cyclic_self_donor_forbidden"] is True
    assert contract["stage_3c32_contract"]["candidate_evaluation_count_matched"] is True
    assert contract["stage_3c32_contract"]["runtime_storage_bytes_matched"] is True
    assert contract["stage_3c32_contract"]["forced_rollback_required"] is True
    assert contract["stage_3c32_contract"]["objective_fact_evaluation_componentwise_difference_in_differences"] is True
    assert contract["stage_3c32_contract"]["learned_weight_authorized"] is False
    assert contract["stage_3c32_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c33_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c33_contract"]["frozen_stage3c32_baseline_reproduced"] is True
    assert contract["stage_3c33_contract"]["horizon_only_control_required"] is True
    assert contract["stage_3c33_contract"]["common_horizon_read_only_control_behavior_identity_required"] is True
    assert contract["stage_3c33_contract"]["same_rank_two_source_checkpoint_panel_required"] is True
    assert contract["stage_3c33_contract"]["same_four_arm_alignment_intervention_required"] is True
    assert contract["stage_3c33_contract"]["forced_rollback_required"] is True
    assert contract["stage_3c33_contract"]["exposure_dose_ledger_integrity_required"] is True
    assert contract["stage_3c33_contract"]["frozen_result"]["dose_ratio"] == 2.0
    assert contract["stage_3c33_contract"][
        "fixed_common_horizon_event_identity_support_required"
    ] is True
    assert contract["stage_3c33_contract"][
        "evaluation_observation_coverage_audit_required"
    ] is True
    assert contract["stage_3c33_contract"]["frozen_result"][
        "paired_window_completion_support_matches"
    ] is False
    assert contract["stage_3c33_contract"]["frozen_result"][
        "fixed_horizon_trajectory_support_matches"
    ] is True
    assert contract["stage_3c33_contract"]["frozen_result"][
        "extended_exposure_adds_new_nonzero_sources"
    ] == 1
    assert contract["stage_3c33_contract"]["frozen_result"][
        "exposure_only_nonzero_source_seeds"
    ] == [12305, 12308]
    assert contract["stage_3c33_contract"]["frozen_result"]["source_replicated_propagation_supported"] is False
    assert contract["stage_3c33_contract"]["adaptive_exposure_extension_authorized"] is False
    assert contract["stage_3c33_contract"]["automatic_keep_or_revert_authorized"] is False
    assert contract["stage_3c33_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c34_contract"]["runtime_or_checkpoint_schema_change"] is False
    assert contract["stage_3c34_contract"]["stage3c33_checksum_and_lineage_required"] is True
    assert contract["stage_3c34_contract"]["same_eight_arm_event_identity_support_required"] is True
    assert contract["stage_3c34_contract"]["runtime_rerun_authorized"] is False
    assert contract["stage_3c34_contract"]["selected_seed_rerun_authorized"] is False
    assert contract["stage_3c34_contract"]["sampled_action_crossing_separated_into_alignment_common_and_differential"] is True
    assert contract["stage_3c34_contract"]["objective_fact_crossing_reported_componentwise"] is True
    assert contract["stage_3c34_contract"]["stage3c33_subject_balanced_fact_sum_reproduction_required"] is True
    assert contract["stage_3c34_contract"]["full_numeric_action_threshold_margin_observable"] is False
    assert contract["stage_3c34_contract"]["frozen_result"]["potential_divergence_source_count"] == 9
    assert contract["stage_3c34_contract"]["frozen_result"]["any_action_crossing_source_seeds"] == [12305, 12307, 12308]
    assert contract["stage_3c34_contract"]["frozen_result"]["alignment_differential_action_crossing_source_seeds"] == [12305, 12308]
    assert contract["stage_3c34_contract"]["frozen_result"]["alignment_common_action_crossing_source_seeds"] == [12307]
    assert contract["stage_3c34_contract"]["frozen_result"]["alignment_differential_objective_crossing_source_seeds"] == [12305, 12308]
    assert contract["stage_3c34_contract"]["frozen_result"]["differential_action_crossing_event_count"] == 4
    assert contract["stage_3c34_contract"]["frozen_result"]["differential_objective_crossing_event_count"] == 12
    assert contract["stage_3c34_contract"]["frozen_result"]["delayed_objective_crossing_event_count"] == 8
    assert contract["stage_3c34_contract"]["frozen_result"]["later_aggregation_cancellation_source_count"] == 0
    assert contract["stage_3c34_contract"]["frozen_result"]["stage3c33_nonzero_source_identity_reproduced"] is True
    assert contract["stage_3c34_contract"]["automatic_keep_or_revert_authorized"] is False
    assert contract["stage_3c34_contract"]["learned_weight_authorized"] is False
    assert contract["stage_3c34_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c35_contract"]["source_panels_disjoint"] is True
    assert contract["stage_3c35_contract"]["stage3c27_prerequisite_must_pass_before_stage3c28_or_later"] is True
    assert contract["stage_3c35_contract"]["frozen_result"]["reference_stage3c28_gate_passed"] is True
    assert contract["stage_3c35_contract"]["frozen_result"]["replication_stage3c28_gate_passed"] is False
    assert contract["stage_3c35_contract"]["frozen_result"]["complete_source_screen_seeds"] == [12402, 12408]
    assert contract["stage_3c35_contract"]["frozen_result"]["crossing_prediction_tested"] is False
    assert contract["stage_3c35_contract"]["selected_seed_replacement_authorized"] is False
    assert contract["stage_3c35_contract"]["gate_relaxation_authorized"] is False
    assert contract["stage_3c35_contract"]["permanent_write_authorized"] is False
    assert contract["stage_3c21_contract"]["common_readout_only_node_index"] == 8
    assert contract["stage_3c21_contract"]["readout_changes_action_output"] is False
    assert contract["stage_3c21_contract"][
        "read_only_objective_behavior_identity_required"
    ] is True
    assert contract["stage_3c21_contract"][
        "within_source_tokens_subjects_or_windows_are_independent_replicates"
    ] is False
    assert contract["stage_3c21_contract"]["uncertainty_value_semantics"] is False
    assert contract["stage_3c21_contract"]["permanent_write_authorized"] is False

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


def test_stage3c40_contract_is_frozen_and_nonretaining() -> None:
    contract = _load("protocols/epochs/subject_graph_vm_v1.json")
    stage = contract["stage_3c40_contract"]
    assert stage["trace_instrumentation_semantics_changed"] is False
    assert stage["frozen_result"]["replication_all_pressure_ratios_below_one"] is True
    assert stage["permanent_write_authorized"] is False


def test_stage3c41_contract_is_frozen_read_only_and_nonretaining() -> None:
    contract = _load("protocols/epochs/subject_graph_vm_v1.json")
    stage = contract["stage_3c41_contract"]
    assert stage["runtime_rerun_authorized"] is False
    assert stage["frozen_result"]["all_nonzero_masked_logit_changes_are_rest_only"] is True
    assert stage["frozen_result"]["rest_logit_magnitude_alone_separates_crossing"] is False
    assert stage["rest_action_port_has_value_semantics"] is False
    assert stage["permanent_write_authorized"] is False


def test_stage3c42_contract_is_frozen_read_only_and_nonretaining() -> None:
    contract = _load("protocols/epochs/subject_graph_vm_v1.json")
    stage = contract["stage_3c42_contract"]
    assert stage["runtime_or_checkpoint_schema_change"] is False
    assert stage["runtime_rerun_only_for_observation_trace"] is True
    assert stage["frozen_result"]["all_exposure_did_structural_contribution_is_current_edge_gate"] is True
    assert stage["frozen_result"]["maximum_abs_inherited_node_state_component"] == 0.0
    assert stage["frozen_result"]["current_gate_component_magnitude_alone_separates_crossing"] is False
    assert stage["frozen_result"]["source_history_proposal_origin_is_fully_resolved"] is False
    assert stage["rest_action_port_has_value_semantics"] is False
    assert stage["permanent_write_authorized"] is False
    assert stage["next_project_boundary"] == "evolve-subject-unified-thought-event-chain-substrate"
