# v0.14.0 Short Control Matrix

## Conditions

All primary runs used:

```text
backend: CPU reference
seed: 10001
ticks: 30
initial entities: 500
maximum entities: 768
working memory: enabled
L2 quantized router: enabled and costed
```

No 500-tick run was used.

## Fixed K=4 vs inherited capacity

The inherited condition used capacity levels `0, 1, 2, 4, 8`.

| Metric | Fixed K=4 | Inherited K |
|---|---:|---:|
| Final alive | 595 | 589 |
| Births | 95 | 89 |
| Mean energy | 2.004136 | 2.020876 |
| Candidate copy-work | 58,922 | 59,462 |
| Selected copy-work | 47,984 | 28,455 |
| Selected fraction | 81.44% | 47.85% |
| L2 MAC count | 16,878,272 | 9,884,280 |
| Routing energy | 0.738006 | 0.528154 |
| Selection energy | 0.001549 | 0.001164 |
| Knowledge-changed actions | 2,474 | 2,472 |

Relative to fixed K=4, inherited capacity reduced:

- L2 MAC count by **41.44%**;
- routing energy by **28.44%**.

The final alive difference is `-6` in this single seed and short horizon. It is
not evidence that fixed or inherited capacity is adaptively superior.

## Inherited capacity distribution

Across entity-ticks with at least one matching candidate:

| Requested K | Entity-ticks |
|---:|---:|
| 0 | 113 |
| 1 | 3,358 |
| 2 | 8,482 |
| 4 | 2,640 |
| 8 | 28 |

At tick 30, among entities with matching candidates:

| Requested K | Entities |
|---:|---:|
| 0 | 4 |
| 1 | 121 |
| 2 | 329 |
| 4 | 93 |
| 8 | 0 |

This demonstrates heterogeneous inherited capacity, not long-term evolution of
the distribution. Thirty ticks are too short for that conclusion.

## Determinism

The inherited condition was run twice independently:

- 235 common non-timing metrics fields: no differences;
- knowledge, outcome, contribution, routing-cost, selection, transfer,
  working-memory, and evolution logs: identical;
- tick 15 and 30 checkpoints: all 37 common arrays identical.

## v0.13 compatibility

With the fixed-capacity schema, v0.14 matched the v0.13 Top-k=4 run:

- 231 common non-timing metrics fields: no differences;
- common fields in outcome, contribution, routing-cost, and selection logs:
  row-for-row identical;
- tick 15 and 30 checkpoints: all 37 common arrays identical.

The existing v0.13 selection counters retain their historical semantics.
New requested-capacity metrics are additional diagnostics.

## Paired checkpoint ablations

Both interventions branched at tick 15 from the inherited run and continued to
tick 30 with common prehistory and stable random streams.

### Working-memory ablation

| Final metric delta, intervention − baseline | Value |
|---|---:|
| Alive | +18 |
| Births | +18 |
| Mean energy | -0.086882 |
| Working-memory committed energy | -0.015106 |
| Routing committed energy | +0.001743 |

This proves causal influence in the tested trajectory. It does not show that
memory is generally harmful: the intervention simultaneously removes memory
state, future updates, and their costs.

### Sparse-selection bypass

| Final metric delta, intervention − baseline | Value |
|---|---:|
| Alive | +3 |
| Births | +3 |
| Mean energy | -0.019153 |
| Selection committed energy | -0.000686 |
| Routing committed energy | +0.215273 |
| Cumulative knowledge-changed-action count | -5 |

Bypassing selection removed no knowledge copies. It substantially increased
routing energy because all matching copies reached L2.

## Validation limits

- one seed;
- 30 ticks;
- CPU reference only;
- no real CUDA world parity;
- no claim of adaptive superiority or subjecthood.
