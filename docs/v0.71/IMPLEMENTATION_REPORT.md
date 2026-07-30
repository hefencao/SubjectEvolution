# v0.71 implementation report

v0.71 separates exploratory throughput from confirmation-level evidence.

## Added

- `exploration-readiness-audit-v1` for within-run versus independent-seed sample diagnosis;
- `tiered-exploration-plan-v1` for smoke, screen, replication and confirmation stages;
- exact `se-multi --exploration-plan` invocation validation;
- automatic exploration-readiness output from completed multi-seed runs;
- `multi-seed-run-plan-v4` and `multi-seed-long-run-analysis-v18`;
- three bounded D3-N exploration presets;
- disjoint-seed enforcement between screen, replication and confirmation;
- explicit authorization before large long confirmation.

## Scientific invariants

- seed is the independent unit;
- windows, entities and events are nested observations;
- insufficient runs remain in the record;
- seed and horizon changes cannot depend on observed outcomes;
- exploration stages cannot make selection claims;
- no population rescue, diversity protection, role assignment or world feedback was added.
