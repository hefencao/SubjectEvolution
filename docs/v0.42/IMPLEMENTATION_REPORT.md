# v0.42 implementation report

## Scope

v0.42 implements D2-D lineage-balanced paired module experiments. It does not
change the authoritative ecological model, module count, module layout, input
vocabulary, output routing, mutation, reproduction, diversity dynamics or GUI.

## Added

- `d2-lineage-paired-plan-v1`;
- `d2-lineage-paired-results-v1`;
- `se-d2-lineage-pairs` console entry;
- pre-intervention lineage membership inspection and eligibility guards;
- lineage-targeted fixed-module output neutralization;
- optional lineage-targeted expression-cost neutralization;
- persistent treatment for same-lineage descendants inside a branch;
- exact output/cost/total effect decomposition;
- target-lineage endpoint summaries;
- equal-weight offline aggregation per checkpoint-lineage paired unit;
- checkpoint persistence and clone support for targeted interventions;
- protocol audit v10 and D2 effect assessment v2 routing.

## Supplied assessment decision

The refreshed assessment shows cross-lineage immediate footprint and repeated
downstream effects, including repeated extraction-efficiency effects for modules
2 and 3. Median effective lineages remain about 2.03, so duplication remains
blocked. D2-D is therefore the admissible next step.

## Compatibility boundary

Lineage-targeted masks are empty by default. Existing global module ablations
retain their v0.41 semantics. Genotype and lineage state are checked before every
targeted branch. New fields load as empty from older checkpoints.

## Final validation

- full suite: `199 passed, 1 skipped`;
- configuration load: `75/75` JSON configs;
- editable package: version `0.42.0`, `84` importable modules, `7` console entries;
- installed `se-d2-lineage-pairs` smoke: `6/6` checkpoint-lineage-module pairs executed with exact decomposition closure;
- feature-disabled v0.41 comparison: byte-identical common authoritative state and zero differences across `345` common non-timing final metrics.

The validation container had no Conda executable. It used the active
`/opt/pyvenv` prefix to execute the exact editable verifier; see
`ENVIRONMENT_VALIDATION_NOTE.md` for the explicit limitation.
