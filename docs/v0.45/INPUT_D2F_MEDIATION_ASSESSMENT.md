# D2 lineage temporal mediation assessment

Schema: `d2-lineage-mediation-assessment-v1`
Observation offsets: `30, 60, 120, 180, 240, 300` ticks

## Decision standard

1. Offsets are repeated observations, not independent replicates.
2. Replication is counted across seeds and non-dominant lineage identities within each offset.
3. Mean energy is interpreted with total energy, harvest/share flows and demography.
4. Routed-output effects qualify; retained-cost and total-expression effects remain separate.
5. Module copy number remains blocked by the source-lineage guard.

| Module | Source endpoint reproduced | Classification | Mean-energy onset | Harvest onset | Shared-energy onset | Demographic conversion | Demographic cost |
|---:|---:|---|---:|---:|---:|---:|---:|
| 3 | False | `source-endpoint-effect-not-reproduced` | 120 | 240 | 180 | True | True |

- `module_3` total-energy support: `180`
- `module_3` sign reversals: `target_lineage.births_since_intervention, target_lineage.descendants_alive, target_lineage.mean_age, target_lineage.mean_fertility`
- `module_3` recommendation: `stop-and-audit-endpoint-reproducibility`

## Lineage guard

- median effective lineages: `2.2721965512968487`
- minimum effective lineages: `1.7153187825998886`
- median dominant share: `0.6052639715203152`
- dominant-lineage risk: `True`

## Recommendation

`causal-chain-supported-redesign-source-population-before-copy-number`

Observation offsets are repeated measurements of the same checkpoint-lineage pair and cannot inflate the replicate count. A target-lineage mean-energy difference is not interpreted as ecological improvement unless total energy, input flows and demographic conversion are reported alongside it. Copy number remains blocked independently by the source-lineage guard.
