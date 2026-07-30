# Structural measurement protocol audit

Schema: `structural-measurement-protocol-audit-v13`
Audit SHA-256: `078be9c67efe21b94b3c11e5bfc4b881225bef06e8205961ea2ef0ae5587203a`

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

- enabled / schema: True / `expression-gated-contextual-harvest-v1`
- module count / gene start: 4 / 539
- inputs: ['bias', 'energy deficit', 'integrity deficit', 'material deficit', 'information-store deficit', 'fertility deficit', 'four local normalized resource channels']
- output scope: zero-sum residual over four harvest-channel request weights
- action selection / new physics: False / False
- neutralization interventions: {'all_modules': 'neutralize-functional-modules', 'per_module': ['neutralize-functional-module-0', 'neutralize-functional-module-1', 'neutralize-functional-module-2', 'neutralize-functional-module-3']}
- contribution diagnostics: {'schema': 'functional-module-contribution-audit-v1', 'per_module_gate': True, 'per_module_activation': True, 'isolated_output_effect': True, 'contribution_effective_count': True, 'cancellation_fraction': True, 'feedback_to_world': False}
- leave-one-out protocol: {'plan_schema': 'd2-module-leave-one-out-plan-v1', 'result_schema': 'd2-module-leave-one-out-results-v2', 'branches': ['baseline', 'all-modules-neutral', 'module-0-neutral', 'module-1-neutral', 'module-2-neutral', 'module-3-neutral'], 'paired_randomness': True, 'genotype_preserved': True, 'immediate_footprint': {'schema': 'd2-module-immediate-footprint-v1', 'conditional_action': 'HARVEST', 'pre_step': True, 'lineage_resolved': True, 'feedback_to_world': False}}
- effect qualification: {'schema': 'd2-module-effect-assessment-v2', 'numerical_tolerance': 1e-12, 'directional_replicates': 4, 'minimum_seeds': 2, 'footprint_preference_changed_fraction': 0.01, 'footprint_channel_changed_fraction': 0.005, 'minimum_lineage_members': 8, 'lineage_guard_effective_count': 4.0, 'duplication_requires': ['practical downstream magnitude', 'replication across at least two seeds', 'immediate checkpoint footprint', 'cross-lineage footprint', 'positive ecological persistence or preregistered phase tradeoff', 'no dominant-lineage guard failure']}
- lineage-balanced pairs: {'plan_schema': 'd2-lineage-paired-plan-v2', 'accepted_plan_schemas': ['d2-lineage-paired-plan-v1', 'd2-lineage-paired-plan-v2'], 'result_schema': 'd2-lineage-paired-results-v2', 'accepted_result_schemas': ['d2-lineage-paired-results-v1', 'd2-lineage-paired-results-v2'], 'default_priority_modules': [2, 3], 'selection_rule': 'largest pre-intervention lineages by membership', 'selection_uses_endpoint_response': False, 'branches': ['baseline', 'output-neutral with expression cost retained', 'expression-neutral with output and expression cost removed'], 'target_scope': 'one fixed module within one genetic lineage', 'same_lineage_descendants_treated': True, 'genotype_preserved': True, 'lineage_membership_preserved': True, 'paired_randomness': True, 'equal_inferential_weight_per_lineage_pair': True, 'abundance_reweighting_inside_world': False, 'diversity_protection': False, 'effect_assessment': {'schema': 'd2-lineage-paired-assessment-v1', 'continuation_effect': 'output_routing_effect', 'minimum_seeds': 2, 'minimum_non_dominant_lineage_identities': 2, 'same_material_direction_required': True, 'cost_only_signal_qualifies': False, 'confirmation_horizon_ticks': 300, 'confirmation_selection_rule': 'module-level-screen-preserve-all-preselected-checkpoint-lineage-pairs-v1', 'outcome_conditioned_pair_selection': False, 'copy_number_remains_guarded': True}, 'temporal_mediation_audit': {'plan_schema': 'd2-lineage-mediation-plan-v1', 'result_schema': 'd2-lineage-mediation-results-v1', 'assessment_schema': 'd2-lineage-mediation-assessment-v1', 'selection_rule': 'module-level-confirmed-output-preserve-all-preselected-checkpoint-lineage-pairs-v1', 'default_observation_offsets': [30, 60, 120, 180, 240, 300], 'branches': ['baseline', 'output-neutral with expression cost retained', 'expression-neutral with output and expression cost removed'], 'read_only_tick_observer': True, 'measured_mediators': ['target-lineage energy stock and quartiles', 'source survivors and living descendants', 'births and deaths by cause', 'fertility and reproduction readiness', 'post-intervention harvested energy', 'post-intervention shared energy received'], 'offsets_are_independent_replicates': False, 'minimum_seeds_per_offset': 2, 'minimum_non_dominant_lineage_identities_per_offset': 2, 'mean_energy_alone_qualifies_as_ecological_benefit': False, 'outcome_conditioned_pair_selection': False, 'copy_number_remains_guarded': True}, 'source_population_reconstitution': {'plan_schema': 'd2-source-population-plan-v1', 'result_schema': 'd2-source-population-results-v1', 'assessment_schema': 'd2-source-population-assessment-v1', 'arms': ['natural-abundance-control', 'equal-lineage-reconstitution'], 'selection_rule': 'cross-run top pre-intervention lineages by abundance; no response-conditioned lineage selection', 'founder_transfer': 'genotype only from unique living donors without replacement', 'reset_state': ['physiology', 'age and generation', 'knowledge', 'social state', 'spatial position'], 'same_total_founders_across_arms': True, 'ongoing_lineage_protection': False, 'lineage_aware_world_rules': False, 'module_copy_number_changed': False, 'qualification': {'minimum_effective_lineages': 4.0, 'maximum_dominant_lineage_fraction': 0.5, 'minimum_lineages_above_member_floor': 4, 'minimum_expressed_lineages_per_candidate_module': 4, 'minimum_qualified_panel_seeds_per_phase': 2, 'minimum_qualified_phases': 2}, 'copy_number_remains_guarded': True}}
- boundary: a bounded D2-A test of inherited input-expression-output routing within the already validated resource-acquisition interface; not a general organ generator or a claim of new physical functionality

## Environment atlas

- enabled / schema: True / `multiscale-subject-environment-atlas-v2`
- scales: 2×2, 4×4, 8×8
- signature: four capacity-normalized resource means, hazard mean, mortality-trace mean
- resource-only metrics: resource effective dimensions, resource channel correlation matrix, mean/max absolute resource channel correlation
- subject exposure: between-label share of realized regional signature variance for genetic lineages and observed social groups
- boundary: descriptive multiscale environment heterogeneity and exposure segregation; not environmental causation or subjecthood
