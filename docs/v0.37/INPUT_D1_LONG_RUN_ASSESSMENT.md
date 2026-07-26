# Uploaded D1 long-run assessment

## Input boundary

The supplied aggregate contains three 1500-tick runs and identifies itself as
`multi-seed-long-run-analysis-v10`.  The D1 runtime configuration was used, but
this aggregate was produced by an analyzer predating the D1 capacity fields.
It therefore cannot establish long-run capacity distributions, utilization,
costs or capacity–outcome relations.

## Valid findings

Final population remained viable but substantially seed-dependent:

| Seed | Alive | Effective lineages | Strategy dimensions | Affinity dimensions |
|---|---:|---:|---:|---:|
| 10001 | 468 | 8.4246 | 9.7280 | 2.1137 |
| 10002 | 558 | 5.1839 | 5.6681 | 1.7890 |
| 10003 | 421 | 16.7731 | 15.3540 | 2.4163 |

The decisive D0 stop condition was reached after entities interacted with the
world:

| Seed | Final resource effective dimensions | Mean absolute channel correlation |
|---|---:|---:|
| 10001 | 1.3094 | 0.8125 |
| 10002 | 1.2703 | 0.8303 |
| 10003 | 1.2649 | 0.8337 |

The external resource generator was orthogonal in the no-entity audit, but the
historical harvest action requested all four channels together.  Population
extraction therefore recreated a common depletion axis.  High field
orthogonality before biological demand was not sufficient to preserve realized
ecological axes.

## Decision

D2 universal expression modules remain blocked.  v0.37 first changes resource
demand semantics so inherited affinity determines which resource channel an
entity attempts to extract on each harvest action.  The total requested budget
is unchanged, and the selected channel is sampled with state-free keyed
randomness.  This creates a measurable efficiency–differentiation tradeoff
without adding a free harvest advantage.

The v0.37 analyzer rejects D1 progress that lacks `capacity_*` fields and
publishes analyzer/runtime versions, realized demand dimensions, channel
correlations and extraction efficiency.
