# Structural measurement protocol audit

Schema: `structural-measurement-protocol-audit-v45`
Audit SHA-256: `8c53345969968ee98d43a030a8f39392ad43b78ebf763b281c9331af7d0ea793`

## Execution backend

- CLI default: `auto`
- configured GPU semantics: `hybrid-accelerated`
- GPU preference: hybrid GPU acceleration when compatible CuPy/CUDA is available
- unavailable GPU: recorded CPU fallback without changing model configuration or random streams
- strict-reference: retained as an explicit historical diagnostic mode; not the production default
- semantic validation: `tests/test_parity.py` / `cpu-gpu-parity-v2`
- parity certificate: `gpu-parity-certificate-v1` via tests/test_parity.py under make parity-gpu
- execution provenance audit: `gpu-execution-audit-v1`
- device-resident preprocessing: ['resource-affinity quantization', 'danger-evidence quantization', 'policy resource-view construction', 'oxygen-gradient construction', 'non-diagnostic information summaries']
- large-run validation: per-tick validation may be disabled for preregistered large GPU runs; semantic validation remains mandatory through test_parity on the target stack
- parity scope: ['device stage algorithms', 'prepared observations and policy decisions', 'intents and resolutions', 'birth and death plans', 'all checkpoint-authoritative semantic leaves', 'persistent GPU entity, environment, information, and social mirrors']
- feedback to world: False

## Run reporting

- plan schema: `simulation-run-plan-v1`
- plan written before first step: True
- summary schema: `authoritative-reporting-snapshot-v1`
- materialize hybrid state at every report: True
- tick consistency required: True
- checkpoint cadence independent: True
- outcome-conditioned schedule changes: False
- feedback to world: False

## Demographic selection validity

- audit / plan: `demographic-selection-validity-audit-v3` / `demographic-selection-validity-plan-v3`
- independent unit: `run-seed`
- windows independent: False
- default population floor: 0.25
- turnover requirements: {'minimum_mean_generation': 1.0, 'minimum_max_generation': 3, 'minimum_cumulative_births_per_initial': 1.0, 'minimum_descendant_alive_fraction': 0.75}
- settled-source requirements: {'minimum_recent_windows': 3, 'minimum_alive': 1000, 'maximum_alive_cv': 0.15, 'maximum_abs_net_growth_fraction': 0.15, 'maximum_alive_slope_fraction_per_window': 0.02, 'maximum_span_change_fraction': 0.1, 'minimum_unique_successful_parents_per_window': 100, 'minimum_effective_successful_parents_per_window': 80.0, 'maximum_largest_parent_contribution_fraction': 0.05}
- source-rule scope: pilot-derived burn-in candidates apply only to new independent seeds; pilot windows are not reused as confirmatory effect evidence
- automatic multi-seed audit / plan: True / `multi-seed-run-plan-v4`
- death-cause accounting: {'canonical_signature_buckets': 8, 'energy_integrity_age_overlap_preserved': True, 'checkpointed': True}
- rescue / replacement / feedback: False / False / False
- boundary: rapid collapse before generation turnover is retained as a bottleneck-dominated trajectory. A later rebound is separately audited for stable population level, near-zero recent population trend, descendant turnover, founder-lineage breadth, current heritable variation, and independent reproductive-contributor breadth before it can define a future source rule

## Tiered exploration

- readiness / source plan / paired plan: `exploration-readiness-audit-v2` / `tiered-exploration-plan-v1` / `tiered-paired-exploration-plan-v2`
- independent unit: `seed`
- nested observations: ['time windows', 'entities', 'births and deaths', 'moves and policy events']
- source checkpoint: {'exact_tick_predeclared': True, 'full_checkpoint_hash_locked': True, 'scale_normalized_acute_support': {'minimum_alive': 'max(64, 0.08 * initial population)', 'minimum_effective_lineages': 'max(32, 0.04 * initial population)', 'maximum_largest_lineage_fraction': 0.25}, 'demographic_turnover_required_for_acute_panel': False, 'free_run_endpoint_is_candidate_effect': False}
- matched branches: ['baseline', 'intervention']
- promotion gate: {'minimum_eligible_seed_fraction': 0.75, 'minimum_direction_consistency': 0.75, 'practical_relative_effect_predeclared': True, 'operational_manipulation_checks_predeclared': True, 'operational_manipulation_checks_required_when_present': True, 'exact_sign_flip_descriptive': True}
- candidate ledger: {'automatic_record_after_execution': True, 'terminal_failed_candidate_reopened_automatically': False, 'candidate_relabeling_allowed': False, 'threshold_or_horizon_change_requires_new_revision': True, 'manipulation_engagement_recorded_separately_from_effect_gate': True, 'manipulation_confirmed_negative_is_candidate_specific': True, 'bounded_negative_requires_aggregate_gate': True, 'additional_bounded_children_before_aggregate_gate': False, 'mechanism_family_metadata_is_non_inferential': True, 'aggregate_family_gate_can_close_current_family_revision': True, 'non_aggregate_candidate_can_close_family_revision': False, 'family_reopening_requires_higher_revision_and_rationale': True, 'family_reopening_requires_new_directly_measurable_interface': True, 'portfolio_audit_schema': 'paired-exploration-portfolio-audit-v1', 'automatic_new_candidate_selection': False, 'family_closure_feedback_to_world': False, 'feedback_to_world': False}
- stages: {'smoke': {'minimum_seeds': 2, 'purpose': 'mechanism and measurement validation'}, 'screen': {'minimum_seeds': 8, 'requires_fixed_checkpoint_matched_branches': True}, 'replication': {'minimum_seeds': 8, 'requires_disjoint_screen_seeds': True, 'requires_passing_screen_assessment': True}, 'confirmation': {'minimum_seeds': 8, 'requires_disjoint_all_prior_stage_seeds': True, 'requires_passing_replication_assessment': True, 'requires_explicit_large_long_authorization': True}}
- large long required for exploration: False
- large long reserved for confirmation: True
- outcome-conditioned changes / feedback: False / False

## Group label

- schema: `trusted-directed-fixed-round-min-label-v1`
- threshold / rounds / minimum members: 0.12 / 8 / 6
- refresh mode: `adaptive-topology-v1`
- propagation: initialize label as physical slot index; for each fixed round, replace an entity label by the minimum of its current label and labels reachable through eligible outgoing relation slots
- token: stable entity ID at the propagated minimum root slot; components below minimum members receive token 0 and remain ungrouped
- boundary: finite-round directed minimum-label propagation is an approximate candidate-group measurement, not a subject-existence verdict

## Subject succession

- enabled / schema: True / `stable-membership-subject-succession-v1`
- identity key: stable entity ID membership
- transition rule: connect previous and current candidate groups when they share at least one stable entity ID; classify zero/one/multiple overlap relations as formation, persistence, split, merge, or dissolution
- boundary: membership succession among candidate social structures; not an ontological identity theorem, arbitrary nesting graph, or subjecthood score

## Spatial regions

- schema: `normalized-fixed-count-grid-v1`
- grid: 4 × 4 (16 regions)
- physical region: 48.0 × 48.0
- world cells per region: 12.0 × 12.0
- grid-aligned: True
- map-size semantics: fixed region counts over normalized coordinates; physical area and represented world-cell count scale with map dimensions and resolution

## Resource environment

- schema / channels: `orthogonal-four-resource-renewal-v2` / 4
- harvest allocation: `affinity-sampled-exclusive-harvest-v1`
- harvest budget semantics: fixed total extraction budget spent on one channel sampled from inherited affinity with state-free keyed randomness
- request observation: `explicit-requested-harvest-window-v1`; requested-before-allocation=True; realized-after-allocation=True; scale/composition separated=True
- independent cycle periods: [173, 257, 349, 431]
- primary wave vectors: [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, -1.0]]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]
- environment generation entity/lineage/group aware: False / False / False
- harvest demand phenotype-aware: True
- boundary: fixed four-channel physical interface with independently configured spatial, temporal, and diffusion dynamics; configuration can create environmental axes but does not guarantee evolved ecological differentiation

## Elastic capacities

- enabled / schema: True / `inherited-elastic-capacities-v1`
- physical maxima: {'working_memory_dimensions': 4, 'knowledge_bytes': 512, 'relation_slots': 8, 'knowledge_attention_slots': 2}
- effective bounds: {'working_memory_dimensions': [0, 4], 'knowledge_bytes': [0, 512], 'relation_slots': [0, 8], 'knowledge_attention_slots': [0, 2]}
- gene start/count: 535 / 4
- mutation probability/std: 0.03 / 0.16
- maintenance energy: {'per_working_memory_dimension': 1e-05, 'per_knowledge_byte': 1e-07, 'per_relation_slot': 5e-06, 'per_attention_slot': 1e-05}
- development energy: {'per_working_memory_dimension': 0.002, 'per_knowledge_byte': 1e-05, 'per_relation_slot': 0.001, 'per_attention_slot': 0.002}
- preset roles / diversity protection: False / False
- boundary: four inherited capacities alter the usable scale and explicit cost of existing memory, knowledge, relationship, and attention mechanisms; they do not add a predefined ecological role or guarantee adaptive differentiation

## D1 affinity × capacity factorial

- schema: `d1-affinity-capacity-factorial-plan-v1`
- branches: {'baseline': [], 'affinity-neutral': ['neutralize-resource-affinity'], 'capacity-neutral': ['neutralize-elastic-capacities'], 'combined-neutral': ['neutralize-resource-affinity', 'neutralize-elastic-capacities']}
- paired randomness / genotype preserved: True / True
- expression effect sign: expressed phenotype minus neutralized branch
- interaction contrast: baseline - affinity-neutral - capacity-neutral + combined-neutral
- boundary: local checkpoint-phase effects over a fixed horizon; not universal necessity

## D2-A contextual functional modules

- enabled / schema: True / `expression-gated-regulatory-resource-metabolism-v6`
- module count / gene start / gene count: 4 / 539 / 142
- architecture / coupling: feed-forward-regulatory-resource-metabolism / `lower-slot-signal-modulation-v1` / 6 links
- hierarchy: [0, 1, 2, 3]
- coupling semantics: lower-slot signals multiplicatively modulate downstream contextual activation; direct module routing remains available at every slot
- inputs: ['bias', 'energy deficit', 'integrity deficit', 'material deficit', 'information-store deficit', 'fertility deficit', 'four local normalized resource channels', 'oxygenation deficit', 'tissue deficit', 'structure deficit', 'metabolic fatigue', 'mobilization messenger', 'maintenance messenger', 'messenger precursor', 'local oxygen availability', 'local terrain resistance', 'local mechanical wear', 'four normalized internal raw-resource store occupancies']
- output scope: zero-sum harvest residual plus oxygen-uptake modulation, mobilization-bus stimulation, maintenance-bus stimulation, and sensory-attention modulation; actual execution emerges from inherited physiology, bounded state and abiotic supply
- action selection / new physics: False / True
- neutralization interventions: {'coupling_output': 'neutralize-functional-module-coupling-output', 'embodied_output': 'neutralize-functional-module-embodied-output', 'physiology_output': 'neutralize-functional-module-physiology-output', 'all_modules': 'neutralize-functional-modules', 'per_module': ['neutralize-functional-module-0', 'neutralize-functional-module-1', 'neutralize-functional-module-2', 'neutralize-functional-module-3']}
- contribution diagnostics: {'schema': 'functional-module-contribution-audit-v5', 'per_module_gate': True, 'per_module_activation': True, 'isolated_output_effect': True, 'contribution_effective_count': True, 'cancellation_fraction': True, 'coupling_weight_effective_dimensions': True, 'mediated_signal_by_hierarchy_level': True, 'amplification_and_suppression': True, 'embodied_output_effective_dimensions': False, 'combined_output_basis_effective_dimensions': True, 'physiology_output_effective_dimensions': True, 'feedback_to_world': False}
- architecture capability experiment: {'plan_schema': 'd2-compositional-capability-plan-v1', 'result_schema': 'd2-compositional-capability-results-v1', 'branches': ['composition-active', 'coupling-neutral'], 'same_v2_genome_and_mutation_streams': True, 'coupling_structure_cost_retained_in_neutral_branch': True, 'module_copy_number_changed': False, 'ecological_niche_claim': False}
- embodied capability experiment: {'plan_schema': 'd2-embodied-capability-plan-v1', 'result_schema': 'd2-embodied-capability-results-v1', 'branches': ['embodied-active', 'embodied-neutral'], 'same_v3_genome_and_mutation_streams': True, 'harvest_and_coupling_output_active_in_both_branches': True, 'embodied_router_structure_cost_retained_in_neutral_branch': True, 'module_copy_number_changed': False, 'ecological_niche_claim': False}
- embodied semantics: {'enabled': False, 'schema': 'harvest-regulatory-drive-v2', 'locomotion': 'bounded multiplier on existing movement speed with quadratic movement-energy accounting', 'field_signal': 'bounded multiplier on existing field-signal strength with quadratic signal-energy accounting', 'repair': 'positive drive converts explicitly debited material and energy into bounded integrity restoration', 'new_action_kind': False, 'resource_or_energy_created': False, 'preset_ecological_role': False}
- physiological semantics: {'enabled': False, 'body_state': ['oxygenation', 'tissue_condition', 'structure_condition'], 'module_drives': ['perfusion', 'contractile', 'sensory', 'repair'], 'abiotic_fields': ['oxygen availability', 'terrain resistance', 'mechanical wear'], 'derived_effects': ['locomotion', 'signal reception/emission', 'repair'], 'conservation': 'repair debits material, energy, and oxygen; damage changes tissue/structure/integrity', 'new_action_kind': False, 'biological_hazard_source': False, 'diversity_reward_or_protection': False, 'preset_ecological_role': False}
- physiological ecology experiment: {'plan_schema': 'd2-physiological-ecology-plan-v1', 'result_schema': 'd2-physiological-ecology-results-v1', 'single_active_population_per_seed': True, 'pass_fail_expression_gate': False, 'independent_abiotic_fields': True, 'dynamic_body_state': True, 'module_copy_number_changed': False, 'food_chain_complete': False, 'stable_niche_claim': False}
- regulatory physiology semantics: {'enabled': True, 'physiology_schema': 'transport-metabolism-messenger-tissue-resource-v7', 'inherited_parameter_count': 23, 'module_requests': ['oxygen uptake modulation', 'mobilization messenger stimulation', 'maintenance messenger stimulation', 'sensory attention modulation'], 'dynamic_states': ['oxygenation', 'tissue condition', 'structure condition', 'metabolic fatigue', 'mobilization messenger', 'maintenance messenger', 'shared messenger precursor'], 'intent_execution_separation': True, 'zero_module_output_semantics': 'basal uptake and attention with no stimulated messenger synthesis', 'messenger_buses': 'two independently inherited synthesis/decay/receptor pathways sharing one finite precursor pool', 'fixed_lifetime_weights': True, 'online_hebbian_learning': False, 'computation_cost': 'actual activation and route load debit energy and oxygen', 'conservative_flow_schema': 'transport-metabolism-messenger-tissue-v3', 'legacy_replay_schema': 'transport-metabolism-messenger-tissue-v2', 'flow_ledger_invariant': 'all reported flow magnitudes are finite and non-negative', 'energy_debt_semantics': 'physiology preserves negative energy until world starvation settlement', 'counterfactual_interfaces': ['regulatory output neutralization', 'messenger receptor blockade', 'bounded state clamp'], 'named_organs_or_hormones': False, 'conservation': 'messenger synthesis debits precursor and energy; precursor recovery debits material; repair debits material, energy and oxygen'}
- regulatory physiology experiment: {'plan_schema': 'd2-regulatory-physiology-plan-v2', 'result_schema': 'd2-regulatory-physiology-results-v2', 'legacy_result_schema_readable': 'd2-regulatory-physiology-results-v1', 'flow_assessment_schema': 'd2-regulatory-physiology-flow-assessment-v1', 'single_active_population_per_seed': True, 'pass_fail_expression_gate': False, 'fixed_lifetime_weights': True, 'finite_messenger_precursor': True, 'computation_and_execution_costed': True, 'module_copy_number_changed': False, 'stable_niche_claim': False}
- resource metabolism semantics: {'enabled': True, 'physiology_schema': 'transport-metabolism-messenger-tissue-resource-v7', 'functional_schema': 'expression-gated-regulatory-resource-metabolism-v6', 'raw_resource_channels': 4, 'inherited_store_capacity_genes': 4, 'inherited_conversion_capacity_genes': 4, 'base_store_capacity': [1.2, 1.2, 1.2, 1.2], 'base_conversion_per_tick': [0.04, 0.04, 0.04, 0.04], 'store_decay_per_tick': [0.002, 0.002, 0.002, 0.002], 'harvest_enters_store_before_body': True, 'minimum_conversion_delay_ticks': 1, 'same_tick_harvest_body_effect': False, 'resource_intake_schema': 'storage-room-constrained-preharvest-v2', 'storage_constrained_preharvest': True, 'capacity_rejected_resource_remains_external': True, 'policy_resource_utility_respects_store_room': True, 'legacy_post_harvest_overflow_replay': False, 'store_occupancy_visible_to_operators': True, 'external_recycling_enabled': True, 'external_recycling_schema': 'identity-preserving-spatial-residue-v1', 'death_store_fate': 'same-channel external residue deposition', 'store_decay_fate': 'same-channel external residue deposition', 'external_recycling_delay_ticks': 1, 'spatial_processing_enabled': True, 'spatial_processing_schema': 'phase-shifted-channel-processing-support-v1', 'spatial_processing_support_amplitude': 0.45, 'spatial_processing_energy_per_unit': [0.002, 0.002, 0.002, 0.002], 'spatial_processing_effect': 'multiply inherited per-channel conversion throughput after storage', 'spatial_processing_cost_timing': 'charged before body outcomes with energy-limited proportional scaling', 'spatial_processing_entity_lineage_group_feedback': False, 'external_residue_diffusion': 'reuse same-channel resource diffusion rate', 'external_residue_release': 'reuse same-channel store-decay rate and limit by resource-field room', 'ledger': 'stored = converted + decay + death loss + final living store; decay + death loss = residue deposited; deposited = released + final residue', 'equal_channel_base_parameters': True, 'persistent_resource_renewal_enabled': True, 'resource_renewal_schema': 'moving-target-source-sink-v2', 'resource_renewal_target_entity_feedback': False, 'resource_renewal_target_lineage_feedback': False, 'resource_renewal_open_system_fluxes': ['source', 'sink'], 'preset_resource_role': False, 'diversity_reward_or_protection': False}
- resource metabolism experiment: {'plan_schema': 'd3-resource-metabolism-plan-v1', 'result_schema': 'd3-resource-metabolism-results-v1', 'single_active_population_per_seed': True, 'pass_fail_module_gate': False, 'minimum_conversion_delay_ticks': 1, 'strict_raw_store_ledger': True, 'legacy_intake_semantics': 'post-harvest bounded storage with overflow loss', 'module_copy_number_changed': False, 'stable_niche_claim': False}
- conservative intake experiment: {'plan_schema': 'd3-conservative-intake-plan-v1', 'result_schema': 'd3-conservative-intake-results-v2', 'legacy_result_reassessment_schema': 'd3-conservative-intake-assessment-v1', 'overflow_zero_semantics': 'scale-aware floating-point tolerance', 'single_active_population_per_seed': True, 'pass_fail_module_gate': False, 'preharvest_request_capped_by_inherited_store_room': True, 'affinity_adjusted_capacity_in_raw_environment_units': True, 'capacity_rejected_resource_remains_external': True, 'post_assimilation_overflow_forbidden': True, 'policy_resource_utility_respects_store_room': True, 'strict_store_ledger': True, 'module_copy_number_changed': False, 'stable_niche_claim': False}
- external recycling experiment: {'plan_schema': 'd3-external-recycling-plan-v2', 'result_schema': 'd3-external-recycling-results-v2', 'float32_residue_inventory_roundoff_recorded_separately': True, 'single_active_population_per_seed': True, 'identity_preserving_channels': True, 'store_decay_and_death_store_sources': True, 'minimum_external_delay_ticks': 1, 'release_limited_by_resource_capacity': True, 'named_decomposer_or_scavenger_roles': False, 'stable_trophic_claim': False}
- persistent resource renewal experiment: {'plan_schema': 'd3-persistent-resource-renewal-plan-v3', 'result_schema': 'd3-persistent-resource-renewal-results-v3', 'single_active_population_per_seed': True, 'moving_target_reuses_role_free_channel_waves': True, 'source_and_sink_recorded_separately': True, 'float32_inventory_roundoff_recorded_separately': True, 'external_resource_ledger': 'initial + renewal source + residue release + field roundoff = harvest + renewal sink + final + harvest roundoff', 'entity_lineage_and_group_feedback': False, 'named_resource_roles': False, 'stable_niche_claim': False}
- spatial processing experiment: {'plan_schema': 'd3-spatial-collection-processing-plan-v2', 'result_schema': 'd3-spatial-collection-processing-results-v2', 'shared_checkpoint_tick': 0, 'paired_branches': ['spatial-support', 'neutral-support'], 'neutralization_intervention': 'neutralize-spatial-processing-support', 'processing_execution_cost_preserved_in_ablation': True, 'genotype_and_resource_fields_preserved_in_ablation': True, 'support_phase_relation': 'quarter-cycle-shifted-from-renewal-wave-basis', 'direct_action_or_harvest_reward': False, 'entity_lineage_and_group_feedback': False, 'named_resource_or_ecological_roles': False, 'stable_migration_or_ecotype_claim': False}
- spatial processing response audit: {'plan_schema': 'd3-spatial-processing-response-plan-v2', 'result_schema': 'd3-spatial-processing-response-results-v2', 'trajectory_schema': 'inventory-weighted-processing-response-trajectory-v1', 'shared_checkpoint_tick': 0, 'branches': ['original-support', 'reversed-support', 'neutral-support'], 'orientation_intervention': 'reverse-spatial-processing-support', 'neutralization_intervention': 'neutralize-spatial-processing-support', 'orientation_changes_only_nonmaterial_support_surface': True, 'processing_execution_cost_preserved_in_all_branches': True, 'genotype_resource_fields_and_residue_preserved': True, 'read_only_tick_observer': True, 'movement_reward_or_controller_added': False, 'support_sensor_added': False, 'measured_mediators': ['inventory-weighted support exposure', 'resource-move support gain against no-move counterfactual', 'resource-move alignment with local support gradient', 'store-support occupancy correlation'], 'finite_seed_signs_generalized': False, 'stable_migration_or_ecotype_claim': False}
- processing response scale audit: {'audit_schema': 'd3-response-scale-audit-v2', 'effect_inference_schema': 'nested-seed-checkpoint-matched-effect-inference-v1', 'supported_panel_result_schemas': ['d3-processing-response-panel-results-v1', 'd3-processing-response-panel-results-v2'], 'independent_replication_unit': 'seed-within-scale', 'checkpoints_within_seed': 'nested-repeated-panels', 'observation_windows_within_checkpoint': 'nested-repeated-measurements', 'checkpoint_weighting_within_seed': 'equal-checkpoint-v1', 'seed_weighting_within_scale': 'equal-seed-v1', 'movement_events_independent_replicates': False, 'matched_orientation_neutral_control_required': True, 'legacy_three_arm_reversed_effect_identified': False, 'default_minimum_independent_seeds': 8, 'default_minimum_positive_seed_fraction': 0.75, 'default_minimum_both_orientation_positive_seed_fraction': 0.75, 'exact_sign_flip_descriptive_only': True, 'sampling_or_replication_gate_feedback_to_world': False}
- processing response sample support: {'plan_schema': 'd3-processing-response-panel-plan-v2', 'result_schema': 'd3-processing-response-panel-results-v2', 'sample_schema': 'nested-seed-checkpoint-response-sampling-v1', 'source_trajectory': 'unintervened baseline to every predeclared checkpoint', 'branches': ['original-support', 'reversed-support', 'neutral-support', 'reversed-neutral-support'], 'matched_orientation_controls': {'original-support': 'neutral-support', 'reversed-support': 'reversed-neutral-support'}, 'float32_residue_inventory_roundoff_recorded_separately': True, 'default_response_window_ticks': 120, 'default_observation_period_ticks': 30, 'all_predeclared_checkpoints_retained': True, 'insufficient_or_unavailable_checkpoints_replaced': False, 'outcome_conditioned_checkpoint_selection': False, 'nested_independent_unit': 'seed/checkpoint', 'movement_events_independent_replicates': False, 'reported_sample_support': ['minimum alive and alive entity-ticks', 'inventory-eligible entity-ticks', 'resource movement count', 'unique entities', 'effective lineage entity-ticks', 'largest lineage entity-tick fraction', 'checkpoint births and generation depth'], 'acute_and_evolutionary_eligibility_separate': True, 'checkpoint_relative_resource_and_recycling_ledgers': True, 'sampling_gate_feedback_to_world': False, 'population_or_lineage_protection': False, 'stable_migration_or_ecotype_claim': False}
- known architecture limit: The v1 schema supports only independent additive harvest routing. The v2 schema adds inherited hierarchy and joint dependence; v3 adds conserved embodied ports. The archived v4 coarse-drive schema is retained for replay only. The v5 schema separates regulatory intent from inherited transport, metabolism, finite messenger turnover, fatigue and repair execution. The v6 functional / v4 physiology pair adds inherited bounded raw-resource storage and delayed conversion but retains archived post-harvest overflow loss. The v6 functional / v5 physiology pair constrains environmental extraction by inherited free store room before commit, so rejected raw resource remains external. Resource-v6 adds identity-preserving external residue recycling. The v2 orthogonal renewal schema keeps channel-specific moving source/sink opportunities active instead of using orthogonal geometry only at initialization. It still lacks explicit coupling between collection location and processing throughput, trophic transfer, a completed food chain, dynamic topology and stable niche proof.
- leave-one-out protocol: {'plan_schema': 'd2-module-leave-one-out-plan-v1', 'result_schema': 'd2-module-leave-one-out-results-v2', 'branches': ['baseline', 'all-modules-neutral', 'module-0-neutral', 'module-1-neutral', 'module-2-neutral', 'module-3-neutral'], 'paired_randomness': True, 'genotype_preserved': True, 'immediate_footprint': {'schema': 'd2-module-immediate-footprint-v1', 'conditional_action': 'HARVEST', 'pre_step': True, 'lineage_resolved': True, 'feedback_to_world': False}}
- effect qualification: {'schema': 'd2-module-effect-assessment-v2', 'numerical_tolerance': 1e-12, 'directional_replicates': 4, 'minimum_seeds': 2, 'footprint_preference_changed_fraction': 0.01, 'footprint_channel_changed_fraction': 0.005, 'minimum_lineage_members': 8, 'lineage_guard_effective_count': 4.0, 'duplication_requires': ['practical downstream magnitude', 'replication across at least two seeds', 'immediate checkpoint footprint', 'cross-lineage footprint', 'positive ecological persistence or preregistered phase tradeoff', 'no dominant-lineage guard failure']}
- lineage-balanced pairs: {'plan_schema': 'd2-lineage-paired-plan-v2', 'accepted_plan_schemas': ['d2-lineage-paired-plan-v1', 'd2-lineage-paired-plan-v2'], 'result_schema': 'd2-lineage-paired-results-v2', 'accepted_result_schemas': ['d2-lineage-paired-results-v1', 'd2-lineage-paired-results-v2'], 'default_priority_modules': [2, 3], 'selection_rule': 'largest pre-intervention lineages by membership', 'selection_uses_endpoint_response': False, 'branches': ['baseline', 'output-neutral with expression cost retained', 'expression-neutral with output and expression cost removed'], 'target_scope': 'one fixed module within one genetic lineage', 'same_lineage_descendants_treated': True, 'genotype_preserved': True, 'lineage_membership_preserved': True, 'paired_randomness': True, 'equal_inferential_weight_per_lineage_pair': True, 'abundance_reweighting_inside_world': False, 'diversity_protection': False, 'effect_assessment': {'schema': 'd2-lineage-paired-assessment-v1', 'continuation_effect': 'output_routing_effect', 'minimum_seeds': 2, 'minimum_non_dominant_lineage_identities': 2, 'same_material_direction_required': True, 'cost_only_signal_qualifies': False, 'confirmation_horizon_ticks': 300, 'confirmation_selection_rule': 'module-level-screen-preserve-all-preselected-checkpoint-lineage-pairs-v1', 'outcome_conditioned_pair_selection': False, 'copy_number_remains_guarded': True}, 'temporal_mediation_audit': {'plan_schema': 'd2-lineage-mediation-plan-v1', 'result_schema': 'd2-lineage-mediation-results-v1', 'assessment_schema': 'd2-lineage-mediation-assessment-v1', 'selection_rule': 'module-level-confirmed-output-preserve-all-preselected-checkpoint-lineage-pairs-v1', 'default_observation_offsets': [30, 60, 120, 180, 240, 300], 'branches': ['baseline', 'output-neutral with expression cost retained', 'expression-neutral with output and expression cost removed'], 'read_only_tick_observer': True, 'measured_mediators': ['target-lineage energy stock and quartiles', 'source survivors and living descendants', 'births and deaths by cause', 'fertility and reproduction readiness', 'post-intervention harvested energy', 'post-intervention shared energy received'], 'offsets_are_independent_replicates': False, 'minimum_seeds_per_offset': 2, 'minimum_non_dominant_lineage_identities_per_offset': 2, 'mean_energy_alone_qualifies_as_ecological_benefit': False, 'outcome_conditioned_pair_selection': False, 'copy_number_remains_guarded': True}, 'source_population_reconstitution': {'plan_schema': 'd2-source-population-plan-v1', 'result_schema': 'd2-source-population-results-v1', 'assessment_schema': 'd2-source-population-assessment-v2', 'arms': ['natural-abundance-control', 'equal-lineage-reconstitution'], 'selection_rule': 'cross-run top pre-intervention lineages by abundance; no response-conditioned lineage selection', 'founder_transfer': 'genotype only from unique living donors without replacement', 'reset_state': ['physiology', 'age and generation', 'knowledge', 'social state', 'spatial position'], 'same_total_founders_across_arms': True, 'ongoing_lineage_protection': False, 'lineage_aware_world_rules': False, 'module_copy_number_changed': False, 'qualification': {'minimum_effective_lineages': 4.0, 'maximum_dominant_lineage_fraction': 0.5, 'minimum_lineages_above_member_floor': 4, 'minimum_expressed_lineages_per_candidate_module': 4, 'minimum_observed_panel_seeds_for_exploratory_decision': 3, 'minimum_qualified_panel_seeds_per_exploratory_phase': 2, 'major_conclusion_minimum_seeds_per_phase': 10, 'uncertainty_interval': 'two-sided-wilson-95-v1'}, 'charter_interpretation': {'ten_seed_floor_applies_to_major_conclusions': True, 'ten_seed_floor_applies_to_every_exploratory_audit': False, 'three_seed_paired_gate_allowed': True}, 'copy_number_remains_guarded': True}, 'source_population_causal_reaudit': {'plan_schema': 'd2-source-population-causal-plan-v1', 'result_schema': 'd2-source-population-causal-results-v1', 'assessment_schema': 'd2-source-population-causal-assessment-v1', 'module_indices': [3], 'default_screen_horizon_ticks': 120, 'confirmation_horizon_ticks': 300, 'checkpoint_selection': 'phase-qualified equal-lineage final checkpoints only', 'lineage_selection': 'all lineages passing preregistered member and expression floors', 'branches': ['baseline', 'output-neutral with expression cost retained', 'expression-neutral with output and expression cost removed'], 'response_conditioned_panel_selection': False, 'response_conditioned_lineage_selection': False, 'general_source_population_claim': False, 'module_copy_number_changed': False, 'copy_number_remains_guarded': True}}
- boundary: a bounded D2-A test of inherited input-expression-output routing within the already validated resource-acquisition interface; not a general organ generator or a claim of new physical functionality

## D4-A resource geography × inherited affinity reversal

- plan / result / assessment: `d4-niche-reversal-plan-v1` / `d4-niche-reversal-results-v1` / `d4-niche-reversal-assessment-v2`
- source gate: explicit D2-H non-replication stop recommendation
- branches: {'baseline': [], 'resource-reversed': ['reverse-resource-geography'], 'affinity-neutral': ['neutralize-resource-affinity'], 'joint-neutral': ['reverse-resource-geography', 'neutralize-resource-affinity']}
- interaction: (baseline - resource-reversed) - (affinity-neutral - joint-neutral)
- resource reversal: {'rotation_degrees': 180, 'current_resource_fields_rotated': True, 'future_seasonal_template_rotated': True, 'resource_identity_changed': False, 'resource_effect_matrix_changed': False, 'hazard_changed': False, 'mortality_trace_changed': False}
- paired randomness / genotype / lineage preserved: True / True / True
- source exposure: pre-intervention affinity-specific utility difference between original and 180-degree-rotated resource geography
- niche claim requires: ['persistent environment-matching interaction', 'stable coexistence', 'ecotype or phenotype-cohort removal', 'map-scale and spatial-template checks']

## Environment atlas

- enabled / schema: True / `multiscale-subject-environment-atlas-v2`
- scales: 2×2, 4×4, 8×8
- signature: four capacity-normalized resource means, hazard mean, mortality-trace mean
- resource-only metrics: resource effective dimensions, resource channel correlation matrix, mean/max absolute resource channel correlation
- subject exposure: between-label share of realized regional signature variance for genetic lineages and observed social groups
- boundary: descriptive multiscale environment heterogeneity and exposure segregation; not environmental causation or subjecthood
