# D3-D run plan

- Seeds: `56001,56002,56003`
- Horizon: `1500` ticks
- Environment: `orthogonal-four-resource-renewal-v2`
- Renewal: `moving-target-source-sink-v2`
- Physiology and recycling: retain D3-C resource-v6
- Gate: none; this is a substrate-evolution run

```bash
se-d3-resource-renewal \
  --config configs/mvp_short_d3d_persistent_resource_renewal_longrun.json \
  --seeds 56001,56002,56003 \
  --output analyses/d3d_persistent_resource_renewal_1500 \
  --backend gpu \
  --until-tick 1500
```

Interpret source/sink and both material ledgers first. Resource dimensions and correlations are descriptive evidence that the external opportunity field persists, not an ecological differentiation claim.
