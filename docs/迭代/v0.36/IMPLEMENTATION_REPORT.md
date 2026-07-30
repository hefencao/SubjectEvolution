# v0.36 implementation report

## Implemented

- Added `se.differentiation` and `inherited-elastic-capacities-v1`.
- Appended four non-overlapping capacity genes to the configuration-dependent genome.
- Added fixed-layout per-entity effective-capacity arrays.
- Enforced per-entity working-memory, knowledge-storage, relationship and attention limits.
- Added structural maintenance and birth development energy costs.
- Added capacity diagnostics to metrics, evolution progress, run manifest and long-run analysis.
- Upgraded structural protocol audit to v4 and long-run analysis to v11.
- Added `neutralize-elastic-capacities` with immediate trimming, genotype preservation, offspring persistence and checkpoint support.
- Added smoke and long-run D1 configurations.

## Not implemented

- sensor range or sensor channel capacity;
- physical resource/body storage capacity;
- module count, expression gating or gene duplication;
- nonlinear capacity costs;
- capacity plasticity within one lifetime;
- proof of ecological niches or social consequences.

## Determinism and compatibility

D1-disabled execution retains the v0.35 common trajectory exactly. D1-enabled checkpoints restore and continue exactly within v0.36. The new state arrays necessarily extend the checkpoint schema.
