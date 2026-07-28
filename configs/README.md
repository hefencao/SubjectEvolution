# Configs

Configuration files contain scientific data only; they do not embed Python import paths.

Single run:

```bash
se --config configs/<name>.json --output runs/<name> --backend cpu
```

Multi-seed:

```bash
se-multi --config configs/<name>.json --seeds 10001,10002,10003 --output runs/<name> --backend gpu
```

D0 files use `env` in filenames while JSON field names retain the full `environment_*` terminology.

- `mvp_short_d3c_external_recycling_longrun.json`: D3-C resource-v6 run with conservative pre-harvest intake plus identity-preserving external residue recycling.
- `mvp_short_d3d_persistent_resource_renewal_longrun.json`: D3-D resource-v6 run with role-free persistent moving renewal targets and separately audited numerical inventory settlement.
- `mvp_short_d3e_spatial_processing_longrun.json`: D3-E resource-v7 paired substrate with phase-shifted abiotic processing support and explicit per-unit execution cost. Run through `se-d3-spatial-processing` to obtain shared-checkpoint active and support-neutralized branches.
