# Next experiment: D3-B

Run the conservative intake substrate with three independent seeds:

```bash
se-d3-conservative-intake \
  --config configs/mvp_short_d3b_conservative_intake_longrun.json \
  --seeds 54001,54002,54003 \
  --output analyses/d3b_conservative_intake_1500 \
  --backend gpu \
  --until-tick 1500
```

Interpretation order:

1. post-assimilation overflow must remain at floating-point tolerance;
2. capacity rejection should occur when stores are full and must not debit the environment;
3. internal store ledgers must remain closed;
4. compare external resource dimensionality and population persistence descriptively with D3-A, but do not treat different seeds as a paired causal estimate;
5. if the corrected substrate remains active, design a conserved external waste/death-material pool before adding entity consumption or trophic roles.
