# v0.72 implementation report

v0.72 replaces free-running endpoint screens with fixed-checkpoint matched panels.

## Added

- `exploration-readiness-audit-v2` with scale-normalized acute checkpoint support;
- explicit detection of a common startup transient across independent seeds;
- `tiered-paired-exploration-plan-v1`;
- `tiered-paired-exploration-results-v1`;
- `tiered-paired-exploration-assessment-v1`;
- `se-exploration-paired-plan` and `se-exploration-paired`;
- checkpoint hash locking before branch execution;
- cumulative-response and endpoint-response metric modes;
- equal seed weighting, direction consistency, practical-effect thresholds, and exact sign-flip reporting;
- disjoint-seed and passing-prior-assessment requirements for replication and confirmation.

## Corrected evidence boundary

The D3-N free-run endpoints are a repeatable startup decline, not a candidate intervention effect. All eight tick-480 checkpoints retain adequate scale-normalized living and lineage support for a short paired panel, while none supports long-horizon selection interpretation.

## Scientific invariants

- baseline and intervention share one full checkpoint per seed;
- checkpoint tick is fixed before branch outcomes;
- seed is the independent unit;
- repeated windows, entities, births, deaths, moves, and actions remain nested observations;
- no failed or ineligible seed is replaced;
- no population rescue, diversity protection, role assignment, or world feedback was added.
