# D3-A result interpretation

The supplied `d3-resource-metabolism-results-v1` contains three 1500-tick runs using resource physiology v4.

## Supported observations

- all four raw channels entered inherited stores and were converted in every seed;
- storage/conversion genetic variation remained non-zero;
- the internal store ledger closed in every seed;
- conversion was approximately 92.97%–93.29% of cumulative stored material;
- final mean store occupancy was approximately 0.607–0.647.

These observations support retaining delayed conversion and inherited buffering.

## Invalid environmental-loss boundary

The cumulative post-harvest overflow divided by cumulative successfully stored material was:

| Seed | Alive | Overflow / stored | Overflow / attempted assimilation | Environment resource dimensions |
|---:|---:|---:|---:|---:|
| 53001 | 79 | 0.621597 | 0.383324 | 1.182794 |
| 53002 | 54 | 0.594195 | 0.372724 | 1.161532 |
| 53003 | 50 | 0.600047 | 0.375018 | 1.180667 |

In resource-v4, environmental extraction was committed before inherited storage capacity was applied. Overflow therefore left the external field but did not enter the entity, detritus, or another external pool. This was explicit in the body ledger but not conservative at the world boundary.

The low final populations and low external resource effective dimensions cannot be cleanly attributed to delayed metabolism while this additional sink exists.

## Decision

Retain inherited stores and delayed conversion. Do not interpret D3-A demographic endpoints. Correct environmental intake before adding detritus or spatial processing, because an external recycling layer built on top of an artificial pre-recycling sink would preserve the wrong mass boundary.
