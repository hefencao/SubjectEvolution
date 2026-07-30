# Project-level configs

This directory contains reusable project-level simulation presets. Configuration files contain scientific data only and do not embed Python import paths.

Study-specific candidate configs are colocated with their design under `studies/<study>/protocol/`. Their exact execution order belongs in that study's numbered `commands/` directory rather than in this README.

For any run, the output root belongs under `runs/`. Each single run writes `run_plan.json` before stepping; each multi-seed run writes `multi_seed_plan.json`. Checkpoint cadence controls recovery artifacts, not report freshness.

D0 files use `env` in filenames while JSON fields retain the full `environment_*` terminology.

## Resource and processing presets

- `mvp_short_d3c_external_recycling_longrun.json`: conservative pre-harvest intake plus identity-preserving external residue recycling.
- `mvp_short_d3d_persistent_resource_renewal_longrun.json`: role-free persistent moving renewal targets with separately audited numerical inventory settlement.
- `mvp_short_d3e_spatial_processing_longrun.json`: phase-shifted abiotic processing support with explicit per-unit execution cost.

## Large-population GPU presets

- `mvp_d3i_gpu_scale4_longrun.json`: density-preserving scale-4 source run.
- `mvp_d3i_gpu_scale8_longrun.json`: density-preserving scale-8 source run.

Both retain aggregate mechanism and cost counters while suppressing selected dense observational logs. These switches do not change scientific semantics. Checkpoint storage must be measured on the target environment, and GPU results require the target parity gate.

## Demographic source audit presets

- `mvp_d3j_gpu_scale4_demographic_audit.json`: fixed pilot.
- `mvp_d3k_gpu_scale4_settled_regime_audit.json`: unprotected continuation for post-bottleneck source assessment.
- `mvp_d3l_gpu_scale4_regime_resolution.json`: fixed regime-resolution run.
- `mvp_d3m_gpu_scale4_memory_stability.json`: memory-stability repetition with bounded unused-cache policy.

## Tiered exploration

The reusable smoke preset remains `mvp_d3n_exploration_smoke.json`. Candidate-specific screen, replication, confirmation, and robustness configs now live inside the owning study directory so their scientific design, frozen evidence, and commands cannot drift apart.
