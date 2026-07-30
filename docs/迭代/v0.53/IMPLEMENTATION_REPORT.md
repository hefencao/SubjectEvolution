# v0.53 implementation report

- Added physiology resource-v4 with four inherited storage and four inherited conversion parameters.
- Added functional v6 with four normalized store-occupancy inputs.
- Added conditional `EntityState.resource_store`, checkpoint/clone persistence, and cumulative raw-store ledgers.
- Added a dedicated `runtime/resource_metabolism.py` settlement module; `runtime/sim.py` remains below the 2500-line architecture boundary.
- Enforced pre-observation conversion and post-action storage, guaranteeing at least one tick of delay.
- Added GPU host-to-device mirror synchronization after delayed body conversion.
- Added D3-A reporting, CLI, configs, protocol audit v21, and regression tests.
- Legacy schemas do not allocate stores and preserve their authoritative trajectories.
