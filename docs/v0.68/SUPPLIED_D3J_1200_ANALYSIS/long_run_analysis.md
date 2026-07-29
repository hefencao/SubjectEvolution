# Multi-seed long-run analysis

Schema: `multi-seed-long-run-analysis-v15`
Analyzer: `0.67.0`
Input runtimes: `['0.67.0']`
Runs: **3**

> This report is observational. Raw correlations, first differences and partial correlations do not identify an in-world causal mechanism.

| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Affinity dims | Transfer commits | Transferred roots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| seed_67001 | 1200 | 1014 | 261.8940 | 0.0168 | 77.6684 | 1.6313 | 0.5363 | 2.9410 | 4602 | 350.6180 |
| seed_67002 | 1200 | 1117 | 188.3873 | 0.0340 | 71.4214 | 1.6174 | 0.3684 | 2.9194 | 4456 | 370.6514 |
| seed_67003 | 1200 | 1085 | 248.9374 | 0.0313 | 77.5813 | 1.6219 | 0.5385 | 2.9721 | 4651 | 326.7220 |

## Within-run raw observational correlations

### seed_67001
- `mortality_vs_same_window_cohesion`: -0.4707
- `mortality_vs_next_window_cohesion`: -0.6507
- `effective_lineages_vs_cohesion`: -0.5342
- `largest_lineage_fraction_vs_cohesion`: 0.6904
- `strategy_dimensions_vs_action_entropy`: 0.9159
- `lineage_group_nmi_vs_cohesion`: 0.3217
- `lineage_group_pair_enrichment_vs_cohesion`: 0.7014
- `knowledge_effective_roots_vs_effective_lineages`: 0.8363

### seed_67002
- `mortality_vs_same_window_cohesion`: 0.2912
- `mortality_vs_next_window_cohesion`: 0.0966
- `effective_lineages_vs_cohesion`: -0.0902
- `largest_lineage_fraction_vs_cohesion`: 0.3256
- `strategy_dimensions_vs_action_entropy`: 0.8892
- `lineage_group_nmi_vs_cohesion`: 0.8927
- `lineage_group_pair_enrichment_vs_cohesion`: 0.7283
- `knowledge_effective_roots_vs_effective_lineages`: 0.8739

### seed_67003
- `mortality_vs_same_window_cohesion`: 0.5107
- `mortality_vs_next_window_cohesion`: 0.6649
- `effective_lineages_vs_cohesion`: -0.1177
- `largest_lineage_fraction_vs_cohesion`: -0.2429
- `strategy_dimensions_vs_action_entropy`: 0.9102
- `lineage_group_nmi_vs_cohesion`: 0.7872
- `lineage_group_pair_enrichment_vs_cohesion`: 0.3567
- `knowledge_effective_roots_vs_effective_lineages`: 0.8342

## First-difference checks

### seed_67001
- `delta_mortality_vs_delta_cohesion`: 0.3196
- `mortality_vs_next_delta_cohesion`: -0.1283
- `delta_effective_lineages_vs_delta_cohesion`: -0.2418
- `delta_largest_lineage_fraction_vs_delta_cohesion`: -0.3877
- `delta_strategy_dimensions_vs_delta_action_entropy`: -0.1174
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: 0.0199

### seed_67002
- `delta_mortality_vs_delta_cohesion`: 0.5480
- `mortality_vs_next_delta_cohesion`: -0.2962
- `delta_effective_lineages_vs_delta_cohesion`: -0.3860
- `delta_largest_lineage_fraction_vs_delta_cohesion`: 0.0544
- `delta_strategy_dimensions_vs_delta_action_entropy`: -0.4494
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: 0.7592

### seed_67003
- `delta_mortality_vs_delta_cohesion`: 0.4404
- `mortality_vs_next_delta_cohesion`: 0.0295
- `delta_effective_lineages_vs_delta_cohesion`: -0.4510
- `delta_largest_lineage_fraction_vs_delta_cohesion`: 0.0603
- `delta_strategy_dimensions_vs_delta_action_entropy`: -0.1917
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: 0.2509

## Partial correlations controlling tick and alive

### seed_67001
- `mortality_vs_cohesion_controlling_tick_alive`: 0.3311
- `effective_lineages_vs_cohesion_controlling_tick_alive`: -0.2469
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: -0.3702
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: 0.2084
- strongest mortality→cohesion cross-lag: lag `2` windows, r=-0.8235

### seed_67002
- `mortality_vs_cohesion_controlling_tick_alive`: 0.8431
- `effective_lineages_vs_cohesion_controlling_tick_alive`: -0.8014
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: 0.7963
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: 0.7920
- strongest mortality→cohesion cross-lag: lag `3` windows, r=-0.6724

### seed_67003
- `mortality_vs_cohesion_controlling_tick_alive`: 0.3929
- `effective_lineages_vs_cohesion_controlling_tick_alive`: -0.4653
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: 0.7430
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: 0.2345
- strongest mortality→cohesion cross-lag: lag `1` windows, r=0.6649

## Costed cultural transfer

### seed_67001
- proposals / admitted attempts / committed / bytes: 6082 / 5588 / 4602 / 277136
- committed cross-lineage / cross-group: 4413 / 6
- active/effective transferred roots: 372 / 350.6180
- cultural-spread interpretable: True

### seed_67002
- proposals / admitted attempts / committed / bytes: 6002 / 5454 / 4456 / 268728
- committed cross-lineage / cross-group: 4244 / 2
- active/effective transferred roots: 385 / 370.6514
- cultural-spread interpretable: True

### seed_67003
- proposals / admitted attempts / committed / bytes: 6235 / 5625 / 4651 / 280112
- committed cross-lineage / cross-group: 4490 / 4
- active/effective transferred roots: 345 / 326.7220
- cultural-spread interpretable: True

## Environment process, danger evidence, mortality trace and group refresh

### seed_67001
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.000215 / 0.250169
- group refresh mode / updates / skipped: adaptive-topology-v1 / 12 / 1188
- group label schema / rounds / trust / min members: trusted-directed-fixed-round-min-label-v1 / 8 / 0.12 / 6
- spatial partition: normalized-fixed-count-grid-v1 4x4, physical=128.0x128.0, cells=32.0x32.0, aligned=True

### seed_67002
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.000221 / 0.250002
- group refresh mode / updates / skipped: adaptive-topology-v1 / 12 / 1188
- group label schema / rounds / trust / min members: trusted-directed-fixed-round-min-label-v1 / 8 / 0.12 / 6
- spatial partition: normalized-fixed-count-grid-v1 4x4, physical=128.0x128.0, cells=32.0x32.0, aligned=True

### seed_67003
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.000171 / 0.250174
- group refresh mode / updates / skipped: adaptive-topology-v1 / 12 / 1188
- group label schema / rounds / trust / min members: trusted-directed-fixed-round-min-label-v1 / 8 / 0.12 / 6
- spatial partition: normalized-fixed-count-grid-v1 4x4, physical=128.0x128.0, cells=32.0x32.0, aligned=True

## Execution backend context

- `seed_67001`: requested=auto, execution=gpu-hybrid-accelerated, gpu_semantics=hybrid-accelerated, device_validated=True, acceleration=True
- `seed_67002`: requested=auto, execution=gpu-hybrid-accelerated, gpu_semantics=hybrid-accelerated, device_validated=True, acceleration=True
- `seed_67003`: requested=auto, execution=gpu-hybrid-accelerated, gpu_semantics=hybrid-accelerated, device_validated=True, acceleration=True

## Local spatial stress panel

### seed_67001
- windows / regions: 12 / 16
- mean population / mortality / scarcity / cohesion CV: 0.2458 / 0.3314 / 0.0811 / 0.3043
- max local/global mortality ratio: 2.7757
- within_region_correlations:
  - `local_mortality_vs_cohesion_within_region`: -0.0729
  - `local_scarcity_vs_cohesion_within_region`: -0.1272
  - `local_hazard_vs_cohesion_within_region`: -0.1164
  - `local_crowding_vs_cohesion_within_region`: -0.1647
  - `local_population_change_vs_cohesion_within_region`: 0.0136
- within_window_correlations:
  - `local_mortality_vs_cohesion_within_window`: 0.0867
  - `local_scarcity_vs_cohesion_within_window`: -0.2894
  - `local_hazard_vs_cohesion_within_window`: -0.1950
  - `local_crowding_vs_cohesion_within_window`: -0.2772
  - `local_population_change_vs_cohesion_within_window`: -0.0239
- first_difference_correlations:
  - `delta_local_mortality_vs_delta_local_cohesion`: -0.3066
  - `delta_local_scarcity_vs_delta_local_cohesion`: -0.2141
  - `delta_local_hazard_vs_delta_local_cohesion`: -0.2687
  - `delta_local_crowding_vs_delta_local_cohesion`: 0.0652
  - `delta_local_population_change_vs_delta_local_cohesion`: 0.4201
- next_window_correlations:
  - `local_mortality_vs_next_window_local_cohesion`: -0.1173
  - `local_scarcity_vs_next_window_local_cohesion`: 0.0637
  - `local_hazard_vs_next_window_local_cohesion`: 0.0809
  - `local_crowding_vs_next_window_local_cohesion`: -0.3060
  - `local_population_change_vs_next_window_local_cohesion`: -0.2171

### seed_67002
- windows / regions: 12 / 16
- mean population / mortality / scarcity / cohesion CV: 0.2469 / 0.3159 / 0.0848 / 0.2031
- max local/global mortality ratio: 2.7285
- within_region_correlations:
  - `local_mortality_vs_cohesion_within_region`: -0.1022
  - `local_scarcity_vs_cohesion_within_region`: 0.2429
  - `local_hazard_vs_cohesion_within_region`: -0.1267
  - `local_crowding_vs_cohesion_within_region`: -0.0351
  - `local_population_change_vs_cohesion_within_region`: 0.0208
- within_window_correlations:
  - `local_mortality_vs_cohesion_within_window`: 0.0694
  - `local_scarcity_vs_cohesion_within_window`: -0.0256
  - `local_hazard_vs_cohesion_within_window`: -0.0494
  - `local_crowding_vs_cohesion_within_window`: -0.0617
  - `local_population_change_vs_cohesion_within_window`: 0.0954
- first_difference_correlations:
  - `delta_local_mortality_vs_delta_local_cohesion`: -0.3143
  - `delta_local_scarcity_vs_delta_local_cohesion`: 0.2995
  - `delta_local_hazard_vs_delta_local_cohesion`: 0.0685
  - `delta_local_crowding_vs_delta_local_cohesion`: -0.4185
  - `delta_local_population_change_vs_delta_local_cohesion`: 0.2716
- next_window_correlations:
  - `local_mortality_vs_next_window_local_cohesion`: -0.0334
  - `local_scarcity_vs_next_window_local_cohesion`: 0.0641
  - `local_hazard_vs_next_window_local_cohesion`: -0.0086
  - `local_crowding_vs_next_window_local_cohesion`: -0.2946
  - `local_population_change_vs_next_window_local_cohesion`: -0.2757

### seed_67003
- windows / regions: 12 / 16
- mean population / mortality / scarcity / cohesion CV: 0.2492 / 0.3447 / 0.0807 / 0.2002
- max local/global mortality ratio: 3.1055
- within_region_correlations:
  - `local_mortality_vs_cohesion_within_region`: -0.1053
  - `local_scarcity_vs_cohesion_within_region`: -0.2710
  - `local_hazard_vs_cohesion_within_region`: 0.2210
  - `local_crowding_vs_cohesion_within_region`: -0.0850
  - `local_population_change_vs_cohesion_within_region`: 0.0073
- within_window_correlations:
  - `local_mortality_vs_cohesion_within_window`: 0.0284
  - `local_scarcity_vs_cohesion_within_window`: -0.1825
  - `local_hazard_vs_cohesion_within_window`: 0.1475
  - `local_crowding_vs_cohesion_within_window`: 0.0097
  - `local_population_change_vs_cohesion_within_window`: -0.1298
- first_difference_correlations:
  - `delta_local_mortality_vs_delta_local_cohesion`: 0.2501
  - `delta_local_scarcity_vs_delta_local_cohesion`: -0.1493
  - `delta_local_hazard_vs_delta_local_cohesion`: 0.1900
  - `delta_local_crowding_vs_delta_local_cohesion`: 0.2341
  - `delta_local_population_change_vs_delta_local_cohesion`: -0.3364
- next_window_correlations:
  - `local_mortality_vs_next_window_local_cohesion`: -0.0582
  - `local_scarcity_vs_next_window_local_cohesion`: -0.0050
  - `local_hazard_vs_next_window_local_cohesion`: 0.0252
  - `local_crowding_vs_next_window_local_cohesion`: -0.1136
  - `local_population_change_vs_next_window_local_cohesion`: -0.0493

## Local cultural transfer panel

### seed_67001
- same/cross-region commits: 4412 / 190
- final active/multi-region transferred roots: 372 / 4
- selected correlations:
  - `local_scarcity_vs_local_outgoing_transfer_rate_within_region`: -0.2838
  - `local_scarcity_vs_local_outgoing_transfer_rate_next_window`: -0.1854
  - `local_scarcity_vs_local_incoming_transfer_rate_within_region`: -0.2859
  - `local_scarcity_vs_local_incoming_transfer_rate_next_window`: -0.1884
  - `local_scarcity_vs_local_new_transferred_roots_within_region`: -0.3010
  - `local_scarcity_vs_local_new_transferred_roots_next_window`: -0.2553
  - `local_scarcity_vs_local_net_transferred_root_establishment_within_region`: -0.2017
  - `local_scarcity_vs_local_net_transferred_root_establishment_next_window`: 0.2829
  - `local_cohesion_vs_local_same_region_transfer_retention_within_region`: 0.0240
  - `local_cohesion_vs_local_same_region_transfer_retention_next_window`: 0.1114
  - `local_crowding_vs_local_outgoing_transfer_rate_within_region`: 0.7853
  - `local_crowding_vs_local_outgoing_transfer_rate_next_window`: 0.8438
  - `local_mortality_vs_local_incoming_transfer_rate_within_region`: 0.3603
  - `local_mortality_vs_local_incoming_transfer_rate_next_window`: 0.1048
- high_scarcity_event_study: 1 events
  - cohesion post1-pre1: —
- high_crowding_event_study: 1 events
  - cohesion post1-pre1: -0.3966
- high_mortality_event_study: 2 events
  - cohesion post1-pre1: —

### seed_67002
- same/cross-region commits: 4257 / 199
- final active/multi-region transferred roots: 385 / 3
- selected correlations:
  - `local_scarcity_vs_local_outgoing_transfer_rate_within_region`: -0.2787
  - `local_scarcity_vs_local_outgoing_transfer_rate_next_window`: -0.2009
  - `local_scarcity_vs_local_incoming_transfer_rate_within_region`: -0.2753
  - `local_scarcity_vs_local_incoming_transfer_rate_next_window`: -0.2129
  - `local_scarcity_vs_local_new_transferred_roots_within_region`: -0.2952
  - `local_scarcity_vs_local_new_transferred_roots_next_window`: -0.2492
  - `local_scarcity_vs_local_net_transferred_root_establishment_within_region`: -0.1825
  - `local_scarcity_vs_local_net_transferred_root_establishment_next_window`: 0.2604
  - `local_cohesion_vs_local_same_region_transfer_retention_within_region`: -0.0374
  - `local_cohesion_vs_local_same_region_transfer_retention_next_window`: -0.0783
  - `local_crowding_vs_local_outgoing_transfer_rate_within_region`: 0.7188
  - `local_crowding_vs_local_outgoing_transfer_rate_next_window`: 0.7708
  - `local_mortality_vs_local_incoming_transfer_rate_within_region`: 0.3853
  - `local_mortality_vs_local_incoming_transfer_rate_next_window`: 0.1297
- high_scarcity_event_study: 1 events
  - cohesion post1-pre1: —
- high_crowding_event_study: 1 events
  - cohesion post1-pre1: —
- high_mortality_event_study: 2 events
  - cohesion post1-pre1: —

### seed_67003
- same/cross-region commits: 4427 / 224
- final active/multi-region transferred roots: 345 / 3
- selected correlations:
  - `local_scarcity_vs_local_outgoing_transfer_rate_within_region`: -0.2643
  - `local_scarcity_vs_local_outgoing_transfer_rate_next_window`: -0.2899
  - `local_scarcity_vs_local_incoming_transfer_rate_within_region`: -0.2590
  - `local_scarcity_vs_local_incoming_transfer_rate_next_window`: -0.2803
  - `local_scarcity_vs_local_new_transferred_roots_within_region`: -0.2923
  - `local_scarcity_vs_local_new_transferred_roots_next_window`: -0.2944
  - `local_scarcity_vs_local_net_transferred_root_establishment_within_region`: -0.2096
  - `local_scarcity_vs_local_net_transferred_root_establishment_next_window`: 0.2769
  - `local_cohesion_vs_local_same_region_transfer_retention_within_region`: 0.0361
  - `local_cohesion_vs_local_same_region_transfer_retention_next_window`: -0.1158
  - `local_crowding_vs_local_outgoing_transfer_rate_within_region`: 0.7714
  - `local_crowding_vs_local_outgoing_transfer_rate_next_window`: 0.8280
  - `local_mortality_vs_local_incoming_transfer_rate_within_region`: 0.3766
  - `local_mortality_vs_local_incoming_transfer_rate_next_window`: 0.1399
- high_scarcity_event_study: 1 events
  - cohesion post1-pre1: -0.2887
- high_crowding_event_study: 0 events
  - cohesion post1-pre1: —
- high_mortality_event_study: 1 events
  - cohesion post1-pre1: —

## Inherited elastic capacities

### seed_67001
- schema: `inherited-elastic-capacities-v1`
- effective dimensions: 3.9258
- working-memory dimensions mean/std: 2.0434 / 0.7023
- knowledge bytes mean/std: 258.0828 / 69.5771
- relation slots mean/std: 4.1183 / 1.0941
- attention slots mean/std: 1.0316 / 0.4034
- working-memory used/utilization/saturated: 2.0414 / 0.9980 / 0.9980
- knowledge bytes used/utilization/saturated: 243.8028 / 0.9350 / 0.3284
- relation edges used/utilization/saturated: 1.3895 / 0.3530 / 0.1124
- zero-attention fraction: 0.0661
- final maintenance/development energy step: — / —
- configured bounds: {'working_memory_dimensions': [0, 4], 'knowledge_bytes': [0, 512], 'relation_slots': [0, 8], 'knowledge_attention_slots': [0, 2]}
- selected observational correlations:
  - `capacity_dimensions_vs_alive`: 0.4954
  - `capacity_dimensions_vs_resource_environment_dimensions`: 0.2405
  - `capacity_dimensions_vs_resource_affinity_dimensions`: 0.8782
  - `capacity_dimensions_vs_boundary_cohesion`: -0.5994
  - `capacity_dimensions_vs_effective_transferred_roots`: 0.6860
  - `working_memory_capacity_vs_action_entropy`: -0.8127
  - `knowledge_capacity_vs_effective_root_contents`: -0.7442
  - `relation_capacity_vs_boundary_cohesion`: 0.7045
  - `attention_capacity_vs_committed_transfer`: -0.7000
- boundary: capacity–outcome correlations can reflect shared selection and demographic drift; paired capacity-expression interventions are required for causal claims.

### seed_67002
- schema: `inherited-elastic-capacities-v1`
- effective dimensions: 3.8902
- working-memory dimensions mean/std: 2.0269 / 0.7063
- knowledge bytes mean/std: 247.2337 / 65.0948
- relation slots mean/std: 3.9346 / 1.1188
- attention slots mean/std: 1.0358 / 0.3953
- working-memory used/utilization/saturated: 2.0224 / 0.9982 / 0.9982
- knowledge bytes used/utilization/saturated: 233.1817 / 0.9390 / 0.3223
- relation edges used/utilization/saturated: 1.4172 / 0.3950 / 0.1558
- zero-attention fraction: 0.0609
- final maintenance/development energy step: — / —
- configured bounds: {'working_memory_dimensions': [0, 4], 'knowledge_bytes': [0, 512], 'relation_slots': [0, 8], 'knowledge_attention_slots': [0, 2]}
- selected observational correlations:
  - `capacity_dimensions_vs_alive`: 0.3448
  - `capacity_dimensions_vs_resource_environment_dimensions`: 0.1753
  - `capacity_dimensions_vs_resource_affinity_dimensions`: 0.7574
  - `capacity_dimensions_vs_boundary_cohesion`: -0.4577
  - `capacity_dimensions_vs_effective_transferred_roots`: 0.5245
  - `working_memory_capacity_vs_action_entropy`: -0.2305
  - `knowledge_capacity_vs_effective_root_contents`: 0.4043
  - `relation_capacity_vs_boundary_cohesion`: -0.4024
  - `attention_capacity_vs_committed_transfer`: -0.5876
- boundary: capacity–outcome correlations can reflect shared selection and demographic drift; paired capacity-expression interventions are required for causal claims.

### seed_67003
- schema: `inherited-elastic-capacities-v1`
- effective dimensions: 3.9549
- working-memory dimensions mean/std: 2.0369 / 0.6472
- knowledge bytes mean/std: 251.9300 / 70.3131
- relation slots mean/std: 3.8627 / 1.1223
- attention slots mean/std: 0.9917 / 0.4553
- working-memory used/utilization/saturated: 2.0350 / 0.9991 / 0.9991
- knowledge bytes used/utilization/saturated: 236.7263 / 0.9368 / 0.3014
- relation edges used/utilization/saturated: 1.3714 / 0.3800 / 0.1189
- zero-attention fraction: 0.1078
- final maintenance/development energy step: — / —
- configured bounds: {'working_memory_dimensions': [0, 4], 'knowledge_bytes': [0, 512], 'relation_slots': [0, 8], 'knowledge_attention_slots': [0, 2]}
- selected observational correlations:
  - `capacity_dimensions_vs_alive`: 0.5495
  - `capacity_dimensions_vs_resource_environment_dimensions`: 0.3113
  - `capacity_dimensions_vs_resource_affinity_dimensions`: 0.8165
  - `capacity_dimensions_vs_boundary_cohesion`: 0.2760
  - `capacity_dimensions_vs_effective_transferred_roots`: 0.7507
  - `working_memory_capacity_vs_action_entropy`: -0.6391
  - `knowledge_capacity_vs_effective_root_contents`: 0.5944
  - `relation_capacity_vs_boundary_cohesion`: 0.2530
  - `attention_capacity_vs_committed_transfer`: 0.3623
- boundary: capacity–outcome correlations can reflect shared selection and demographic drift; paired capacity-expression interventions are required for causal claims.

## D2-A contextual functional modules

### seed_67001
- schema: `expression-gated-regulatory-resource-metabolism-v6`
- expressed modules mean/fraction: 1.9862 / 0.4965
- gate mean/std/effective dimensions: 0.0939 / 0.1361 / 3.8916
- contextual harvest-preference effective dimensions: 2.9418
- module residual mean/max |share|: 0.000339 / 0.004456
- entities with changed request weights: 0.9082
- residual effective dimensions: 2.9691
- effective contributing modules / dominance / cancellation: 3.9931 / 0.2614 / 0.2100
- coupling schema / links / changed entities: `lower-slot-signal-modulation-v1` / 6 / 0.5262
- mediated signal / modulation mean: 0.000381 / 0.011386
- per-level mediated signal: [0.0, 0.0001923240066633761, 0.00039549335204837116, 0.0009351092053307008]
- per-level amplification / suppression: [0.0, 0.11213235294117647, 0.206286836935167, 0.3004115226337449] / [0.0, 0.14705882352941177, 0.2730844793713163, 0.33539094650205764]
- per-module contribution shares: [0.23631910426871938, 0.243666899930021, 0.26137158852344294, 0.2586424072778167]
- per-module isolated |residual| means: [0.00010173530239696446, 0.00010489852619076999, 0.00011252038923679664, 0.00011134547754195459]
- per-module nonzero/silent fractions: [0.4027640671273445, 0.4531095755182626, 0.43435340572556763, 0.42941757156959526] / [0.13742071881606766, 0.15625, 0.13555992141453832, 0.10493827160493827]
- preference mean: [0.2702622860817189, 0.24330372636198175, 0.24053467037882528, 0.2458993171774741]
- final maintenance/development energy step: — / —
- boundary: v1 slots are independent additive terms; v2 adds bounded feed-forward composition but still only alters harvest-channel requests. Neither architecture alone establishes ecological differentiation.

### seed_67002
- schema: `expression-gated-regulatory-resource-metabolism-v6`
- expressed modules mean/fraction: 2.0412 / 0.5103
- gate mean/std/effective dimensions: 0.0992 / 0.1454 / 3.8314
- contextual harvest-preference effective dimensions: 2.9185
- module residual mean/max |share|: 0.000393 / 0.005310
- entities with changed request weights: 0.9211
- residual effective dimensions: 2.9619
- effective contributing modules / dominance / cancellation: 3.9007 / 0.3004 / 0.1889
- coupling schema / links / changed entities: `lower-slot-signal-modulation-v1` / 6 / 0.5305
- mediated signal / modulation mean: 0.000430 / 0.012136
- per-level mediated signal: [0.0, 0.00029095612119175627, 0.000598975834453405, 0.0008291155633960573]
- per-level amplification / suppression: [0.0, 0.12457912457912458, 0.22878228782287824, 0.23432343234323433] / [0.0, 0.1717171717171717, 0.25092250922509224, 0.3712871287128713]
- per-module contribution shares: [0.22514652840396754, 0.3003832281334536, 0.1992786293958521, 0.27519161406672676]
- per-module isolated |residual| means: [0.00010924527294746864, 0.0001457515155969982, 9.669368839605735e-05, 0.000133528077046931]
- per-module nonzero/silent fractions: [0.4103942652329749, 0.4560931899641577, 0.3942652329749104, 0.47401433691756273] / [0.1455223880597015, 0.14309764309764308, 0.1881918819188192, 0.12706270627062707]
- preference mean: [0.2723363514014897, 0.24263060648381496, 0.24241375666792675, 0.24261928544676858]
- final maintenance/development energy step: — / —
- boundary: v1 slots are independent additive terms; v2 adds bounded feed-forward composition but still only alters harvest-channel requests. Neither architecture alone establishes ecological differentiation.

### seed_67003
- schema: `expression-gated-regulatory-resource-metabolism-v6`
- expressed modules mean/fraction: 2.0092 / 0.5023
- gate mean/std/effective dimensions: 0.0982 / 0.1435 / 3.9647
- contextual harvest-preference effective dimensions: 2.9717
- module residual mean/max |share|: 0.000367 / 0.004761
- entities with changed request weights: 0.8903
- residual effective dimensions: 2.9626
- effective contributing modules / dominance / cancellation: 3.9923 / 0.2646 / 0.2085
- coupling schema / links / changed entities: `lower-slot-signal-modulation-v1` / 6 / 0.5253
- mediated signal / modulation mean: 0.000415 / 0.011264
- per-level mediated signal: [0.0, 0.0003141201036866359, 0.0006356656826036867, 0.0007114955357142857]
- per-level amplification / suppression: [0.0, 0.1735985533453888, 0.21212121212121213, 0.29713114754098363] / [0.0, 0.1609403254972875, 0.28342245989304815, 0.3442622950819672]
- per-module contribution shares: [0.26459942084942084, 0.24022683397683398, 0.2566361003861004, 0.23853764478764478]
- per-module isolated |residual| means: [0.00012336414530529955, 0.00011200091805875576, 0.00011965140769009217, 0.00011121336765552996]
- per-module nonzero/silent fractions: [0.4663594470046083, 0.432258064516129, 0.4202764976958525, 0.3778801843317972] / [0.1245674740484429, 0.1518987341772152, 0.18716577540106952, 0.1598360655737705]
- preference mean: [0.27229482061851956, 0.24115198372695854, 0.23930467174899195, 0.24724852390552995]
- final maintenance/development energy step: — / —
- boundary: v1 slots are independent additive terms; v2 adds bounded feed-forward composition but still only alters harvest-channel requests. Neither architecture alone establishes ecological differentiation.

## Candidate-subject succession diagnostics

### seed_67001
- schema: `stable-membership-subject-succession-v1`
- refreshes / active / effective groups: 12 / 2 / 1.9600
- weighted predecessor Jaccard / inheritance: 0.4286 / 0.4286
- cumulative splits / merges / formations / dissolutions: 0 / 0 / 99 / 97

### seed_67002
- schema: `stable-membership-subject-succession-v1`
- refreshes / active / effective groups: 12 / 5 / 4.7087
- weighted predecessor Jaccard / inheritance: 0.5876 / 0.6829
- cumulative splits / merges / formations / dissolutions: 2 / 1 / 85 / 81

### seed_67003
- schema: `stable-membership-subject-succession-v1`
- refreshes / active / effective groups: 12 / 1 / 1.0000
- weighted predecessor Jaccard / inheritance: 0.0000 / 0.0000
- cumulative splits / merges / formations / dissolutions: 0 / 0 / 96 / 95

## Realized resource demand

### seed_67001
- harvest allocation schema: `affinity-sampled-exclusive-harvest-v1`
- request observation schema: `explicit-requested-harvest-window-v1`
- realized channel shares: [0.2525, 0.2497, 0.2492, 0.2486]
- requested channel shares: [0.2515, 0.2492, 0.2491, 0.2503]
- realized balance effective count: 3.9999
- requested balance effective count: 3.9999
- raw realized volume dimensions / mean |corr|: 1.0002 / 0.9999
- realized share-composition dimensions / mean |corr|: 2.5151 / 0.4283
- raw requested volume dimensions / mean |corr|: 1.0005 / 0.9997
- requested share-composition dimensions / mean |corr|: 2.3992 / 0.4522
- realized volume vs requested volume: 0.9999
- balance vs resource-field dimensions: -0.5226
- realized/requested extraction efficiency mean/final: 0.9810 / 0.9657

### seed_67002
- harvest allocation schema: `affinity-sampled-exclusive-harvest-v1`
- request observation schema: `explicit-requested-harvest-window-v1`
- realized channel shares: [0.2513, 0.2503, 0.2496, 0.2487]
- requested channel shares: [0.25, 0.2499, 0.25, 0.2501]
- realized balance effective count: 3.9999
- requested balance effective count: 4.0000
- raw realized volume dimensions / mean |corr|: 1.0004 / 0.9997
- realized share-composition dimensions / mean |corr|: 2.7937 / 0.3103
- raw requested volume dimensions / mean |corr|: 1.0006 / 0.9996
- requested share-composition dimensions / mean |corr|: 2.2846 / 0.4604
- realized volume vs requested volume: 0.9998
- balance vs resource-field dimensions: -0.3838
- realized/requested extraction efficiency mean/final: 0.9752 / 0.9323

### seed_67003
- harvest allocation schema: `affinity-sampled-exclusive-harvest-v1`
- request observation schema: `explicit-requested-harvest-window-v1`
- realized channel shares: [0.252, 0.2503, 0.2494, 0.2483]
- requested channel shares: [0.2507, 0.2498, 0.2503, 0.2493]
- realized balance effective count: 3.9999
- requested balance effective count: 4.0000
- raw realized volume dimensions / mean |corr|: 1.0003 / 0.9998
- realized share-composition dimensions / mean |corr|: 2.7323 / 0.3213
- raw requested volume dimensions / mean |corr|: 1.0003 / 0.9998
- requested share-composition dimensions / mean |corr|: 2.7722 / 0.3317
- realized volume vs requested volume: 0.9999
- balance vs resource-field dimensions: -0.2482
- realized/requested extraction efficiency mean/final: 0.9824 / 0.9695

## Orthogonal resource environment

### seed_67001
- schema: `orthogonal-four-resource-renewal-v2`
- final resource effective dimensions: 2.3372
- final resource mean/max absolute correlation: 0.1187 / 0.2380
- cycle periods: [173, 257, 349, 431]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]

### seed_67002
- schema: `orthogonal-four-resource-renewal-v2`
- final resource effective dimensions: 2.3691
- final resource mean/max absolute correlation: 0.1520 / 0.2753
- cycle periods: [173, 257, 349, 431]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]

### seed_67003
- schema: `orthogonal-four-resource-renewal-v2`
- final resource effective dimensions: 2.3544
- final resource mean/max absolute correlation: 0.1441 / 0.2690
- cycle periods: [173, 257, 349, 431]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]

## Multiscale subject–environment atlas

### seed_67001
- schema / scales: `multiscale-subject-environment-atlas-v2` / 3
- 2x2: signature dims=1.8145, resource dims=1.0883, resource mean/max |corr|=0.2914/0.9999, mean distance=0.1892, turnover=0.0626, lineage association=0.9122, social association=1.0000
- 4x4: signature dims=2.7946, resource dims=2.2303, resource mean/max |corr|=0.0571/0.1134, mean distance=0.3413, turnover=0.1361, lineage association=0.9356, social association=1.0000
- 8x8: signature dims=2.8223, resource dims=2.1684, resource mean/max |corr|=0.0208/0.0415, mean distance=0.3987, turnover=0.1577, lineage association=0.9176, social association=1.0000

### seed_67002
- schema / scales: `multiscale-subject-environment-atlas-v2` / 3
- 2x2: signature dims=1.8104, resource dims=1.0991, resource mean/max |corr|=0.2705/0.9992, mean distance=0.1925, turnover=0.0625, lineage association=0.9402, social association=1.0000
- 4x4: signature dims=2.8049, resource dims=2.2129, resource mean/max |corr|=0.0696/0.1891, mean distance=0.3443, turnover=0.1360, lineage association=0.9236, social association=0.9039
- 8x8: signature dims=2.8451, resource dims=2.1990, resource mean/max |corr|=0.0421/0.0948, mean distance=0.4016, turnover=0.1575, lineage association=0.9388, social association=0.8915

### seed_67003
- schema / scales: `multiscale-subject-environment-atlas-v2` / 3
- 2x2: signature dims=1.7936, resource dims=1.0839, resource mean/max |corr|=0.2628/0.9991, mean distance=0.1933, turnover=0.0624, lineage association=0.9343, social association=0.0000
- 4x4: signature dims=2.8100, resource dims=2.2289, resource mean/max |corr|=0.0646/0.1641, mean distance=0.3439, turnover=0.1360, lineage association=0.9099, social association=0.0000
- 8x8: signature dims=2.8476, resource dims=2.1908, resource mean/max |corr|=0.0395/0.1112, mean distance=0.4024, turnover=0.1577, lineage association=0.9287, social association=0.0000

## Repeated local directional patterns

- `local_culture.local_crowding_vs_local_outgoing_transfer_rate_next_window`: mean=0.8142, range=[0.7708, 0.8438]
- `local_culture.local_crowding_vs_local_outgoing_transfer_rate_within_region`: mean=0.7585, range=[0.7188, 0.7853]
- `local_culture.local_mortality_vs_local_incoming_transfer_rate_next_window`: mean=0.1248, range=[0.1048, 0.1399]
- `local_culture.local_mortality_vs_local_incoming_transfer_rate_within_region`: mean=0.3741, range=[0.3603, 0.3853]
- `local_culture.local_scarcity_vs_local_incoming_transfer_rate_next_window`: mean=-0.2272, range=[-0.2803, -0.1884]
- `local_culture.local_scarcity_vs_local_incoming_transfer_rate_within_region`: mean=-0.2734, range=[-0.2859, -0.2590]
- `local_culture.local_scarcity_vs_local_net_transferred_root_establishment_next_window`: mean=0.2734, range=[0.2604, 0.2829]
- `local_culture.local_scarcity_vs_local_net_transferred_root_establishment_within_region`: mean=-0.1979, range=[-0.2096, -0.1825]
- `local_culture.local_scarcity_vs_local_new_transferred_roots_next_window`: mean=-0.2663, range=[-0.2944, -0.2492]
- `local_culture.local_scarcity_vs_local_new_transferred_roots_within_region`: mean=-0.2962, range=[-0.3010, -0.2923]
- `local_culture.local_scarcity_vs_local_outgoing_transfer_rate_next_window`: mean=-0.2254, range=[-0.2899, -0.1854]
- `local_culture.local_scarcity_vs_local_outgoing_transfer_rate_within_region`: mean=-0.2756, range=[-0.2838, -0.2643]
- `next_window_correlations.local_crowding_vs_next_window_local_cohesion`: mean=-0.2381, range=[-0.3060, -0.1136]
- `next_window_correlations.local_mortality_vs_next_window_local_cohesion`: mean=-0.0696, range=[-0.1173, -0.0334]
- `next_window_correlations.local_population_change_vs_next_window_local_cohesion`: mean=-0.1807, range=[-0.2757, -0.0493]
- `within_region_correlations.local_crowding_vs_cohesion_within_region`: mean=-0.0949, range=[-0.1647, -0.0351]
- `within_region_correlations.local_mortality_vs_cohesion_within_region`: mean=-0.0934, range=[-0.1053, -0.0729]
- `within_region_correlations.local_population_change_vs_cohesion_within_region`: mean=0.0139, range=[0.0073, 0.0208]

## Repeated directional patterns

- `correlations_observational.effective_lineages_vs_cohesion`
- `correlations_observational.knowledge_effective_roots_vs_effective_lineages`
- `correlations_observational.lineage_group_nmi_vs_cohesion`
- `correlations_observational.lineage_group_pair_enrichment_vs_cohesion`
- `correlations_observational.strategy_dimensions_vs_action_entropy`
- `correlations_first_difference.delta_effective_lineages_vs_delta_cohesion`
- `correlations_first_difference.delta_lineage_group_pair_enrichment_vs_delta_cohesion`
- `correlations_first_difference.delta_mortality_vs_delta_cohesion`
- `correlations_first_difference.delta_strategy_dimensions_vs_delta_action_entropy`
- `correlations_partial.effective_lineages_vs_cohesion_controlling_tick_alive`
- `correlations_partial.lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`
- `correlations_partial.mortality_vs_cohesion_controlling_tick_alive`

## Interpretation boundary

Repeated signs across seeds support robustness, not necessity. Raw within-run correlations may reflect shared temporal drift. Controlled checkpoint interventions are required for phase-specific causal claims.
