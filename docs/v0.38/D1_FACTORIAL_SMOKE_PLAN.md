# D1 affinity × capacity factorial plan

Schema: `d1-affinity-capacity-factorial-plan-v1`
Post-intervention horizon: **10 ticks**

| Run | Phase | Target tick | Checkpoint | Until tick |
|---|---|---:|---:|---:|
| v038_factorial_source | peak | 50 | 60 | 70 |
| v038_factorial_source | trough | 80 | 20 | 30 |

## Branches

- `baseline`: inherited affinity and capacities expressed
- `affinity-neutral`: neutralize resource-affinity expression
- `capacity-neutral`: neutralize elastic-capacity expression
- `combined-neutral`: neutralize both expressions

> All branches start from the same trusted checkpoint and preserve genotype and keyed randomness.
