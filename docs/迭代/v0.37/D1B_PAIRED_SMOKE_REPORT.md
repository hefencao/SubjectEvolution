# D1-B 300-tick paired smoke

Common condition: CPU reference, seed 10001, D1 elastic capacities, D0
orthogonal environment.  The only configuration difference is harvest
allocation schema.

| Metric | Uniform four-channel requests | Affinity-sampled exclusive | Difference |
|---|---:|---:|---:|
| Final alive | 134 | 115 | -19 |
| Final mean energy | 1.3738 | 1.5500 | +0.1762 |
| Resource effective dimensions | 1.4897 | 1.8248 | +0.3351 |
| Resource mean absolute correlation | 0.7442 | 0.6083 | -0.1359 |
| Demand temporal effective dimensions | 1.2015 | 2.0816 | +0.8801 |
| Demand mean absolute correlation | 0.8758 | 0.5224 | -0.3534 |
| Mean realized/requested extraction efficiency | 0.9415 | 0.9093 | -0.0322 |
| Final realized/requested extraction efficiency | 0.9043 | 0.8713 | -0.0330 |
| Capacity effective dimensions | 3.8081 | 3.8532 | +0.0451 |

The selective rule materially delays the common-demand collapse and causes
window-level resource demand to diverge.  It also lowers extraction efficiency
and final population in this short single-seed run.  This is the intended
tradeoff boundary, not evidence that either allocation is adaptively superior.

The paired smoke is not a checkpoint intervention: trajectories diverge from
tick zero because demand semantics differ.  Causal phenotype claims require a
shared-checkpoint `neutralize-resource-affinity` branch within the selective
schema.
