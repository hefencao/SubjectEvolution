# Multi-seed long-run analysis

Schema: `multi-seed-long-run-analysis-v7`
Runs: **3**

> This report is observational. Raw correlations, first differences and partial correlations do not identify an in-world causal mechanism.

| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Affinity dims | Transfer commits | Transferred roots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| seed_10001 | 1500 | 1360 | 15.7770 | 0.1618 | 14.0074 | 1.7361 | 0.2647 | 2.7623 | 12166 | 2011.2152 |
| seed_10002 | 1500 | 1352 | 21.0734 | 0.1154 | 19.4264 | 1.7472 | 0.3711 | 2.4215 | 12460 | 2051.1186 |
| seed_10003 | 1500 | 1328 | 21.3029 | 0.1318 | 18.8021 | 1.7355 | 0.3362 | 2.2760 | 14168 | 2183.6257 |

## Within-run raw observational correlations

### seed_10001
- `mortality_vs_same_window_cohesion`: 0.5829
- `mortality_vs_next_window_cohesion`: 0.6384
- `effective_lineages_vs_cohesion`: -0.7981
- `largest_lineage_fraction_vs_cohesion`: 0.3537
- `strategy_dimensions_vs_action_entropy`: 0.9760
- `lineage_group_nmi_vs_cohesion`: 0.5472
- `lineage_group_pair_enrichment_vs_cohesion`: -0.1412
- `knowledge_effective_roots_vs_effective_lineages`: -0.2888

### seed_10002
- `mortality_vs_same_window_cohesion`: 0.3756
- `mortality_vs_next_window_cohesion`: 0.4079
- `effective_lineages_vs_cohesion`: -0.9154
- `largest_lineage_fraction_vs_cohesion`: 0.8044
- `strategy_dimensions_vs_action_entropy`: 0.9830
- `lineage_group_nmi_vs_cohesion`: 0.4801
- `lineage_group_pair_enrichment_vs_cohesion`: -0.1997
- `knowledge_effective_roots_vs_effective_lineages`: -0.2652

### seed_10003
- `mortality_vs_same_window_cohesion`: 0.5005
- `mortality_vs_next_window_cohesion`: 0.5600
- `effective_lineages_vs_cohesion`: -0.8849
- `largest_lineage_fraction_vs_cohesion`: 0.6984
- `strategy_dimensions_vs_action_entropy`: 0.9774
- `lineage_group_nmi_vs_cohesion`: 0.6098
- `lineage_group_pair_enrichment_vs_cohesion`: 0.0411
- `knowledge_effective_roots_vs_effective_lineages`: -0.2663

## First-difference checks

### seed_10001
- `delta_mortality_vs_delta_cohesion`: -0.0043
- `mortality_vs_next_delta_cohesion`: -0.0058
- `delta_effective_lineages_vs_delta_cohesion`: -0.2827
- `delta_largest_lineage_fraction_vs_delta_cohesion`: -0.0396
- `delta_strategy_dimensions_vs_delta_action_entropy`: 0.0549
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: 0.3360

### seed_10002
- `delta_mortality_vs_delta_cohesion`: -0.0892
- `mortality_vs_next_delta_cohesion`: -0.0222
- `delta_effective_lineages_vs_delta_cohesion`: -0.1912
- `delta_largest_lineage_fraction_vs_delta_cohesion`: 0.1669
- `delta_strategy_dimensions_vs_delta_action_entropy`: 0.3569
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: 0.4324

### seed_10003
- `delta_mortality_vs_delta_cohesion`: -0.1033
- `mortality_vs_next_delta_cohesion`: -0.0071
- `delta_effective_lineages_vs_delta_cohesion`: -0.1765
- `delta_largest_lineage_fraction_vs_delta_cohesion`: 0.1023
- `delta_strategy_dimensions_vs_delta_action_entropy`: 0.2867
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: 0.4483

## Partial correlations controlling tick and alive

### seed_10001
- `mortality_vs_cohesion_controlling_tick_alive`: 0.5520
- `effective_lineages_vs_cohesion_controlling_tick_alive`: -0.8480
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: -0.7915
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: -0.0242
- strongest mortality→cohesion cross-lag: lag `3` windows, r=0.6661

### seed_10002
- `mortality_vs_cohesion_controlling_tick_alive`: 0.3592
- `effective_lineages_vs_cohesion_controlling_tick_alive`: -0.7980
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: 0.7400
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: 0.1016
- strongest mortality→cohesion cross-lag: lag `2` windows, r=0.4260

### seed_10003
- `mortality_vs_cohesion_controlling_tick_alive`: 0.4863
- `effective_lineages_vs_cohesion_controlling_tick_alive`: -0.6917
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: 0.1441
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: 0.3690
- strongest mortality→cohesion cross-lag: lag `1` windows, r=0.5600

## Costed cultural transfer

### seed_10001
- proposals / admitted attempts / committed / bytes: 14564 / 14499 / 12166 / 697888
- committed cross-lineage / cross-group: 8788 / 1429
- active/effective transferred roots: 2408 / 2011.2152
- cultural-spread interpretable: True

### seed_10002
- proposals / admitted attempts / committed / bytes: 14983 / 14907 / 12460 / 713504
- committed cross-lineage / cross-group: 8633 / 1359
- active/effective transferred roots: 2538 / 2051.1186
- cultural-spread interpretable: True

### seed_10003
- proposals / admitted attempts / committed / bytes: 16991 / 16906 / 14168 / 815120
- committed cross-lineage / cross-group: 9928 / 1507
- active/effective transferred roots: 2709 / 2183.6257
- cultural-spread interpretable: True

## Environment process, danger evidence, mortality trace and group refresh

### seed_10001
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.012774 / 0.253983
- group refresh mode / updates / skipped: adaptive-topology-v1 / 15 / 1485

### seed_10002
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.011962 / 0.260144
- group refresh mode / updates / skipped: adaptive-topology-v1 / 15 / 1485

### seed_10003
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.010825 / 0.138970
- group refresh mode / updates / skipped: adaptive-topology-v1 / 15 / 1485

## Execution backend context

- `seed_10001`: requested=gpu, execution=gpu-strict-reference, gpu_semantics=strict-reference, device_validated=True, acceleration=False
- `seed_10002`: requested=gpu, execution=gpu-strict-reference, gpu_semantics=strict-reference, device_validated=True, acceleration=False
- `seed_10003`: requested=gpu, execution=gpu-strict-reference, gpu_semantics=strict-reference, device_validated=True, acceleration=False

## Local spatial stress panel

### seed_10001
- windows / regions: 50 / 16
- mean population / mortality / scarcity / cohesion CV: 0.1280 / 0.6511 / 0.0165 / 0.3239
- max local/global mortality ratio: 5.8852
- within_region_correlations:
  - `local_mortality_vs_cohesion_within_region`: 0.1421
  - `local_scarcity_vs_cohesion_within_region`: 0.3263
  - `local_hazard_vs_cohesion_within_region`: 0.0317
  - `local_crowding_vs_cohesion_within_region`: -0.3336
  - `local_population_change_vs_cohesion_within_region`: -0.1538
- within_window_correlations:
  - `local_mortality_vs_cohesion_within_window`: 0.0265
  - `local_scarcity_vs_cohesion_within_window`: -0.0611
  - `local_hazard_vs_cohesion_within_window`: 0.0363
  - `local_crowding_vs_cohesion_within_window`: -0.1584
  - `local_population_change_vs_cohesion_within_window`: -0.0608
- first_difference_correlations:
  - `delta_local_mortality_vs_delta_local_cohesion`: 0.0182
  - `delta_local_scarcity_vs_delta_local_cohesion`: -0.0093
  - `delta_local_hazard_vs_delta_local_cohesion`: 0.0244
  - `delta_local_crowding_vs_delta_local_cohesion`: -0.0934
  - `delta_local_population_change_vs_delta_local_cohesion`: -0.0648
- next_window_correlations:
  - `local_mortality_vs_next_window_local_cohesion`: 0.1957
  - `local_scarcity_vs_next_window_local_cohesion`: 0.3259
  - `local_hazard_vs_next_window_local_cohesion`: 0.0517
  - `local_crowding_vs_next_window_local_cohesion`: -0.2640
  - `local_population_change_vs_next_window_local_cohesion`: -0.2732

### seed_10002
- windows / regions: 50 / 16
- mean population / mortality / scarcity / cohesion CV: 0.1361 / 0.6647 / 0.0159 / 0.3332
- max local/global mortality ratio: 7.3646
- within_region_correlations:
  - `local_mortality_vs_cohesion_within_region`: 0.0390
  - `local_scarcity_vs_cohesion_within_region`: 0.3609
  - `local_hazard_vs_cohesion_within_region`: -0.0187
  - `local_crowding_vs_cohesion_within_region`: -0.3915
  - `local_population_change_vs_cohesion_within_region`: -0.1142
- within_window_correlations:
  - `local_mortality_vs_cohesion_within_window`: -0.0388
  - `local_scarcity_vs_cohesion_within_window`: 0.0807
  - `local_hazard_vs_cohesion_within_window`: -0.0443
  - `local_crowding_vs_cohesion_within_window`: -0.0453
  - `local_population_change_vs_cohesion_within_window`: -0.0478
- first_difference_correlations:
  - `delta_local_mortality_vs_delta_local_cohesion`: 0.0027
  - `delta_local_scarcity_vs_delta_local_cohesion`: 0.0142
  - `delta_local_hazard_vs_delta_local_cohesion`: -0.0132
  - `delta_local_crowding_vs_delta_local_cohesion`: -0.0764
  - `delta_local_population_change_vs_delta_local_cohesion`: -0.0234
- next_window_correlations:
  - `local_mortality_vs_next_window_local_cohesion`: 0.0511
  - `local_scarcity_vs_next_window_local_cohesion`: 0.3512
  - `local_hazard_vs_next_window_local_cohesion`: 0.0210
  - `local_crowding_vs_next_window_local_cohesion`: -0.2886
  - `local_population_change_vs_next_window_local_cohesion`: -0.2192

### seed_10003
- windows / regions: 50 / 16
- mean population / mortality / scarcity / cohesion CV: 0.1337 / 0.6349 / 0.0155 / 0.3161
- max local/global mortality ratio: 4.9144
- within_region_correlations:
  - `local_mortality_vs_cohesion_within_region`: 0.0987
  - `local_scarcity_vs_cohesion_within_region`: 0.3505
  - `local_hazard_vs_cohesion_within_region`: 0.0316
  - `local_crowding_vs_cohesion_within_region`: -0.3438
  - `local_population_change_vs_cohesion_within_region`: -0.1238
- within_window_correlations:
  - `local_mortality_vs_cohesion_within_window`: -0.0555
  - `local_scarcity_vs_cohesion_within_window`: 0.0254
  - `local_hazard_vs_cohesion_within_window`: 0.0372
  - `local_crowding_vs_cohesion_within_window`: -0.1119
  - `local_population_change_vs_cohesion_within_window`: -0.0553
- first_difference_correlations:
  - `delta_local_mortality_vs_delta_local_cohesion`: 0.0212
  - `delta_local_scarcity_vs_delta_local_cohesion`: 0.0084
  - `delta_local_hazard_vs_delta_local_cohesion`: 0.0464
  - `delta_local_crowding_vs_delta_local_cohesion`: -0.0926
  - `delta_local_population_change_vs_delta_local_cohesion`: -0.0428
- next_window_correlations:
  - `local_mortality_vs_next_window_local_cohesion`: 0.0626
  - `local_scarcity_vs_next_window_local_cohesion`: 0.3329
  - `local_hazard_vs_next_window_local_cohesion`: 0.0216
  - `local_crowding_vs_next_window_local_cohesion`: -0.2574
  - `local_population_change_vs_next_window_local_cohesion`: -0.2208

## Local cultural transfer panel

### seed_10001
- same/cross-region commits: 10022 / 2144
- final active/multi-region transferred roots: 2408 / 152
- selected correlations:
  - `local_scarcity_vs_local_outgoing_transfer_rate_within_region`: 0.0127
  - `local_scarcity_vs_local_outgoing_transfer_rate_next_window`: -0.0673
  - `local_scarcity_vs_local_incoming_transfer_rate_within_region`: -0.0025
  - `local_scarcity_vs_local_incoming_transfer_rate_next_window`: -0.0813
  - `local_scarcity_vs_local_new_transferred_roots_within_region`: 0.3569
  - `local_scarcity_vs_local_new_transferred_roots_next_window`: 0.2452
  - `local_scarcity_vs_local_net_transferred_root_establishment_within_region`: -0.1943
  - `local_scarcity_vs_local_net_transferred_root_establishment_next_window`: -0.2418
  - `local_cohesion_vs_local_same_region_transfer_retention_within_region`: 0.0426
  - `local_cohesion_vs_local_same_region_transfer_retention_next_window`: 0.0238
  - `local_crowding_vs_local_outgoing_transfer_rate_within_region`: 0.4819
  - `local_crowding_vs_local_outgoing_transfer_rate_next_window`: 0.4084
  - `local_mortality_vs_local_incoming_transfer_rate_within_region`: 0.1942
  - `local_mortality_vs_local_incoming_transfer_rate_next_window`: 0.1047
- high_scarcity_event_study: 71 events
  - cohesion post1-pre1: 0.0147
- high_crowding_event_study: 53 events
  - cohesion post1-pre1: 0.0100
- high_mortality_event_study: 97 events
  - cohesion post1-pre1: 0.0226

### seed_10002
- same/cross-region commits: 10393 / 2067
- final active/multi-region transferred roots: 2538 / 189
- selected correlations:
  - `local_scarcity_vs_local_outgoing_transfer_rate_within_region`: 0.0574
  - `local_scarcity_vs_local_outgoing_transfer_rate_next_window`: -0.0372
  - `local_scarcity_vs_local_incoming_transfer_rate_within_region`: 0.0574
  - `local_scarcity_vs_local_incoming_transfer_rate_next_window`: -0.0358
  - `local_scarcity_vs_local_new_transferred_roots_within_region`: 0.3787
  - `local_scarcity_vs_local_new_transferred_roots_next_window`: 0.2614
  - `local_scarcity_vs_local_net_transferred_root_establishment_within_region`: -0.1803
  - `local_scarcity_vs_local_net_transferred_root_establishment_next_window`: -0.2300
  - `local_cohesion_vs_local_same_region_transfer_retention_within_region`: -0.0528
  - `local_cohesion_vs_local_same_region_transfer_retention_next_window`: -0.0020
  - `local_crowding_vs_local_outgoing_transfer_rate_within_region`: 0.3682
  - `local_crowding_vs_local_outgoing_transfer_rate_next_window`: 0.2915
  - `local_mortality_vs_local_incoming_transfer_rate_within_region`: 0.2059
  - `local_mortality_vs_local_incoming_transfer_rate_next_window`: 0.0682
- high_scarcity_event_study: 65 events
  - cohesion post1-pre1: 0.0217
- high_crowding_event_study: 47 events
  - cohesion post1-pre1: 0.0209
- high_mortality_event_study: 98 events
  - cohesion post1-pre1: 0.0071

### seed_10003
- same/cross-region commits: 11788 / 2380
- final active/multi-region transferred roots: 2709 / 199
- selected correlations:
  - `local_scarcity_vs_local_outgoing_transfer_rate_within_region`: 0.1687
  - `local_scarcity_vs_local_outgoing_transfer_rate_next_window`: 0.0504
  - `local_scarcity_vs_local_incoming_transfer_rate_within_region`: 0.1602
  - `local_scarcity_vs_local_incoming_transfer_rate_next_window`: 0.0464
  - `local_scarcity_vs_local_new_transferred_roots_within_region`: 0.3825
  - `local_scarcity_vs_local_new_transferred_roots_next_window`: 0.2676
  - `local_scarcity_vs_local_net_transferred_root_establishment_within_region`: -0.1830
  - `local_scarcity_vs_local_net_transferred_root_establishment_next_window`: -0.2338
  - `local_cohesion_vs_local_same_region_transfer_retention_within_region`: 0.0434
  - `local_cohesion_vs_local_same_region_transfer_retention_next_window`: 0.0647
  - `local_crowding_vs_local_outgoing_transfer_rate_within_region`: 0.4153
  - `local_crowding_vs_local_outgoing_transfer_rate_next_window`: 0.4168
  - `local_mortality_vs_local_incoming_transfer_rate_within_region`: 0.1896
  - `local_mortality_vs_local_incoming_transfer_rate_next_window`: 0.0904
- high_scarcity_event_study: 67 events
  - cohesion post1-pre1: 0.0324
- high_crowding_event_study: 50 events
  - cohesion post1-pre1: 0.0100
- high_mortality_event_study: 98 events
  - cohesion post1-pre1: 0.0075

## Repeated local directional patterns

- `local_culture.local_crowding_vs_local_outgoing_transfer_rate_next_window`: mean=0.3722, range=[0.2915, 0.4168]
- `local_culture.local_crowding_vs_local_outgoing_transfer_rate_within_region`: mean=0.4218, range=[0.3682, 0.4819]
- `local_culture.local_mortality_vs_local_incoming_transfer_rate_next_window`: mean=0.0878, range=[0.0682, 0.1047]
- `local_culture.local_mortality_vs_local_incoming_transfer_rate_within_region`: mean=0.1966, range=[0.1896, 0.2059]
- `local_culture.local_scarcity_vs_local_net_transferred_root_establishment_next_window`: mean=-0.2352, range=[-0.2418, -0.2300]
- `local_culture.local_scarcity_vs_local_net_transferred_root_establishment_within_region`: mean=-0.1859, range=[-0.1943, -0.1803]
- `local_culture.local_scarcity_vs_local_new_transferred_roots_next_window`: mean=0.2581, range=[0.2452, 0.2676]
- `local_culture.local_scarcity_vs_local_new_transferred_roots_within_region`: mean=0.3727, range=[0.3569, 0.3825]
- `local_culture.local_scarcity_vs_local_outgoing_transfer_rate_within_region`: mean=0.0796, range=[0.0127, 0.1687]
- `next_window_correlations.local_crowding_vs_next_window_local_cohesion`: mean=-0.2700, range=[-0.2886, -0.2574]
- `next_window_correlations.local_hazard_vs_next_window_local_cohesion`: mean=0.0314, range=[0.0210, 0.0517]
- `next_window_correlations.local_mortality_vs_next_window_local_cohesion`: mean=0.1031, range=[0.0511, 0.1957]
- `next_window_correlations.local_population_change_vs_next_window_local_cohesion`: mean=-0.2378, range=[-0.2732, -0.2192]
- `next_window_correlations.local_scarcity_vs_next_window_local_cohesion`: mean=0.3367, range=[0.3259, 0.3512]
- `within_region_correlations.local_crowding_vs_cohesion_within_region`: mean=-0.3563, range=[-0.3915, -0.3336]
- `within_region_correlations.local_mortality_vs_cohesion_within_region`: mean=0.0932, range=[0.0390, 0.1421]
- `within_region_correlations.local_population_change_vs_cohesion_within_region`: mean=-0.1306, range=[-0.1538, -0.1142]
- `within_region_correlations.local_scarcity_vs_cohesion_within_region`: mean=0.3459, range=[0.3263, 0.3609]

## Repeated directional patterns

- `correlations_observational.effective_lineages_vs_cohesion`
- `correlations_observational.knowledge_effective_roots_vs_effective_lineages`
- `correlations_observational.largest_lineage_fraction_vs_cohesion`
- `correlations_observational.lineage_group_nmi_vs_cohesion`
- `correlations_observational.mortality_vs_next_window_cohesion`
- `correlations_observational.mortality_vs_same_window_cohesion`
- `correlations_observational.strategy_dimensions_vs_action_entropy`
- `correlations_first_difference.delta_effective_lineages_vs_delta_cohesion`
- `correlations_first_difference.delta_lineage_group_pair_enrichment_vs_delta_cohesion`
- `correlations_first_difference.delta_mortality_vs_delta_cohesion`
- `correlations_first_difference.delta_strategy_dimensions_vs_delta_action_entropy`
- `correlations_first_difference.mortality_vs_next_delta_cohesion`
- `correlations_partial.effective_lineages_vs_cohesion_controlling_tick_alive`
- `correlations_partial.mortality_vs_cohesion_controlling_tick_alive`

## Interpretation boundary

Repeated signs across seeds support robustness, not necessity. Raw within-run correlations may reflect shared temporal drift. Controlled checkpoint interventions are required for phase-specific causal claims.
