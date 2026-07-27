# v0.41 implementation report

## Scope

v0.41 adds no new world action, resource, module slot, copy-number mutation or
physical port. It formalizes the evidence gate required before such expansion.

## Added

- `d2-module-leave-one-out-results-v2`;
- `d2-module-immediate-footprint-v1`;
- `d2-module-effect-assessment-v1`;
- `se-d2-assess` console entry;
- automatic 120-tick recommendation;
- outcome-specific practical thresholds;
- cross-seed and phase-conditioned replication checks;
- immediate conditional-HARVEST preference/channel footprint;
- top-lineage footprint summaries;
- dominant-lineage duplication guard.

## Compatibility

The assessment CLI accepts both v1 and v2 D2 audit result files. Existing v0.40
branch results can be assessed directly. `--refresh-footprints` reads their
referenced source checkpoints and does not rerun branches.

The authoritative simulation path is unchanged. D2 audit v2 computes footprint
outside branch stepping and never feeds the result back into the world.

## Scientific conclusion from supplied input

The 120-tick audit justified a 300-tick confirmation. At 300 ticks modules 2 and
3 have repeated extraction-efficiency effects, and several modules have repeated
resource, population or cultural contrasts. However signs are not universally
beneficial, immediate footprints are missing from the v1 result, and median
effective lineage count is only about two. Module duplication remains blocked.

## Validation

- full suite: 195 passed, 1 real-CUDA test skipped;
- configs: 75/75 valid;
- import audit: 83 modules;
- editable metadata and six console entries verified;
- v0.40/v0.41: 2415 common non-timing metric cells, zero differences;
- tick-30 and tick-60 checkpoints: 38/38 common arrays equal.
