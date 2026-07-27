# D2 lineage-balanced paired audit plan

Schema: `d2-lineage-paired-plan-v2`
Post-intervention horizon: **300 ticks**
Fixed modules: `2, 3`

## Confirmation design

Source screen horizon: **120 ticks**
Selection rule: `module-level-screen-preserve-all-preselected-checkpoint-lineage-pairs-v1`
Outcome-conditioned pair selection: **False**

| Run | Phase | Checkpoint | Active | Effective lineages | Dominant share | Selected | Eligible |
|---|---|---:|---:|---:|---:|---:|---:|
| seed_10001 | peak | 2640 | 489 | 2.3380 | 0.5971 | 4 | True |
| seed_10001 | trough | 2820 | 463 | 2.2064 | 0.6134 | 4 | True |
| seed_10002 | peak | 2880 | 575 | 1.9451 | 0.6922 | 4 | True |
| seed_10002 | trough | 3000 | 582 | 1.7153 | 0.7457 | 4 | True |
| seed_10003 | peak | 2760 | 454 | 3.7665 | 0.4736 | 4 | True |
| seed_10003 | trough | 2880 | 448 | 3.5284 | 0.4933 | 4 | True |

## Branches per module-lineage pair

- `baseline`: output and expression cost retained
- `output-neutral`: output removed, expression cost retained
- `expression-neutral`: output and expression cost removed

> Selection uses pre-intervention lineage membership only. No lineage is rewarded, protected, created, or reweighted inside the world.
