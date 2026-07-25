# Multi-seed long-run analysis

Schema: `multi-seed-long-run-analysis-v1`
Runs: **3**

> This report is observational. Correlation does not identify an in-world causal mechanism.

| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Lineage-group NMI | Pair enrichment |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| seed_10001 | 1500 | 1381 | 17.3257 | 0.1760 | 15.7431 | 1.7241 | 0.3791 | 0.5469 | 3.6218 |
| seed_10002 | 1500 | 1337 | 22.3203 | 0.0957 | 19.5730 | 1.7425 | 0.4178 | 0.5600 | 4.7385 |
| seed_10003 | 1500 | 1341 | 22.1673 | 0.1156 | 20.0626 | 1.7500 | 0.4184 | 0.5380 | 4.3413 |

## Within-run observational correlations

### seed_10001
- `mortality_vs_same_window_cohesion`: 0.6209
- `mortality_vs_next_window_cohesion`: 0.6490
- `effective_lineages_vs_cohesion`: -0.8727
- `largest_lineage_fraction_vs_cohesion`: 0.4559
- `strategy_dimensions_vs_action_entropy`: 0.9727
- `lineage_group_nmi_vs_cohesion`: 0.2174
- `lineage_group_pair_enrichment_vs_cohesion`: -0.2513
- `knowledge_effective_roots_vs_effective_lineages`: -0.4900

### seed_10002
- `mortality_vs_same_window_cohesion`: 0.3435
- `mortality_vs_next_window_cohesion`: 0.3629
- `effective_lineages_vs_cohesion`: -0.8715
- `largest_lineage_fraction_vs_cohesion`: 0.6673
- `strategy_dimensions_vs_action_entropy`: 0.9820
- `lineage_group_nmi_vs_cohesion`: 0.2090
- `lineage_group_pair_enrichment_vs_cohesion`: -0.2920
- `knowledge_effective_roots_vs_effective_lineages`: -0.5160

### seed_10003
- `mortality_vs_same_window_cohesion`: 0.4240
- `mortality_vs_next_window_cohesion`: 0.4025
- `effective_lineages_vs_cohesion`: -0.8958
- `largest_lineage_fraction_vs_cohesion`: 0.7827
- `strategy_dimensions_vs_action_entropy`: 0.9787
- `lineage_group_nmi_vs_cohesion`: 0.3389
- `lineage_group_pair_enrichment_vs_cohesion`: -0.0282
- `knowledge_effective_roots_vs_effective_lineages`: -0.5140

## Interpretation boundary

A repeated directional trend across seeds supports robustness, not necessity. Divergent lineage outcomes are expected evidence of path dependence until controlled checkpoint interventions are run.
