# D2 lineage temporal mediation plan

Schema: `d2-lineage-mediation-plan-v1`
Modules: `3`
Observation offsets: `30, 60, 120, 180, 240, 300` ticks
Selection rule: `module-level-confirmed-output-preserve-all-preselected-checkpoint-lineage-pairs-v1`
Source assessment SHA-256: `855e5a5f189085ca4a0e489feb77d43ba55284339fa62381b7330e2a0e50207a`
Source persistent expectations: `{'module_3': {'target_lineage.mean_energy': 1}}`
Outcome-conditioned pair selection: **False**

| Run | Phase | Checkpoint | Selected lineages | Effective lineages | Dominant share |
|---|---|---:|---:|---:|---:|
| seed_10001 | peak | 2640 | 4 | 2.3380 | 0.5971 |
| seed_10001 | trough | 2820 | 4 | 2.2064 | 0.6134 |
| seed_10002 | peak | 2880 | 4 | 1.9451 | 0.6922 |
| seed_10002 | trough | 3000 | 4 | 1.7153 | 0.7457 |
| seed_10003 | peak | 2760 | 4 | 3.7665 | 0.4736 |
| seed_10003 | trough | 2880 | 4 | 3.5284 | 0.4933 |

## Read-only mediator trajectory

- energy stock: mean, total and quartiles;
- demography: source survivors, living descendants, births and deaths by cause;
- conversion: fertility and reproduction-ready count;
- flows: harvested and shared energy accumulated after intervention;
- all three paired branches retain the existing output/cost/total decomposition.

> The plan selects a confirmed module only and preserves every preselected checkpoint-lineage pair. It does not select responsive lineages.
