# v0.61 implementation report

v0.61 is a measurement and control-design correction.

## Implemented

- Records float32 residue-field settlement during diffusion and release.
- Records float32 sparse-deposit settlement when residue is added to the field.
- Persists and GPU-synchronizes both cumulative and per-step counters.
- Backfills missing counters with zero when restoring pre-v0.61 checkpoints.
- Uses the numerical terms only in ledgers and diagnostics; world state is not corrected.
- Upgrades external recycling result schemas and downstream D3-D/D3-E/D3-F schemas.
- Upgrades the acute checkpoint panel to four matched branches.
- Adds matched original and reversed active-minus-neutral contrasts.
- Adds `se-d3-response-scale-audit` with seed-level replication semantics and legacy v1 detection.
- Upgrades the structural protocol audit to v29.

## Supplied-result finding

The supplied base scale has 0 acute-eligible panels; 1.5× and 2× each have 12. All are v1 three-arm panels, so none identifies a reversed active effect. No supplied checkpoint is evolutionarily eligible.

At the two larger scales, original active-minus-neutral mean support gain is approximately `6.0e-6` and `7.6e-6`; original and neutral panel trajectories track at about `0.99` correlation. These are descriptive measurements, not proof of a zero effect.

## Excluded changes

No support sensor, reward, controller, rescue, diversity protection, role label, population feedback, or ecological mechanism was added.

## 1.5× short pilot

A one-seed checkpoint-30, 30-tick four-arm CPU pilot completed with 1,125 entities at the checkpoint and 1,110–1,113 survivors by tick 60. The quartet met the acute sample gate and failed the evolutionary gate, as expected.

All four external-resource and recycling ledgers closed. The unadjusted residue residual was about `2.1e-5`–`2.3e-5` in the largest channel; after separately recorded field and deposit settlement, the maximum corrected residual was below `1.8e-14`.

The one-panel matched contrasts are retained only as mechanism validation and are not generalized.
## Final verification

- 93/93 JSON configurations load and validate.
- 186 Python source, script and test files compile.
- `make test`: 287 passed, 1 skipped across 61 test files.
- Non-Conda editable validation: 116 modules, 31 console entries and external smoke passed.
- Isolated wheel and sdist validation passed.
- The editable verifier now derives its authoritative console-entry set directly from `[project.scripts]`, preventing its own hard-coded list from becoming stale.
- Conda-only checks were attempted but correctly stopped because `CONDA_PREFIX` was not set; no environment state was fabricated.

