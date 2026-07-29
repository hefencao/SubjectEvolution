# Configs

Configuration files contain scientific data only; they do not embed Python import paths.

Single run:

```bash
se --config configs/<name>.json --output runs/<name> --backend auto
```

Each run writes `run_plan.json` before its first step and tags every summary
with an authoritative reporting-state tick. Checkpoint cadence controls recovery
artifacts, not the freshness of `summary.json`.

Multi-seed:

```bash
se-multi --config configs/<name>.json --seeds 10001,10002,10003 --output runs/<name> --backend auto
```

D0 files use `env` in filenames while JSON field names retain the full `environment_*` terminology.

- `mvp_short_d3c_external_recycling_longrun.json`: D3-C resource-v6 run with conservative pre-harvest intake plus identity-preserving external residue recycling.
- `mvp_short_d3d_persistent_resource_renewal_longrun.json`: D3-D resource-v6 run with role-free persistent moving renewal targets and separately audited numerical inventory settlement.
- `mvp_short_d3e_spatial_processing_longrun.json`: D3-E resource-v7 paired substrate with phase-shifted abiotic processing support and explicit per-unit execution cost. Run through `se-d3-spatial-processing` to obtain shared-checkpoint active and support-neutralized branches.

Large-population GPU presets:

- `mvp_d3i_gpu_scale4_longrun.json`: density-preserving 4× linear-area source run with 8,000 initial entities, 32,768 maximum capacity, 128×128 resource grid and 3,000 ticks.
- `mvp_d3i_gpu_scale8_longrun.json`: density-preserving 8× linear-area source run with 32,000 initial entities, 131,072 maximum capacity, 256×256 resource grid and 1,500 ticks.

Both presets request `hybrid-accelerated` semantics through the normal `auto` backend, disable per-tick invariant validation, and write both the observation `.npz` and trusted full-world `.sechk` checkpoint every 100 ticks. They also disable dense per-entity outcome, policy, routing-cost, working-memory and sparse-selection CSV publication; aggregate mechanism/cost counters, transfer events, periodic diagnostics and full checkpoints remain enabled. These observational log switches do not change entity density, per-cell resource parameters, costs, inheritance, mutation or scientific interpretation rules. Checkpoint storage must be budgeted before a full run: the measured scale-4 tick-100 pair was about 55 MiB combined, and scale-8 should be measured independently rather than extrapolated as a guarantee. Run `make parity-gpu` on the target CUDA/CuPy stack before treating device results as parity-certified.

Demographic source audit presets:

- `mvp_d3j_gpu_scale4_demographic_audit.json`: 1,200-tick pilot at 100-tick reporting/evaluation/checkpoint cadence.
- `mvp_d3k_gpu_scale4_settled_regime_audit.json`: 3,000-tick continuation of the same unprotected scale-4 world, used to test whether a stable, descendant-dominated and reproductively broad post-bottleneck source emerges.
- `mvp_d3l_gpu_scale4_regime_resolution.json`: fixed 5,000-tick regime-resolution run. It retains the same world and mechanisms while requiring recent population slope and cross-window change to approach zero before a rebound can be called settled.

`se-multi` writes `multi_seed_plan.json` before the first seed and automatically emits `selection_validity_plan.json`, `selection_validity_audit.json` and Markdown after all available seed progress streams complete. These outputs never alter the simulation or replace failed seeds.
