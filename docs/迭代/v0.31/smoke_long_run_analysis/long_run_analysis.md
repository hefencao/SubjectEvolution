# Multi-seed long-run analysis

Schema: `multi-seed-long-run-analysis-v10`
Runs: **1**

> This report is observational. Raw correlations, first differences and partial correlations do not identify an in-world causal mechanism.

| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Affinity dims | Transfer commits | Transferred roots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v031_d0_smoke | 120 | 163 | 134.8680 | 0.0184 | 61.6764 | 1.9134 | 0.0000 | 2.9679 | 45 | 35.0000 |

## Within-run raw observational correlations

### v031_d0_smoke
- `mortality_vs_same_window_cohesion`: —
- `mortality_vs_next_window_cohesion`: —
- `effective_lineages_vs_cohesion`: —
- `largest_lineage_fraction_vs_cohesion`: —
- `strategy_dimensions_vs_action_entropy`: —
- `lineage_group_nmi_vs_cohesion`: —
- `lineage_group_pair_enrichment_vs_cohesion`: —
- `knowledge_effective_roots_vs_effective_lineages`: —

## First-difference checks

### v031_d0_smoke
- `delta_mortality_vs_delta_cohesion`: —
- `mortality_vs_next_delta_cohesion`: —
- `delta_effective_lineages_vs_delta_cohesion`: —
- `delta_largest_lineage_fraction_vs_delta_cohesion`: —
- `delta_strategy_dimensions_vs_delta_action_entropy`: —
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: —

## Partial correlations controlling tick and alive

### v031_d0_smoke
- `mortality_vs_cohesion_controlling_tick_alive`: —
- `effective_lineages_vs_cohesion_controlling_tick_alive`: —
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: —
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: —

## Costed cultural transfer

### v031_d0_smoke
- proposals / admitted attempts / committed / bytes: 56 / 56 / 45 / 2888
- committed cross-lineage / cross-group: 44 / 0
- active/effective transferred roots: 35 / 35.0000
- cultural-spread interpretable: True

## Environment process, danger evidence, mortality trace and group refresh

### v031_d0_smoke
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.004827 / 0.252842
- group refresh mode / updates / skipped: adaptive-topology-v1 / 2 / 118
- group label schema / rounds / trust / min members: trusted-directed-fixed-round-min-label-v1 / 8 / 0.12 / 6
- spatial partition: normalized-fixed-count-grid-v1 4x4, physical=32.0x32.0, cells=8.0x8.0, aligned=True

## Execution backend context

- `v031_d0_smoke`: requested=cpu, execution=cpu, gpu_semantics=strict-reference, device_validated=False, acceleration=False

## Local spatial stress panel

### v031_d0_smoke
- unavailable: fewer than five spatial diagnostic windows

## Local cultural transfer panel

### v031_d0_smoke
- unavailable: no local culture diagnostics

## Candidate-subject succession diagnostics

### v031_d0_smoke
- schema: `stable-membership-subject-succession-v1`
- refreshes / active / effective groups: 2 / 0 / 0.0000
- weighted predecessor Jaccard / inheritance: 0.0000 / 0.0000
- cumulative splits / merges / formations / dissolutions: 0 / 0 / 0 / 0

## Orthogonal resource environment

### v031_d0_smoke
- schema: `orthogonal-four-resource-niche-v1`
- final resource effective dimensions: 3.5183
- final resource mean/max absolute correlation: 0.1968 / 0.3284
- cycle periods: [173, 257, 349, 431]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]

## Multiscale subject–environment atlas

### v031_d0_smoke
- schema / scales: `multiscale-subject-environment-atlas-v2` / 3
- 2x2: signature dims=1.8176, resource dims=1.8367, resource mean/max |corr|=0.3903/0.8885, mean distance=0.2728, turnover=0.0397, lineage association=1.0000, social association=0.0000
- 4x4: signature dims=4.2468, resource dims=3.9149, resource mean/max |corr|=0.0535/0.1209, mean distance=0.4096, turnover=0.0499, lineage association=1.0000, social association=0.0000
- 8x8: signature dims=4.3994, resource dims=3.9209, resource mean/max |corr|=0.0658/0.1545, mean distance=0.4552, turnover=0.0553, lineage association=1.0000, social association=0.0000

## Repeated local directional patterns

- No local metric had the same non-zero sign in at least three runs.

## Repeated directional patterns

- No metric had the same non-zero sign in at least three runs.

## Interpretation boundary

Repeated signs across seeds support robustness, not necessity. Raw within-run correlations may reflect shared temporal drift. Controlled checkpoint interventions are required for phase-specific causal claims.
