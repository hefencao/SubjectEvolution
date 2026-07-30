# Multi-seed long-run analysis

Schema: `multi-seed-long-run-analysis-v9`
Runs: **1**

> This report is observational. Raw correlations, first differences and partial correlations do not identify an in-world causal mechanism.

| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Affinity dims | Transfer commits | Transferred roots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v030_subject_env_smoke_final | 30 | 568 | 458.2727 | 0.0035 | 89.6980 | 1.9608 | 0.0000 | 2.9821 | 69 | 63.4800 |

## Within-run raw observational correlations

### v030_subject_env_smoke_final
- `mortality_vs_same_window_cohesion`: —
- `mortality_vs_next_window_cohesion`: —
- `effective_lineages_vs_cohesion`: —
- `largest_lineage_fraction_vs_cohesion`: —
- `strategy_dimensions_vs_action_entropy`: —
- `lineage_group_nmi_vs_cohesion`: —
- `lineage_group_pair_enrichment_vs_cohesion`: —
- `knowledge_effective_roots_vs_effective_lineages`: —

## First-difference checks

### v030_subject_env_smoke_final
- `delta_mortality_vs_delta_cohesion`: —
- `mortality_vs_next_delta_cohesion`: —
- `delta_effective_lineages_vs_delta_cohesion`: —
- `delta_largest_lineage_fraction_vs_delta_cohesion`: —
- `delta_strategy_dimensions_vs_delta_action_entropy`: —
- `delta_lineage_group_pair_enrichment_vs_delta_cohesion`: —

## Partial correlations controlling tick and alive

### v030_subject_env_smoke_final
- `mortality_vs_cohesion_controlling_tick_alive`: —
- `effective_lineages_vs_cohesion_controlling_tick_alive`: —
- `largest_lineage_fraction_vs_cohesion_controlling_tick_alive`: —
- `lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive`: —

## Costed cultural transfer

### v030_subject_env_smoke_final
- proposals / admitted attempts / committed / bytes: 84 / 84 / 69 / 4232
- committed cross-lineage / cross-group: 69 / 0
- active/effective transferred roots: 66 / 63.4800
- cultural-spread interpretable: True

## Environment process, danger evidence, mortality trace and group refresh

### v030_subject_env_smoke_final
- environment process: disabled (core-disabled)
- mechanism / interpretation: none / scientific-core-only
- process parameter names: []
- v0.22 moving-hazard compatibility fields / sources: disabled / 0
- danger evidence schema: disabled
- direct mean/std: 1.0000 / 0.0000
- trace mean/std: 1.0000 / 0.0000
- mortality trace mean/max: 0.000000 / 0.000000
- group refresh mode / updates / skipped: adaptive-topology-v1 / 1 / 29
- group label schema / rounds / trust / min members: trusted-directed-fixed-round-min-label-v1 / 8 / 0.12 / 6
- spatial partition: normalized-fixed-count-grid-v1 4x4, physical=32.0x32.0, cells=8.0x8.0, aligned=True

## Execution backend context

- `v030_subject_env_smoke_final`: requested=cpu, execution=cpu, gpu_semantics=strict-reference, device_validated=False, acceleration=False

## Local spatial stress panel

### v030_subject_env_smoke_final
- unavailable: fewer than five spatial diagnostic windows

## Local cultural transfer panel

### v030_subject_env_smoke_final
- unavailable: no local culture diagnostics

## Candidate-subject succession diagnostics

### v030_subject_env_smoke_final
- schema: `stable-membership-subject-succession-v1`
- refreshes / active / effective groups: 1 / 0 / 0.0000
- weighted predecessor Jaccard / inheritance: 0.0000 / 0.0000
- cumulative splits / merges / formations / dissolutions: 0 / 0 / 0 / 0

## Multiscale subject–environment atlas

### v030_subject_env_smoke_final
- schema / scales: `multiscale-subject-environment-atlas-v1` / 3
- 2x2: signature dims=1.9140, mean distance=0.4381, turnover=0.0000, lineage association=1.0000, social association=0.0000
- 4x4: signature dims=2.2961, mean distance=0.4837, turnover=0.0000, lineage association=0.9937, social association=0.0000
- 8x8: signature dims=2.8259, mean distance=0.5351, turnover=0.0000, lineage association=0.9967, social association=0.0000

## Repeated local directional patterns

- No local metric had the same non-zero sign in at least three runs.

## Repeated directional patterns

- No metric had the same non-zero sign in at least three runs.

## Interpretation boundary

Repeated signs across seeds support robustness, not necessity. Raw within-run correlations may reflect shared temporal drift. Controlled checkpoint interventions are required for phase-specific causal claims.
