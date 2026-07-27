# v0.39 D2-A long-run plan

## Main run

```bash
se-multi \
  --config configs/mvp_short_d2a_contextual_harvest_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/d2a_contextual_harvest_multiseed \
  --backend gpu \
  --checkpoint-ticks 2400,2640,2760,2820,2880,3000 \
  --until-tick 3000
```

The explicit checkpoint union is based on the supplied D1 trajectory and is a
convenience, not a phase claim for D2. Periodic 60-tick checkpoints remain
enabled, so a D2-specific phase plan can select other ticks.

## Analysis

```bash
python -m se.analysis.long_run \
  runs/d2a_contextual_harvest_multiseed/seed_10001/evolution_progress.jsonl \
  runs/d2a_contextual_harvest_multiseed/seed_10002/evolution_progress.jsonl \
  runs/d2a_contextual_harvest_multiseed/seed_10003/evolution_progress.jsonl \
  --output analyses/d2a_contextual_harvest
```

## Required paired branches

For each seed, select at least peak and trough checkpoints from a complete
observed population cycle. From each checkpoint run:

- baseline;
- `neutralize-functional-modules`.

Recommended horizon: 120–240 ticks. Preserve genotype and keyed randomness.

## Gate for structural mutation

Do not add module duplication/deletion or arbitrary output ports unless at least
two seeds satisfy all of:

1. non-zero module residual persists across multiple windows;
2. input/output topology retains non-trivial dimensions;
3. module-neutralization changes at least one downstream outcome repeatedly;
4. the effect is not explained solely by extraction efficiency or total request
   volume;
5. module maintenance/development cost remains measurable;
6. environment and capacity axes do not collapse to a single complexity factor.
