# D3-I nested matched-response effect audit

Schema: `d3-response-scale-audit-v2`

| Scale | Result schema | Panels | Acute eligible | Matched eligible | Seeds | Original gain | Reversed gain | Both-positive seed fraction | Replication gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| scale1p5 | d3-processing-response-panel-results-v2 | 12 | 12 | 12 | 3 | 6.47752786474193e-08 | -7.434496869115597e-06 | 0.0 | False |

## Replication contract

- minimum independent seeds per scale: `8`
- minimum positive seed fraction per orientation: `0.75`
- minimum both-orientation-positive seed fraction: `0.75`
- checkpoints are equally weighted within each seed
- seeds are equally weighted within each scale
- windows and movement events are not independent replicates

## scale1p5 seed summaries

| Seed | Checkpoints | Original gain | Reversed gain | Original positive checkpoints | Reversed positive checkpoints | Both positive |
|---:|---:|---:|---:|---:|---:|---:|
| 61001 | 4 | -6.13535695413714e-06 | -9.724851395485924e-06 | 0.25 | 0.25 | False |
| 61002 | 4 | 8.51957695502786e-06 | -4.254221135537801e-06 | 0.75 | 0.5 | False |
| 61003 | 4 | -2.189894164948463e-06 | -8.324418076323066e-06 | 0.5 | 0.5 | False |

Recommendation: `collect-more-independent-seeds-with-fixed-v2-protocol`

Only active-minus-neutral contrasts under the same support observation orientation isolate support execution. Seed means use equal checkpoint weighting and scale means use equal seed weighting; movement counts do not increase the independent sample size. Exact sign-flip values are descriptive. No result here establishes evolutionary adaptation, migration, specialization, coexistence, or ecological roles.
