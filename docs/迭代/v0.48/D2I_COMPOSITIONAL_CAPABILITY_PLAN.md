# D2-I compositional capability run plan

This is a generative mechanism comparison, not another module-copy or niche pass/fail gate.

## Run

```bash
se-d2-compose \
  --config configs/mvp_short_d2i_compositional_harvest_longrun.json \
  --seeds 48001,48002,48003 \
  --output analyses/d2i_compositional_capability_1500 \
  --backend gpu \
  --until-tick 1500
```

Each seed starts two fresh populations with the same v2 genome distribution, world seed, mutation streams and explicit coupling costs:

- `composition-active`: inherited feed-forward module coupling is active;
- `coupling-neutral`: the same coupling genes remain inherited, mutate and incur structure cost, but their routed modulation is disabled from tick 0.

## Questions, not a binary gate

1. Are coupling genes actually used at entity level?
2. Are two or more downstream hierarchy levels active, or does one slot still dominate?
3. Does composition change contribution dominance, cancellation or functional harvest-preference dimensionality?
4. Does the effect persist through evolution rather than appearing only at initialization?

Interpretation is diagnostic:

- no mediated signal → expression, mutation or cost calibration is the bottleneck;
- mediated signal without more functional variation → the harvest-only output vocabulary is the bottleneck;
- mediated signal with broader persistent functional variation → retain v2 populations and only then revisit environment matching;
- endpoint divergence without functional variation → trajectory amplification, not differentiation.

No outcome changes module copy number or establishes an ecological niche.
