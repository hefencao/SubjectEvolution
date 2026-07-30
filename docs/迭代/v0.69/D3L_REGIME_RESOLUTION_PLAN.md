# D3-L fixed-horizon demographic regime plan

Schema: `d3l-regime-resolution-plan-v1`

- configuration: `configs/mvp_d3l_gpu_scale4_regime_resolution.json`
- independent seeds: `69001`, `69002`, `69003`
- fixed horizon: 5,000 ticks
- metrics, evolution evaluation and full checkpoints: every 100 ticks
- world, density, resource, cost, inheritance, mutation, reproduction and mortality mechanisms: unchanged from D3-K
- outcome-conditioned stopping: disabled
- failed or unresolved seeds replaced: false
- population or lineage protection: false

The panel resolves whether the strong D3-K rebound approaches a plateau. A candidate settled source requires recent population slope and cross-window span change to pass their preregistered limits in addition to turnover, parent-contributor and founder-lineage checks. Pilot seeds remain design evidence only.
