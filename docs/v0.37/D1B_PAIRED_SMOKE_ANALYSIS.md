# Multi-seed long-run analysis

Schema: `multi-seed-long-run-analysis-v12`
Analyzer: `0.37.0`
Input runtimes: `['0.37.0']`
Runs: **2**

> This report is observational. Raw correlations, first differences and partial correlations do not identify an in-world causal mechanism.

| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Affinity dims | Transfer commits | Transferred roots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v037_uniform300 | 300 | 134 | 44.4455 | 0.0597 | 32.4824 | 1.8540 | 0.0000 | 2.8665 | 51 | 18.0000 |
| v037_selective300_sampled | 300 | 115 | 35.0796 | 0.0783 | 27.8082 | 1.8452 | 0.0000 | 2.8392 | 49 | 17.0000 |

## Within-run raw observational correlations

### v037_uniform300
- `mortality_vs_same_window_cohesion`: —
- `mortality_vs_next_window_cohesion`: —
- `effective_lineages_vs_cohesion`: —
- `largest_lineage_fraction_vs_cohesion`: —
- `strategy_dimensions_vs_action_entropy`: 0.9585
- `lineage_group_nmi_vs_cohesion`: —
- `lineage_group_pair_enrichment_vs_cohesion`: —
- `knowledge_effective_roots_vs_effective_lineages`: 0.9698

### v037_selective300_sampled
- `mortality_vs_same_window_cohesion`: 0.6536
- `mortality_vs_next_window_cohesion`: 0.4537
- `effective_lineages_vs_cohesion`: 0.0097
- `largest_lineage_fraction_vs_cohesion`: -0.2859
- `strategy_dimensions_vs_action_entropy`: 0.9494
- `lineage_group_nmi_vs_cohesion`: —
- `lineage_group_pair_enrichment_vs_cohesion`: 0.7567
- `knowledge_effective_roots_vs_effective_lineages`: 0.9824

## First-difference checks

### v037_uniform300
- `delta_mortality_vs_delta_cohesion`: —
- `mortality_vs_next_delta_cohesion`: —
- `delta_effective_lineages_vs_delta_cohesion`: —
- `delta_largest_lineage_fraction_vs_delta_cohesion`: —
- `delta_strategy_dimensions_vs_delta_action_entropy`: 0.3779
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: —

### v037_selective300_sampled
- `delta_mortality_vs_delta_cohesion`: 0.5039
- `mortality_vs_next_delta_cohesion`: -0.1869
- `delta_effective_lineages_vs_delta_cohesion`: -0.3541
- `delta_largest_lineage_fraction_vs_delta_cohesion`: -0.3585
- `delta_strategy_dimensions_vs_delta_action_entropy`: 0.1584
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: 0.5491

## Partial correlations controlling tick and alive

### v037_uniform300
- `mortality_vs_cohesion_controlling_tick_alive`: —
- `effective_lineages_vs_cohesion_controlling_tick_alive`: —
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: —
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: —

### v037_selective300_sampled
- `mortality_vs_cohesion_controlling_tick_alive`: 0.6509
- `effective_lineages_vs_cohesion_controlling_tick_alive`: -0.3702
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: -0.4564
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: 0.6674
- strongest mortality→cohesion cross-lag: lag `3` windows, r=-0.9546

## Costed cultural transfer

### v037_uniform300
- proposals / admitted attempts / committed / bytes: 74 / 66 / 51 / 3184
- committed cross-lineage / cross-group: 47 / 0
- active/effective transferred roots: 18 / 18.0000
- cultural-spread interpretable: True

### v037_selective300_sampled
- proposals / admitted attempts / committed / bytes: 73 / 63 / 49 / 2736
- committed cross-lineage / cross-group: 40 / 0
- active/effective transferred roots: 17 / 17.0000
- cultural-spread interpretable: True

## Environment process, danger evidence, mortality trace and group refresh

### v037_uniform300
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.001298 / 0.113641
- group refresh mode / updates / skipped: adaptive-topology-v1 / 3 / 297
- group label schema / rounds / trust / min members: trusted-directed-fixed-round-min-label-v1 / 8 / 0.12 / 6
- spatial partition: normalized-fixed-count-grid-v1 4x4, physical=32.0x32.0, cells=8.0x8.0, aligned=True

### v037_selective300_sampled
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.003057 / 0.255113
- group refresh mode / updates / skipped: adaptive-topology-v1 / 3 / 297
- group label schema / rounds / trust / min members: trusted-directed-fixed-round-min-label-v1 / 8 / 0.12 / 6
- spatial partition: normalized-fixed-count-grid-v1 4x4, physical=32.0x32.0, cells=8.0x8.0, aligned=True

## Execution backend context

- `v037_uniform300`: requested=cpu, execution=cpu, gpu_semantics=strict-reference, device_validated=False, acceleration=False
- `v037_selective300_sampled`: requested=cpu, execution=cpu, gpu_semantics=strict-reference, device_validated=False, acceleration=False

## Local spatial stress panel

### v037_uniform300
- windows / regions: 10 / 16
- mean population / mortality / scarcity / cohesion CV: 0.4020 / 1.1477 / 0.1679 / 0.0000
- max local/global mortality ratio: 8.3740
- within_region_correlations:
  - `local_mortality_vs_cohesion_within_region`: —
  - `local_scarcity_vs_cohesion_within_region`: —
  - `local_hazard_vs_cohesion_within_region`: —
  - `local_crowding_vs_cohesion_within_region`: —
  - `local_population_change_vs_cohesion_within_region`: —
- within_window_correlations:
  - `local_mortality_vs_cohesion_within_window`: —
  - `local_scarcity_vs_cohesion_within_window`: —
  - `local_hazard_vs_cohesion_within_window`: —
  - `local_crowding_vs_cohesion_within_window`: —
  - `local_population_change_vs_cohesion_within_window`: —
- first_difference_correlations:
  - `delta_local_mortality_vs_delta_local_cohesion`: —
  - `delta_local_scarcity_vs_delta_local_cohesion`: —
  - `delta_local_hazard_vs_delta_local_cohesion`: —
  - `delta_local_crowding_vs_delta_local_cohesion`: —
  - `delta_local_population_change_vs_delta_local_cohesion`: —
- next_window_correlations:
  - `local_mortality_vs_next_window_local_cohesion`: —
  - `local_scarcity_vs_next_window_local_cohesion`: —
  - `local_hazard_vs_next_window_local_cohesion`: —
  - `local_crowding_vs_next_window_local_cohesion`: —
  - `local_population_change_vs_next_window_local_cohesion`: —

### v037_selective300_sampled
- windows / regions: 10 / 16
- mean population / mortality / scarcity / cohesion CV: 0.4448 / 0.8462 / 0.1808 / 0.0000
- max local/global mortality ratio: 2.9438
- within_region_correlations:
  - `local_mortality_vs_cohesion_within_region`: —
  - `local_scarcity_vs_cohesion_within_region`: —
  - `local_hazard_vs_cohesion_within_region`: —
  - `local_crowding_vs_cohesion_within_region`: —
  - `local_population_change_vs_cohesion_within_region`: —
- within_window_correlations:
  - `local_mortality_vs_cohesion_within_window`: —
  - `local_scarcity_vs_cohesion_within_window`: —
  - `local_hazard_vs_cohesion_within_window`: —
  - `local_crowding_vs_cohesion_within_window`: —
  - `local_population_change_vs_cohesion_within_window`: —
- first_difference_correlations:
  - `delta_local_mortality_vs_delta_local_cohesion`: —
  - `delta_local_scarcity_vs_delta_local_cohesion`: —
  - `delta_local_hazard_vs_delta_local_cohesion`: —
  - `delta_local_crowding_vs_delta_local_cohesion`: —
  - `delta_local_population_change_vs_delta_local_cohesion`: —
- next_window_correlations:
  - `local_mortality_vs_next_window_local_cohesion`: —
  - `local_scarcity_vs_next_window_local_cohesion`: —
  - `local_hazard_vs_next_window_local_cohesion`: —
  - `local_crowding_vs_next_window_local_cohesion`: —
  - `local_population_change_vs_next_window_local_cohesion`: —

## Local cultural transfer panel

### v037_uniform300
- same/cross-region commits: 43 / 8
- final active/multi-region transferred roots: 18 / 0
- selected correlations:
  - `local_scarcity_vs_local_outgoing_transfer_rate_within_region`: -0.1736
  - `local_scarcity_vs_local_outgoing_transfer_rate_next_window`: 0.1296
  - `local_scarcity_vs_local_incoming_transfer_rate_within_region`: -0.1988
  - `local_scarcity_vs_local_incoming_transfer_rate_next_window`: 0.1845
  - `local_scarcity_vs_local_new_transferred_roots_within_region`: -0.2534
  - `local_scarcity_vs_local_new_transferred_roots_next_window`: 0.0927
  - `local_scarcity_vs_local_net_transferred_root_establishment_within_region`: -0.2489
  - `local_scarcity_vs_local_net_transferred_root_establishment_next_window`: -0.0073
  - `local_cohesion_vs_local_same_region_transfer_retention_within_region`: —
  - `local_cohesion_vs_local_same_region_transfer_retention_next_window`: —
  - `local_crowding_vs_local_outgoing_transfer_rate_within_region`: -0.0867
  - `local_crowding_vs_local_outgoing_transfer_rate_next_window`: 0.0956
  - `local_mortality_vs_local_incoming_transfer_rate_within_region`: -0.1550
  - `local_mortality_vs_local_incoming_transfer_rate_next_window`: -0.1754
- high_scarcity_event_study: 0 events
  - cohesion post1-pre1: —
- high_crowding_event_study: 0 events
  - cohesion post1-pre1: —
- high_mortality_event_study: 0 events
  - cohesion post1-pre1: —

### v037_selective300_sampled
- same/cross-region commits: 39 / 10
- final active/multi-region transferred roots: 17 / 0
- selected correlations:
  - `local_scarcity_vs_local_outgoing_transfer_rate_within_region`: -0.0142
  - `local_scarcity_vs_local_outgoing_transfer_rate_next_window`: 0.1938
  - `local_scarcity_vs_local_incoming_transfer_rate_within_region`: -0.1164
  - `local_scarcity_vs_local_incoming_transfer_rate_next_window`: 0.0095
  - `local_scarcity_vs_local_new_transferred_roots_within_region`: -0.1935
  - `local_scarcity_vs_local_new_transferred_roots_next_window`: 0.0651
  - `local_scarcity_vs_local_net_transferred_root_establishment_within_region`: -0.2316
  - `local_scarcity_vs_local_net_transferred_root_establishment_next_window`: -0.0443
  - `local_cohesion_vs_local_same_region_transfer_retention_within_region`: —
  - `local_cohesion_vs_local_same_region_transfer_retention_next_window`: —
  - `local_crowding_vs_local_outgoing_transfer_rate_within_region`: 0.1121
  - `local_crowding_vs_local_outgoing_transfer_rate_next_window`: 0.2359
  - `local_mortality_vs_local_incoming_transfer_rate_within_region`: -0.1090
  - `local_mortality_vs_local_incoming_transfer_rate_next_window`: -0.0384
- high_scarcity_event_study: 0 events
  - cohesion post1-pre1: —
- high_crowding_event_study: 0 events
  - cohesion post1-pre1: —
- high_mortality_event_study: 0 events
  - cohesion post1-pre1: —

## Inherited elastic capacities

### v037_uniform300
- schema: `inherited-elastic-capacities-v1`
- effective dimensions: 3.8081
- working-memory dimensions mean/std: 2.1716 / 0.6750
- knowledge bytes mean/std: 256.4776 / 64.8287
- relation slots mean/std: 3.8881 / 1.0904
- attention slots mean/std: 0.9328 / 0.4603
- working-memory used/utilization/saturated: 2.1716 / 1.0000 / 1.0000
- knowledge bytes used/utilization/saturated: 240.5970 / 0.9335 / 0.2836
- relation edges used/utilization/saturated: 1.8134 / 0.4946 / 0.1866
- zero-attention fraction: 0.1418
- final maintenance/development energy step: — / —
- configured bounds: {'working_memory_dimensions': [0, 4], 'knowledge_bytes': [0, 512], 'relation_slots': [0, 8], 'knowledge_attention_slots': [0, 2]}
- selected observational correlations:
  - `capacity_dimensions_vs_alive`: 0.9312
  - `capacity_dimensions_vs_resource_environment_dimensions`: 0.9538
  - `capacity_dimensions_vs_resource_affinity_dimensions`: 0.5659
  - `capacity_dimensions_vs_boundary_cohesion`: —
  - `capacity_dimensions_vs_effective_transferred_roots`: 0.0904
  - `working_memory_capacity_vs_action_entropy`: -0.8234
  - `knowledge_capacity_vs_effective_root_contents`: 0.7516
  - `relation_capacity_vs_boundary_cohesion`: —
  - `attention_capacity_vs_committed_transfer`: 0.6458
- boundary: capacity–outcome correlations can reflect shared selection and demographic drift; paired capacity-expression interventions are required for causal claims.

### v037_selective300_sampled
- schema: `inherited-elastic-capacities-v1`
- effective dimensions: 3.8532
- working-memory dimensions mean/std: 2.2000 / 0.7003
- knowledge bytes mean/std: 251.5478 / 69.4561
- relation slots mean/std: 3.9304 / 1.0191
- attention slots mean/std: 0.8957 / 0.4823
- working-memory used/utilization/saturated: 2.1826 / 0.9912 / 0.9912
- knowledge bytes used/utilization/saturated: 232.4174 / 0.9212 / 0.2522
- relation edges used/utilization/saturated: 1.3217 / 0.3525 / 0.0696
- zero-attention fraction: 0.1739
- final maintenance/development energy step: — / —
- configured bounds: {'working_memory_dimensions': [0, 4], 'knowledge_bytes': [0, 512], 'relation_slots': [0, 8], 'knowledge_attention_slots': [0, 2]}
- selected observational correlations:
  - `capacity_dimensions_vs_alive`: 0.7667
  - `capacity_dimensions_vs_resource_environment_dimensions`: 0.9506
  - `capacity_dimensions_vs_resource_affinity_dimensions`: 0.6968
  - `capacity_dimensions_vs_boundary_cohesion`: 0.1224
  - `capacity_dimensions_vs_effective_transferred_roots`: -0.1745
  - `working_memory_capacity_vs_action_entropy`: -0.9500
  - `knowledge_capacity_vs_effective_root_contents`: 0.6657
  - `relation_capacity_vs_boundary_cohesion`: -0.2103
  - `attention_capacity_vs_committed_transfer`: 0.6052
- boundary: capacity–outcome correlations can reflect shared selection and demographic drift; paired capacity-expression interventions are required for causal claims.

## Candidate-subject succession diagnostics

### v037_uniform300
- schema: `stable-membership-subject-succession-v1`
- refreshes / active / effective groups: 3 / 0 / 0.0000
- weighted predecessor Jaccard / inheritance: 0.0000 / 0.0000
- cumulative splits / merges / formations / dissolutions: 0 / 0 / 0 / 0

### v037_selective300_sampled
- schema: `stable-membership-subject-succession-v1`
- refreshes / active / effective groups: 3 / 0 / 0.0000
- weighted predecessor Jaccard / inheritance: 0.0000 / 0.0000
- cumulative splits / merges / formations / dissolutions: 0 / 0 / 1 / 1

## Realized resource demand

### v037_uniform300
- harvest allocation schema: `uniform-channel-rates-v1`
- channel shares: [0.2387, 0.2474, 0.2539, 0.2599]
- balance effective count: 3.9960
- temporal effective dimensions: 1.2015
- mean/max |channel correlation|: 0.8758 / 0.9870
- balance vs resource-field dimensions: 0.9497
- realized/requested extraction efficiency mean/final: 0.9415 / 0.9043

### v037_selective300_sampled
- harvest allocation schema: `affinity-sampled-exclusive-harvest-v1`
- channel shares: [0.2451, 0.2518, 0.2513, 0.2518]
- balance effective count: 3.9995
- temporal effective dimensions: 2.0816
- mean/max |channel correlation|: 0.5224 / 0.6770
- balance vs resource-field dimensions: -0.1097
- realized/requested extraction efficiency mean/final: 0.9093 / 0.8713

## Orthogonal resource environment

### v037_uniform300
- schema: `orthogonal-four-resource-niche-v1`
- final resource effective dimensions: 1.4897
- final resource mean/max absolute correlation: 0.7442 / 0.7800
- cycle periods: [173, 257, 349, 431]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]

### v037_selective300_sampled
- schema: `orthogonal-four-resource-niche-v1`
- final resource effective dimensions: 1.8248
- final resource mean/max absolute correlation: 0.6083 / 0.6636
- cycle periods: [173, 257, 349, 431]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]

## Multiscale subject–environment atlas

### v037_uniform300
- schema / scales: `multiscale-subject-environment-atlas-v2` / 3
- 2x2: signature dims=1.1493, resource dims=1.1308, resource mean/max |corr|=0.7754/0.9964, mean distance=0.1926, turnover=0.0571, lineage association=0.8663, social association=0.0000
- 4x4: signature dims=2.7723, resource dims=2.2287, resource mean/max |corr|=0.4586/0.5889, mean distance=0.2937, turnover=0.0591, lineage association=0.8485, social association=0.0000
- 8x8: signature dims=2.6669, resource dims=2.0116, resource mean/max |corr|=0.5519/0.6644, mean distance=0.3408, turnover=0.0642, lineage association=0.8136, social association=0.0000

### v037_selective300_sampled
- schema / scales: `multiscale-subject-environment-atlas-v2` / 3
- 2x2: signature dims=1.2954, resource dims=1.3258, resource mean/max |corr|=0.5912/0.9939, mean distance=0.1724, turnover=0.0575, lineage association=0.8931, social association=0.0000
- 4x4: signature dims=3.0590, resource dims=2.6485, resource mean/max |corr|=0.3403/0.4400, mean distance=0.2861, turnover=0.0608, lineage association=0.6777, social association=0.0000
- 8x8: signature dims=3.0885, resource dims=2.3767, resource mean/max |corr|=0.4344/0.5300, mean distance=0.3284, turnover=0.0657, lineage association=0.6428, social association=0.0000

## Repeated local directional patterns

- No local metric had the same non-zero sign in at least three runs.

## Repeated directional patterns

- No metric had the same non-zero sign in at least three runs.

## Interpretation boundary

Repeated signs across seeds support robustness, not necessity. Raw within-run correlations may reflect shared temporal drift. Controlled checkpoint interventions are required for phase-specific causal claims.
