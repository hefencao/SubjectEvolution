# D2-L run plan

Run three independent v5 populations for 1500 ticks:

```bash
se-d2-regulatory-physiology \
  --config configs/mvp_short_d2l_regulatory_physiology_longrun.json \
  --seeds 51001,51002,51003 \
  --output analyses/d2l_regulatory_physiology_1500 \
  --backend gpu \
  --until-tick 1500
```

This is not an expression or ecological pass/fail audit. Preserve the resulting checkpoints as candidate populations for the later ecological-chain implementation. The report records whether inherited physiological variation, messenger turnover, finite precursor use, computation cost, fatigue turnover and damage/repair fluxes remain active.

Do not interpret seed-level endpoint differences as proof of a named organ or niche. Counterfactual receptor blockade and state clamps should be used only when a concrete evolved chain is selected for mechanistic follow-up.
