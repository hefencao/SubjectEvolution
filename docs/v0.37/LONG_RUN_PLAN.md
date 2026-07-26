# v0.37 long-run plan

## Primary run

```bash
se-multi \
  --config configs/mvp_short_d1b_selective_harvest_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/d1b_selective_harvest_multiseed \
  --backend gpu \
  --until-tick 1500
```

Analyze with the v0.37 package so the report schema is
`multi-seed-long-run-analysis-v12` and includes D1 capacity and realized demand
fields.

## Required checks

1. Resource effective dimensions must not rapidly return to approximately one.
2. Demand temporal dimensions and channel correlations must remain distinct
   across seeds, not only at one endpoint.
3. Report realized/requested extraction efficiency and demographic cost.
4. Report capacity means, distributions, utilization and saturation.
5. Test whether affinity and capacity dimensions collapse into one general
   complexity axis.
6. Stratify by environment phase, lineage turnover and generation.
7. Do not infer adaptation from raw endpoint correlations.

## Paired branches

From preregistered shared checkpoints run:

- `neutralize-resource-affinity`;
- `neutralize-elastic-capacities`;
- combined neutralization only as a separately declared interaction branch.

The affinity branch tests phenotype routing while retaining exclusive harvest
semantics.  The capacity branch tests D1 expression without changing affinity.

## Advance criterion

D2 remains blocked unless at least two seeds show:

- persistent nontrivial resource and demand dimensions;
- actual use of multiple capacity axes;
- environment-conditional phenotype effects or stable coexistence evidence;
- no unexplained population collapse caused solely by acquisition inefficiency.
