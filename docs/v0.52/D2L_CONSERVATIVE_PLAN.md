# D2-L conservative rerun plan

- Seeds: `51001,51002,51003`
- Horizon: `1500` ticks
- Functional schema: `expression-gated-regulatory-physiology-v5`
- Physiology schema: `transport-metabolism-messenger-tissue-v3`
- Online weight learning: disabled
- Module maturity gate: disabled
- Named organs or hormones: absent
- Diversity reward or lineage protection: absent
- Module copy number: unchanged

Run:

```bash
se-d2-regulatory-physiology \
  --config configs/mvp_short_d2l_regulatory_physiology_longrun.json \
  --seeds 51001,51002,51003 \
  --output analyses/d2l_regulatory_physiology_v3_1500 \
  --backend gpu \
  --until-tick 1500
```

Assess:

```bash
se-d2-regulatory-physiology-assess \
  --results analyses/d2l_regulatory_physiology_v3_1500/d2_regulatory_physiology_results.json \
  --output analyses/d2l_regulatory_physiology_v3_assessment
```

The rerun should replace—not be pooled with—the v0.51 long-run flow totals. Ecological and differentiation outcomes remain descriptive until the broader ecosystem is implemented.
