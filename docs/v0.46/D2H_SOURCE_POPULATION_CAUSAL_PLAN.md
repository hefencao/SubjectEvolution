# D2-H source-population module-3 causal re-audit plan

Schema: `d2-source-population-causal-plan-v1`
Stage: `120-tick-exploratory-screen`
Evidence scope: `phase-specific-exploratory-causal-reaudit`
Horizon: **120 ticks**
Selected phases: `peak`
Selected fresh-world seeds: `45001, 45003`
Modules: `3`

The panel selection uses only the preregistered D2-G qualification guards. Every eligible lineage in each frozen checkpoint is retained; no D2-G response magnitude is used to select a lineage.

# D2 lineage-balanced paired audit plan

Schema: `d2-lineage-paired-plan-v2`
Post-intervention horizon: **120 ticks**
Fixed modules: `3`

| Run | Phase | Checkpoint | Active | Effective lineages | Dominant share | Selected | Eligible |
|---|---|---:|---:|---:|---:|---:|---:|
| peak_seed_45001 | peak | 600 | 504 | 4.0688 | 0.4167 | 6 | True |
| peak_seed_45003 | peak | 600 | 483 | 4.3243 | 0.3892 | 6 | True |

## Branches per module-lineage pair

- `baseline`: output and expression cost retained
- `output-neutral`: output removed, expression cost retained
- `expression-neutral`: output and expression cost removed

> Selection uses pre-intervention lineage membership only. No lineage is rewarded, protected, created, or reweighted inside the world.
