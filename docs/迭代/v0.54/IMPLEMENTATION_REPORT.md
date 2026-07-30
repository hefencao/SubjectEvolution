# v0.54 implementation report

## Implemented

- Added resource physiology v5 with pre-harvest inherited storage-room constraints.
- Added affinity-aware conversion from assimilated room to raw environmental request units.
- Added policy opportunity masking by channel-specific free-store fraction.
- Added explicit unconstrained request and capacity-rejection reporting.
- Forbid material post-assimilation overflow in v5.
- Preserve resource-v4 serialization and authoritative trajectory for exact historical replay.
- Added `se-d3-conservative-intake`, a long-run config, plan/result schemas and tests.
- Split authoritative harvest commit from `runtime/sim.py` into `runtime/harvest_commit.py`.
- Upgraded protocol audit to v22.

## Scientific boundary

The change repairs a conservation boundary. It does not assert that storage improves fitness, that a metabolism has differentiated, or that a food chain exists.
