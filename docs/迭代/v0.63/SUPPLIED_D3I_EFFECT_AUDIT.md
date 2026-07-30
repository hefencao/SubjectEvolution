# D3-I nested matched-response effect audit

Schema: `d3-response-scale-audit-v2`

| Scale | Result schema | Panels | Acute eligible | Matched eligible | Seeds | Original gain | Reversed gain | Both-positive seed fraction | Replication gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| scale1p5 | d3-processing-response-panel-results-v2 | 32 | 32 | 32 | 8 | -2.898296122704174e-06 | -5.477934432784455e-06 | 0.0 | False |
| scale2 | d3-processing-response-panel-results-v2 | 32 | 32 | 32 | 8 | 9.253429667044727e-07 | 6.064305225430936e-07 | 0.125 | False |

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
| 62001 | 4 | -5.653265320601928e-06 | 2.687147075736379e-06 | 0.5 | 0.5 | False |
| 62002 | 4 | 4.70598050731464e-06 | -1.1689697521084533e-05 | 0.5 | 0.5 | False |
| 62003 | 4 | -6.0887438486763665e-06 | 2.3648434730657266e-05 | 0.25 | 1.0 | False |
| 62004 | 4 | -1.0497330033443735e-05 | 4.045718387819581e-06 | 0.25 | 0.5 | False |
| 62005 | 4 | -5.846253135368662e-06 | -1.008296464158781e-05 | 0.25 | 0.25 | False |
| 62006 | 4 | -3.4528665398610525e-07 | -3.201559874678896e-05 | 0.5 | 0.0 | False |
| 62007 | 4 | 4.9807540518165975e-06 | -2.3413248232481277e-05 | 0.5 | 0.0 | False |
| 62008 | 4 | -4.442224548687833e-06 | 2.996733485453708e-06 | 0.25 | 0.5 | False |

## scale2 seed summaries

| Seed | Checkpoints | Original gain | Reversed gain | Original positive checkpoints | Reversed positive checkpoints | Both positive |
|---:|---:|---:|---:|---:|---:|---:|
| 62001 | 4 | -5.175110819252673e-06 | 9.224309835263738e-06 | 0.5 | 1.0 | False |
| 62002 | 4 | -1.537555977236148e-05 | -1.215388456149264e-06 | 0.0 | 0.5 | False |
| 62003 | 4 | 8.125079027873386e-06 | -2.5198060435078505e-06 | 0.75 | 0.5 | False |
| 62004 | 4 | 1.2056042211948363e-05 | -1.1201450738567316e-05 | 1.0 | 0.25 | False |
| 62005 | 4 | -4.0238850629916985e-06 | 8.848019870780628e-06 | 0.5 | 0.5 | False |
| 62006 | 4 | 5.865819497962444e-06 | 5.171314844755132e-06 | 0.75 | 0.75 | True |
| 62007 | 4 | 5.343607819494391e-06 | -3.24855614199656e-07 | 0.75 | 0.5 | False |
| 62008 | 4 | 5.867508309630491e-07 | -3.1306995180306644e-06 | 0.5 | 0.25 | False |

Recommendation: `matched-effect-not-directionally-replicated-do-not-add-response-mechanism`

Only active-minus-neutral contrasts under the same support observation orientation isolate support execution. Seed means use equal checkpoint weighting and scale means use equal seed weighting; movement counts do not increase the independent sample size. Exact sign-flip values are descriptive. No result here establishes evolutionary adaptation, migration, specialization, coexistence, or ecological roles.
