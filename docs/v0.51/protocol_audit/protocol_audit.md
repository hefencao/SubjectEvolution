# Structural measurement protocol audit

Schema: `structural-measurement-protocol-audit-v19`
Audit SHA-256: `d55d891a369570733650f4f9efa73502e05c0aeaa26b5f474c3e815a3f47199a`

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
- physical region: 32.0 × 32.0
- world cells per region: 8.0 × 8.0
- grid-aligned: True
- map-size semantics: fixed region counts over normalized coordinates; physical area and represented world-cell count scale with map dimensions and resolution

## Resource environment

- schema / channels: `orthogonal-four-resource-niche-v1` / 4
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

- enabled / schema: True / `expression-gated-regulatory-physiology-v5`
- module count / gene start / gene count: 4 / 539 / 126
- architecture / coupling: feed-forward-regulatory-physiology / `lower-slot-signal-modulation-v1` / 6 links
- hierarchy: [0, 1, 2, 3]
- coupling semantics: lower-slot signals multiplicatively modulate downstream contextual activation; direct module routing remains available at every slot
- inputs: ['bias', 'energy deficit', 'integrity deficit', 'material deficit', 'information-store deficit', 'fertility deficit', 'four local normalized resource channels', 'oxygenation deficit', 'tissue deficit', 'structure deficit', 'metabolic fatigue', 'mobilization messenger', 'maintenance messenger', 'messenger precursor', 'local oxygen availability', 'local terrain resistance', 'local mechanical wear']
- output scope: zero-sum harvest residual plus oxygen-uptake modulation, mobilization-bus stimulation, maintenance-bus stimulation, and sensory-attention modulation; actual execution emerges from inherited physiology, bounded state and abiotic supply
- action selection / new physics: False / True
- neutralization interventions: {'coupling_output': 'neutralize-functional-module-coupling-output', 'embodied_output': 'neutralize-functional-module-embodied-output', 'physiology_output': 'neutralize-functional-module-physiology-output', 'all_modules': 'neutralize-functional-modules', 'per_module': ['neutralize-functional-module-0', 'neutralize-functional-module-1', 'neutralize-functional-module-2', 'neutralize-functional-module-3']}
- contribution diagnostics: {'schema': 'functional-module-contribution-audit-v5', 'per_module_gate': True, 'per_module_activation': True, 'isolated_output_effect': True, 'contribution_effective_count': True, 'cancellation_fraction': True, 'coupling_weight_effective_dimensions': True, 'mediated_signal_by_hierarchy_level': True, 'amplification_and_suppression': True, 'embodied_output_effective_dimensions': False, 'combined_output_basis_effective_dimensions': True, 'physiology_output_effective_dimensions': True, 'feedback_to_world': False}
- architecture capability experiment: {'plan_schema': 'd2-compositional-capability-plan-v1', 'result_schema': 'd2-compositional-capability-results-v1', 'branches': ['composition-active', 'coupling-neutral'], 'same_v2_genome_and_mutation_streams': True, 'coupling_structure_cost_retained_in_neutral_branch': True, 'module_copy_number_changed': False, 'ecological_niche_claim': False}
- embodied capability experiment: {'plan_schema': 'd2-embodied-capability-plan-v1', 'result_schema': 'd2-embodied-capability-results-v1', 'branches': ['embodied-active', 'embodied-neutral'], 'same_v3_genome_and_mutation_streams': True, 'harvest_and_coupling_output_active_in_both_branches': True, 'embodied_router_structure_cost_retained_in_neutral_branch': True, 'module_copy_number_changed': False, 'ecological_niche_claim': False}
- embodied semantics: {'enabled': False, 'schema': 'harvest-regulatory-drive-v2', 'locomotion': 'bounded multiplier on existing movement speed with quadratic movement-energy accounting', 'field_signal': 'bounded multiplier on existing field-signal strength with quadratic signal-energy accounting', 'repair': 'positive drive converts explicitly debited material and energy into bounded integrity restoration', 'new_action_kind': False, 'resource_or_energy_created': False, 'preset_ecological_role': False}
- physiological semantics: {'enabled': False, 'body_state': ['oxygenation', 'tissue_condition', 'structure_condition'], 'module_drives': ['perfusion', 'contractile', 'sensory', 'repair'], 'abiotic_fields': ['oxygen availability', 'terrain resistance', 'mechanical wear'], 'derived_effects': ['locomotion', 'signal reception/emission', 'repair'], 'conservation': 'repair debits material, energy, and oxygen; damage changes tissue/structure/integrity', 'new_action_kind': False, 'biological_hazard_source': False, 'diversity_reward_or_protection': False, 'preset_ecological_role': False}
- physiological ecology experiment: {'plan_schema': 'd2-physiological-ecology-plan-v1', 'result_schema': 'd2-physiological-ecology-results-v1', 'single_active_population_per_seed': True, 'pass_fail_expression_gate': False, 'independent_abiotic_fields': True, 'dynamic_body_state': True, 'module_copy_number_changed': False, 'food_chain_complete': False, 'stable_niche_claim': False}
- regulatory physiology semantics: {'enabled': True, 'physiology_schema': 'transport-metabolism-messenger-tissue-v2', 'inherited_parameter_count': 15, 'module_requests': ['oxygen uptake modulation', 'mobilization messenger stimulation', 'maintenance messenger stimulation', 'sensory attention modulation'], 'dynamic_states': ['oxygenation', 'tissue condition', 'structure condition', 'metabolic fatigue', 'mobilization messenger', 'maintenance messenger', 'shared messenger precursor'], 'intent_execution_separation': True, 'zero_module_output_semantics': 'basal uptake and attention with no stimulated messenger synthesis', 'messenger_buses': 'two independently inherited synthesis/decay/receptor pathways sharing one finite precursor pool', 'fixed_lifetime_weights': True, 'online_hebbian_learning': False, 'computation_cost': 'actual activation and route load debit energy and oxygen', 'counterfactual_interfaces': ['regulatory output neutralization', 'messenger receptor blockade', 'bounded state clamp'], 'named_organs_or_hormones': False, 'conservation': 'messenger synthesis debits precursor and energy; precursor recovery debits material; repair debits material, energy and oxygen'}
- regulatory physiology experiment: {'plan_schema': 'd2-regulatory-physiology-plan-v1', 'result_schema': 'd2-regulatory-physiology-results-v1', 'single_active_population_per_seed': True, 'pass_fail_expression_gate': False, 'fixed_lifetime_weights': True, 'finite_messenger_precursor': True, 'computation_and_execution_costed': True, 'module_copy_number_changed': False, 'stable_niche_claim': False}
- known architecture limit: The v1 schema supports only independent additive harvest routing. The v2 schema adds inherited hierarchy and joint dependence; v3 adds conserved embodied ports. The archived v4 coarse-drive schema is retained for replay only. The v5 schema separates regulatory intent from inherited transport, metabolism, finite messenger turnover, fatigue and repair execution. It still uses a fixed bounded kernel and lacks a completed trophic chain, dynamic topology and stable niche proof.
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
