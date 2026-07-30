# Exploration readiness and sample adequacy

Schema: `exploration-readiness-audit-v2`

| Run | Initial | Final alive | Alive fraction | Effective lineages | Strategy dimensions | Paired source support | Long-horizon support |
|---|---:|---:|---:|---:|---:|---:|---:|
| seed_71101 | 1125 | 151 | 0.13422222222222221 | 124.59562841530054 | 57.72436328553811 | True | False |
| seed_71102 | 1125 | 157 | 0.13955555555555554 | 125.1218274111675 | 57.763296347518896 | True | False |
| seed_71103 | 1125 | 148 | 0.13155555555555556 | 115.28421052631575 | 57.863310278212296 | True | False |
| seed_71104 | 1125 | 154 | 0.1368888888888889 | 127.50537634408602 | 58.6692710686662 | True | False |
| seed_71105 | 1125 | 139 | 0.12355555555555556 | 118.53374233128834 | 56.4253420799181 | True | False |
| seed_71106 | 1125 | 138 | 0.12266666666666666 | 110.72093023255813 | 55.57262826994051 | True | False |
| seed_71107 | 1125 | 165 | 0.14666666666666667 | 136.80904522613065 | 60.53263056308321 | True | False |
| seed_71108 | 1125 | 150 | 0.13333333333333333 | 129.31034482758616 | 59.08488540526699 | True | False |

## Diagnosis

- independent seed count: `8`
- acute paired source checkpoints: `8`
- long-horizon supported runs: `0`
- common startup transient: `True`
- free-run endpoint is a candidate-effect measurement: `False`

## Exploration policy

- source checkpoint tick is fixed before branch outcomes are observed
- baseline and intervention start from the same full checkpoint
- screen and replication use disjoint independent seeds
- demographic turnover is not required for an acute paired mechanism screen
- large long runs remain confirmation-only

Recommendation: `reuse-fixed-checkpoints-for-paired-acute-screen-do-not-promote-free-run-endpoints`

A fixed checkpoint may support a short paired mechanism panel even when the free-running trajectory has not completed demographic turnover. The paired seed is the independent unit. Free-running endpoints, repeated windows, entities, births, and moves do not become candidate-effect replicates.
