# v0.46 implementation report

v0.46 replaces the unrun, over-constrained D2-H replication candidate with a phase-specific causal re-audit based on the actually completed D2-G experiment.

## Code changes

- D2-G assessment schema upgraded from v1 to v2.
- Added explicit distinction between exploratory routing and major-conclusion evidence.
- Added two-sided 95% Wilson intervals for guarded panel pass fractions.
- Added D2-H plan/result/assessment schemas and two console entries.
- Added source-population checkpoint selection based only on preregistered D2-G guards.
- Added response-blind retention of all member- and expression-qualified lineages.
- Reused the existing lineage-targeted output/cost decomposition.
- Added automatic response-blind 300-tick plan generation after a passing 120-tick screen.
- Kept module copy number, deletion and routing expansion disabled.

## Supplied-data decision

- peak: equal-lineage 2/3, natural 0/3; selected for D2-H;
- trough: equal-lineage 1/3, natural 0/3; not selected;
- selected checkpoints: seeds 45001 and 45003;
- selected lineages: 6 per checkpoint;
- planned module-lineage causal units: 12;
- branch executions excluding shared baselines: 24;
- initial horizon: 120 ticks.
