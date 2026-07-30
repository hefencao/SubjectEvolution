# Exploration readiness and sample adequacy

Schema: `exploration-readiness-audit-v1`

| Run | Final alive | Descendants | Effective parents | Founder lineages | Strategy dimensions | Within-run support | Source ready |
|---|---:|---:|---:|---:|---:|---:|---:|
| seed_70001 | 24951 | 1.0 | 2414.2852784134247 | 35.21210643602199 | 27.40291619867307 | True | False |
| seed_70002 | 23533 | 1.0 | 2277.9794014768754 | 13.925564617531833 | 13.381871332824291 | True | False |
| seed_70003 | 28523 | 1.0 | 2479.834403997145 | 19.283212442147335 | 16.752658770442675 | True | False |

## Diagnosis

- within-run observational support: `True`
- independent seed count: `3`
- confirmation-level independent replication: `False`
- sample issue present: `True`
- independent-seed count is below the confirmation threshold
- founder-lineage breadth is insufficient for a stable source claim
- no common future source rule is supported across runs

## Exploration policy

- smoke: 2 seeds, at most 512 initial entities and 180 ticks
- screen: at least 8 seeds, at most 2048 initial entities and 600 ticks
- replication: at least 8 disjoint seeds, at most 4096 initial entities and 900 ticks
- large long runs: confirmation only, after screen and replication

Recommendation: `use-tiered-small-panel-exploration-add-independent-seeds-before-confirmation`

Large trajectories may establish demographic and runtime behavior, but repeated windows, entities, births, and moves are not independent confirmation samples. Exploration should use cheaper independent-seed panels; large long runs are reserved for promoted candidates on new seeds.
