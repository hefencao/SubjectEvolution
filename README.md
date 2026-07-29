# SE v0.69

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains role-free four-channel resources, conservative storage and recycling, persistent abiotic renewal, costed spatial processing, matched controls, GPU-first execution, and explicit scientific-validity gates.

## Why v0.69

The supplied D3-K aggregate shows a severe early contraction followed by a strong rebound. At tick 3000 the three runs contain 6,056–7,339 living entities, more than 92% are descendants, mean generation is about 2.6–3.0, and recent reproduction is distributed across hundreds of effective parents. However, the last three 100-tick windows are still growing by about 10.5%–12.6% of their recent mean population per window. They are not a settled demographic platform.

v0.69 therefore fixes the regime classifier rather than changing the world. A rebound is no longer called settled merely because its coefficient of variation and per-window growth remain below broad limits. Recent population slope and total cross-window change must also approach zero.

The same audit now reports founder-lineage concentration separately from current strategy and policy variation. Founder lineages are inherited historical labels; their concentration is informative, but it is not a complete substitute for measuring current heritable variation.

No population is rescued. No death, birth, resource, carrying-capacity, reward, sensing, diversity or lineage-protection parameter is changed.

## Demographic regime audit

`se-multi` writes `multi_seed_plan.json` before the first seed starts and automatically emits long-run and selection-validity artifacts after all available seeds finish.

A post-bottleneck source requires all of the following in recent fixed windows:

- adequate absolute population;
- low population coefficient of variation;
- low per-window net growth;
- near-zero recent population slope;
- small total population change across the settled window span;
- descendant and generation replacement;
- broad reproductive contribution;
- conservative founder-lineage concentration checks.

Run the fixed D3-L regime-resolution panel:

```bash
se-multi \
  --config configs/mvp_d3l_gpu_scale4_regime_resolution.json \
  --seeds 69001,69002,69003 \
  --output analyses/d3l_scale4_regime_resolution \
  --backend auto \
  --until-tick 5000
```

The horizon and seeds are fixed before execution. Failed or unresolved runs remain in the analysis.

## GPU execution and parity

Normal runs default to `--backend auto`. A compatible CUDA/CuPy stack uses the hybrid GPU runtime; otherwise execution follows the recorded fallback path. Device semantics are validated independently through:

```bash
make parity-gpu
```

Execution provenance, semantic parity and scientific-effect inference remain separate claims.

## Workflow

```bash
make conda-sync
make test
make conda-check
make release-check
```

## Current version documents

- [Implementation report](docs/v0.69/IMPLEMENTATION_REPORT.md)
- [D3-K regime reinterpretation](docs/v0.69/D3K_3000_REGIME_REINTERPRETATION.md)
- [D3-L fixed-horizon plan](docs/v0.69/D3L_REGIME_RESOLUTION_PLAN.md)
- [Protocol audit](docs/v0.69/protocol_audit.md)
