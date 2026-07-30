# v0.46 -> v0.47 authoritative compatibility

- Backend: CPU
- Config: `configs/mvp_small.json`
- Horizon: 20 ticks
- D4-A state: disabled
- Checkpoint semantic leaves: `9797 / 9797` identical after normalizing the newly persisted disabled flag to `false`
- Non-timing summary leaves: `350` compared, `0` differences
- Non-timing metrics cells: `1041` compared, `0` differences
- Auxiliary scientific/event outputs: `12 / 12` byte-identical

Expected non-authoritative differences are project version, wall/phase timings, and the new explicit disabled diagnostic `environment_resource_spatial_reversed=false`.

Result: **passed**.
