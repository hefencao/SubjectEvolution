# D1 long-run plan

Run the pre-registered D1-A configuration before implementing D2:

```bash
se-multi \
  --config configs/mvp_short_d1_elastic_capacities_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/d1_elastic_capacities_multiseed \
  --backend gpu \
  --until-tick 1500
```

Then analyze:

```bash
python -m se.analysis.long_run \
  runs/d1_elastic_capacities_multiseed/seed_10001/evolution_progress.jsonl \
  runs/d1_elastic_capacities_multiseed/seed_10002/evolution_progress.jsonl \
  runs/d1_elastic_capacities_multiseed/seed_10003/evolution_progress.jsonl \
  --output analyses/d1_elastic_capacities
```

## Primary checks

1. All four capacity traits retain non-trivial variation and actual use.
2. Means or distributions show selection response measured against generation and lineage turnover, not tick alone.
3. Capacity effective dimensions do not collapse immediately to one size axis.
4. Costs do not cause rapid extinction or make maximum capacity free.
5. Relationships, knowledge bytes, transfer admission and working-memory use respond to their own capacities.
6. Capacity–environment associations are conditional and repeat across seeds rather than reflecting only population drift.
7. The neutralized midpoint branch changes mechanism-proximal outcomes from shared checkpoints.

## Stop conditions

Do not proceed directly to D2 if:

- one capacity is never used or never limiting;
- every capacity fixes at the same boundary because costs are badly scaled;
- environment/resource dimensions collapse;
- capacity variation is explained only by one founder lineage;
- downstream differences disappear under expression neutralization;
- the population becomes non-viable before multiple generations occur.
