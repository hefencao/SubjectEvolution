# Next experiment

Run the paired v2 generative-capability experiment:

```bash
se-d2-compose \
  --config configs/mvp_short_d2i_compositional_harvest_longrun.json \
  --seeds 48001,48002,48003 \
  --output analyses/d2i_compositional_capability_1500 \
  --backend gpu \
  --until-tick 1500
```

Do not run the previously generated D4-A 300-tick confirmation plan. The supplied 120-tick result is now classified as a generic interaction without realized exposure-aligned differentiation.

The paired D2-I output should be read as a capability map rather than a single pass/fail result. Preserve the complete branch directories because the time series, not only the final endpoint, determines whether composition is used persistently.
