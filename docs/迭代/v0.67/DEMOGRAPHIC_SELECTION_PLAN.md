# D3-J demographic-selection validity plan

Run three fixed seeds without population rescue:

```bash
se-multi \
  --config configs/mvp_d3j_gpu_scale4_demographic_audit.json \
  --seeds 67001,67002,67003 \
  --output analyses/d3j_scale4_demography \
  --backend auto \
  --until-tick 1200
```

Then audit every seed directory:

```bash
se-selection-validity-audit \
  --run 67001=analyses/d3j_scale4_demography/seed_67001 \
  --run 67002=analyses/d3j_scale4_demography/seed_67002 \
  --run 67003=analyses/d3j_scale4_demography/seed_67003 \
  --output analyses/d3j_scale4_demography/selection_validity
```

A trajectory that falls below 25% of its initial population before satisfying
generation-turnover requirements is retained as a bottleneck-dominated run. It
may still support mechanism, accounting and failure-mode analysis, but not an
effective-selection claim. Windows are repeated observations within a seed and
do not increase the independent sample count.
