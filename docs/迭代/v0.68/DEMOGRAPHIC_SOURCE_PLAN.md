# D3-K post-bottleneck demographic source plan

Schema: `d3k-post-bottleneck-source-plan-v1`

```bash
se-multi \
  --config configs/mvp_d3k_gpu_scale4_settled_regime_audit.json \
  --seeds 68001,68002,68003 \
  --output analyses/d3k_scale4_settled_regime \
  --backend auto \
  --until-tick 3000
```

The run retains the D3-J world, density, resources, costs, inheritance, mutation, birth and death semantics. Only the observation horizon is extended.

A post-bottleneck source is not accepted from rebound alone. Recent fixed windows must pass population stability, lineage breadth, descendant replacement, generation turnover, unique/effective successful-parent breadth and parent-contribution concentration.

Any burn-in rule derived from these three pilots applies only to new independent seeds. The pilots are not reused as confirmatory effect samples.
