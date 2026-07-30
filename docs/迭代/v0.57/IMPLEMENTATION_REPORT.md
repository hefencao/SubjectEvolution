# v0.57 implementation report

## Baseline and evidence

- Sole code baseline: uploaded complete v0.56 project.
- Supplied evidence: D3-D seeds `56001`, `56002`, `56003` at tick 1500.
- Observed gate: persistent resource dimensions and conservative recycling pass; v1 open-resource ledger fails in every seed.

## Root cause

The v0.56 physical ledger omitted signed float32 inventory settlement generated at two implementation boundaries:

1. field update, diffusion and clipping;
2. segmented harvest commit.

An instrumented same-seed replay decomposed the old residual into exactly those two terms.

## Changes

- Added independent per-step and cumulative field-settlement diagnostics.
- Added independent per-step and cumulative harvest-settlement diagnostics.
- Added CPU, simulated-device, GPU-runtime and checkpoint synchronization.
- Upgraded D3-D plan/results to v2 with explicit unadjusted and corrected ledgers.
- Upgraded structural measurement protocol audit to v25.
- Added parity, compatibility, non-zero settlement and near-machine-precision closure tests.
- Updated version metadata and current documentation to 0.57.0.

## Deliberate non-changes

- no new ecological mechanism;
- no collection-processing coupling;
- no migration controller;
- no role label;
- no diversity reward or protection;
- no population, lineage or group feedback;
- no modification of authoritative float32 trajectory state;
- no causal claim from final field correlations.

## Next gate

Rerun the three supplied seeds to 1500 ticks under D3-D results v2. Advance only when corrected ledgers close, numerical settlement remains small relative to throughput, recycling remains conservative, and multiple external resource dimensions persist.
