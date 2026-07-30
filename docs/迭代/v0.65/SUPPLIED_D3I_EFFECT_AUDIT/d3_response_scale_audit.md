# D3-I nested matched-response effect audit

Schema: `d3-response-scale-audit-v2`

| Scale | Result schema | Panels | Acute eligible | Matched eligible | Seeds | Original gain | Reversed gain | Both-positive seed fraction | Replication gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1p5-fixed-gpu | d3-processing-response-panel-results-v2 | 32 | 31 | 31 | 8 | -7.585360200717007e-07 | -4.841683726372987e-08 | 0.25 | False |

## Replication contract

- minimum independent seeds per scale: `8`
- minimum positive seed fraction per orientation: `0.75`
- minimum both-orientation-positive seed fraction: `0.75`
- checkpoints are equally weighted within each seed
- seeds are equally weighted within each scale
- windows and movement events are not independent replicates

## 1p5-fixed-gpu seed summaries

| Seed | Checkpoints | Original gain | Reversed gain | Original positive checkpoints | Reversed positive checkpoints | Both positive |
|---:|---:|---:|---:|---:|---:|---:|
| 63001 | 4 | -1.1572696775131972e-05 | 1.3251264624355598e-05 | 0.25 | 0.75 | False |
| 63002 | 4 | -2.099589413269962e-06 | -2.9490012347678304e-06 | 0.25 | 0.5 | False |
| 63003 | 4 | 5.41297356319512e-06 | 1.7557565092463736e-05 | 0.75 | 0.75 | True |
| 63004 | 4 | -1.0604318147864795e-05 | 9.171874923958435e-06 | 0.25 | 0.75 | False |
| 63005 | 4 | 2.5033108915216055e-06 | -1.3290257818795769e-05 | 0.5 | 0.0 | False |
| 63006 | 4 | 8.184954649777827e-06 | 8.326879565352858e-06 | 0.75 | 0.75 | True |
| 63007 | 4 | 3.1255827999476225e-06 | -2.804205757151567e-06 | 0.5 | 0.25 | False |
| 63008 | 3 | -1.0185057287490536e-06 | -2.9651454093525302e-05 | 0.3333333333333333 | 0.3333333333333333 | False |

Recommendation: `matched-effect-not-directionally-replicated-do-not-add-response-mechanism`

Only active-minus-neutral contrasts under the same support observation orientation isolate support execution. Seed means use equal checkpoint weighting and scale means use equal seed weighting; movement counts do not increase the independent sample size. Exact sign-flip values are descriptive. No result here establishes evolutionary adaptation, migration, specialization, coexistence, or ecological roles.
