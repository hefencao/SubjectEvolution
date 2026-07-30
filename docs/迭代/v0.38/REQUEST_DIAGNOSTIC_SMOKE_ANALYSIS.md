# Multi-seed long-run analysis

Schema: `multi-seed-long-run-analysis-v13`
Analyzer: `0.38.0`
Input runtimes: `['0.38.0']`
Runs: **1**

> This report is observational. Raw correlations, first differences and partial correlations do not identify an in-world causal mechanism.

| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Affinity dims | Transfer commits | Transferred roots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v038_smoke | 60 | 205 | 181.9264 | 0.0098 | 69.8544 | 1.9286 | 0.0000 | 2.9276 | 19 | 18.0000 |

## Within-run raw observational correlations

### v038_smoke
- `mortality_vs_same_window_cohesion`: —
- `mortality_vs_next_window_cohesion`: —
- `effective_lineages_vs_cohesion`: —
- `largest_lineage_fraction_vs_cohesion`: —
- `strategy_dimensions_vs_action_entropy`: —
- `lineage_group_nmi_vs_cohesion`: —
- `lineage_group_pair_enrichment_vs_cohesion`: —
- `knowledge_effective_roots_vs_effective_lineages`: —

## First-difference checks

### v038_smoke
- `delta_mortality_vs_delta_cohesion`: —
- `mortality_vs_next_delta_cohesion`: —
- `delta_effective_lineages_vs_delta_cohesion`: —
- `delta_largest_lineage_fraction_vs_delta_cohesion`: —
- `delta_strategy_dimensions_vs_delta_action_entropy`: —
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: —

## Partial correlations controlling tick and alive

### v038_smoke
- `mortality_vs_cohesion_controlling_tick_alive`: —
- `effective_lineages_vs_cohesion_controlling_tick_alive`: —
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: —
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: —

## Costed cultural transfer

### v038_smoke
- proposals / admitted attempts / committed / bytes: 30 / 25 / 19 / 1128
- committed cross-lineage / cross-group: 19 / 0
- active/effective transferred roots: 18 / 18.0000
- cultural-spread interpretable: True

## Environment process, danger evidence, mortality trace and group refresh

### v038_smoke
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.001625 / 0.164675
- group refresh mode / updates / skipped: adaptive-topology-v1 / 1 / 59
- group label schema / rounds / trust / min members: trusted-directed-fixed-round-min-label-v1 / 8 / 0.12 / 6
- spatial partition: normalized-fixed-count-grid-v1 4x4, physical=32.0x32.0, cells=8.0x8.0, aligned=True

## Execution backend context

- `v038_smoke`: requested=cpu, execution=cpu, gpu_semantics=strict-reference, device_validated=False, acceleration=False

## Local spatial stress panel

### v038_smoke
- unavailable: fewer than five spatial diagnostic windows

## Local cultural transfer panel

### v038_smoke
- unavailable: no local culture diagnostics

## Inherited elastic capacities

### v038_smoke
- schema: `inherited-elastic-capacities-v1`
- effective dimensions: 3.9485
- working-memory dimensions mean/std: 2.0341 / 0.6580
- knowledge bytes mean/std: 262.7122 / 73.0390
- relation slots mean/std: 3.8683 / 1.1422
- attention slots mean/std: 0.9659 / 0.3874
- working-memory used/utilization/saturated: 2.0341 / 1.0000 / 1.0000
- knowledge bytes used/utilization/saturated: 248.0000 / 0.9298 / 0.2829
- relation edges used/utilization/saturated: 1.4829 / 0.4198 / 0.1415
- zero-attention fraction: 0.0927
- final maintenance/development energy step: — / —
- configured bounds: {'working_memory_dimensions': [0, 4], 'knowledge_bytes': [0, 512], 'relation_slots': [0, 8], 'knowledge_attention_slots': [0, 2]}
- selected observational correlations:
  - `capacity_dimensions_vs_alive`: —
  - `capacity_dimensions_vs_resource_environment_dimensions`: —
  - `capacity_dimensions_vs_resource_affinity_dimensions`: —
  - `capacity_dimensions_vs_boundary_cohesion`: —
  - `capacity_dimensions_vs_effective_transferred_roots`: —
  - `working_memory_capacity_vs_action_entropy`: —
  - `knowledge_capacity_vs_effective_root_contents`: —
  - `relation_capacity_vs_boundary_cohesion`: —
  - `attention_capacity_vs_committed_transfer`: —
- boundary: capacity–outcome correlations can reflect shared selection and demographic drift; paired capacity-expression interventions are required for causal claims.

## Candidate-subject succession diagnostics

### v038_smoke
- schema: `stable-membership-subject-succession-v1`
- refreshes / active / effective groups: 1 / 0 / 0.0000
- weighted predecessor Jaccard / inheritance: 0.0000 / 0.0000
- cumulative splits / merges / formations / dissolutions: 0 / 0 / 0 / 0

## Realized resource demand

### v038_smoke
- harvest allocation schema: `affinity-sampled-exclusive-harvest-v1`
- request observation schema: `explicit-requested-harvest-window-v1`
- realized channel shares: [0.2307, 0.249, 0.2505, 0.2697]
- requested channel shares: [0.2409, 0.2457, 0.2441, 0.2693]
- realized balance effective count: 3.9878
- requested balance effective count: 3.9919
- raw realized volume dimensions / mean |corr|: 1.0000 / 1.0000
- realized share-composition dimensions / mean |corr|: 1.0000 / 1.0000
- raw requested volume dimensions / mean |corr|: 1.0000 / 0.5000
- requested share-composition dimensions / mean |corr|: 1.0000 / 1.0000
- realized volume vs requested volume: —
- balance vs resource-field dimensions: —
- realized/requested extraction efficiency mean/final: 0.9675 / 0.9559

## Orthogonal resource environment

### v038_smoke
- schema: `orthogonal-four-resource-niche-v1`
- final resource effective dimensions: 3.9436
- final resource mean/max absolute correlation: 0.0564 / 0.1033
- cycle periods: [173, 257, 349, 431]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]

## Multiscale subject–environment atlas

### v038_smoke
- schema / scales: `multiscale-subject-environment-atlas-v2` / 3
- 2x2: signature dims=1.6650, resource dims=1.6828, resource mean/max |corr|=0.3843/0.8102, mean distance=0.3691, turnover=0.0469, lineage association=1.0000, social association=0.0000
- 4x4: signature dims=3.6190, resource dims=3.9277, resource mean/max |corr|=0.0317/0.0666, mean distance=0.5092, turnover=0.0537, lineage association=1.0000, social association=0.0000
- 8x8: signature dims=3.9380, resource dims=3.9752, resource mean/max |corr|=0.0279/0.0541, mean distance=0.5568, turnover=0.0595, lineage association=0.9945, social association=0.0000

## Repeated local directional patterns

- No local metric had the same non-zero sign in at least three runs.

## Repeated directional patterns

- No metric had the same non-zero sign in at least three runs.

## Interpretation boundary

Repeated signs across seeds support robustness, not necessity. Raw within-run correlations may reflect shared temporal drift. Controlled checkpoint interventions are required for phase-specific causal claims.
