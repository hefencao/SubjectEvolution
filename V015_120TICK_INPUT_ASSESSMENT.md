# Assessment of the supplied v0.15 120-tick runs

The supplied JSONL files contain four scheduled records at ticks 30, 60, 90 and
120 for:

1. heterogeneous budget-matched environment without resource affinity;
2. the same environment with fixed-budget inherited affinity.

## Tick 120 comparison

| Metric | No affinity | Affinity | Difference |
|---|---:|---:|---:|
| Alive | 1020 | 1002 | -18 |
| Effective founder lineages | 356.301 | 352.035 | -4.266 |
| Largest lineage fraction | 0.00784 | 0.00699 | -0.00086 |
| Strategy effective dimensions | 85.129 | 84.896 | -0.233 |
| Active morphology effective dimensions | 1.961 | 5.719 | +3.758 |
| Resource-affinity effective dimensions | 0 | 2.965 | +2.965 |
| Window action entropy | 1.96588 | 1.96463 | -0.00125 |
| Boundary cohesion | 0.2678 | 0.2897 | +0.0219 |

Four-channel harvested shares remain close in both conditions, approximately
`23–27%` per channel.

## Interpretation

The run supports **mechanism activation**: affinity changes the active
morphology covariance rank from roughly two to nearly six dimensions while the
fixed-budget affinity subspace uses nearly three dimensions.

It does not yet support **long-term ecological improvement**:

- population and founder-lineage differences are small and seed-specific;
- strategy effective dimensions and action entropy are almost unchanged;
- cohesion changes sign across the four windows and cannot be attributed to
  affinity from this pair alone;
- 120 ticks is far shorter than the approximately 390-tick population cycle
  observed in the previous 3000-tick legacy runs.

The correct next test is multi-seed long-horizon selection diagnostics, not
another immediate increase in network depth or mutation amplitude.
