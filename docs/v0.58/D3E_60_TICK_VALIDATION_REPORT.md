# D3-E 60-tick validation

Schema: `d3e-60-tick-validation-report-v1`

Seeds: `[58001, 58002]`; horizon: `60` ticks.

| Seed | Shared checkpoint | Active alive | Neutral alive | Active converted | Neutral converted | Active cost | Neutral cost |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 58001 | True | 490 | 491 | 1976.1188922230044 | 2022.7640922118676 | 3.9522377844460097 | 4.045528184423736 |
| 58002 | True | 496 | 497 | 2075.628665182563 | 2138.3711570907844 | 4.151257330365126 | 4.27674231418157 |

## Substrate checks

- shared tick0 checkpoint in every pair: `True`
- processing cost observed in every branch: `True`
- spatial support exposure nonuniform in every active branch: `True`
- neutral support exactly one in every ablation branch: `True`
- support limited processing observed in every active branch: `True`
- support accelerated processing observed in every active branch: `True`
- external resource ledger valid in every branch: `True`
- external recycling ledger valid in every branch: `True`

Recommendation: `retain-costed-spatial-processing-substrate-and-audit-response`

The two seeds show lower active-branch conversion and one fewer survivor than their neutral branches at tick 60. These are paired finite-horizon observations, not a general fitness, migration, specialization, or coexistence result.

D3-E tests whether location-dependent abiotic processing support can constrain or accelerate internal conversion while retaining explicit energy cost and conservative resource ledgers. It does not establish migration, collection-processing specialization, coexistence, trophic transfer, or named ecological roles.
