# D1 paired smoke

A CPU reference run used seed 10001 and the D1 smoke configuration. A trusted tick-30 checkpoint was branched to an untreated baseline and `neutralize-elastic-capacities`; both branches ended at tick 60.

| Metric | Baseline | Neutralized | Delta |
|---|---:|---:|---:|
| Alive | 204 | 204 | +0 |
| Mean energy | 1.262094 | 1.274897 | +0.012803 |
| Total births | 6 | 6 | +0 |
| Total deaths | 2 | 2 | +0 |
| Active knowledge copies | 853 | 852 | -1 |
| Active knowledge bytes | 50,552 | 49,184 | -1,368 |
| Relation edges | 314 | 323 | +9 |
| Capacity effective dimensions | 3.9645 | 0.0000 | -3.9645 |

The intervention immediately evicted 122 knowledge copies at tick 30 because midpoint storage was below some inherited capacities. At tick 60 every treated living entity expressed `[2, 256, 4, 1]`, while the untreated branch retained variation across all four dimensions.

This is a mechanism smoke only. The 30-tick, one-seed downstream deltas do not identify adaptive value, ecological specialization or long-run selection.
