# v0.43 implementation report

## Scope

v0.43 implements D2-E automated qualification of D2-D lineage-paired results. It does not change the authoritative world, module topology, module count, routing vocabulary, reproduction, mutation, lineage abundance or GUI.

## Added

- `d2-lineage-paired-assessment-v1`;
- `d2-lineage-paired-plan-v2` and `d2-lineage-paired-results-v2`;
- backward acceptance of v1 lineage-pair plans and results;
- `se-d2-lineage-assess`;
- practical effect thresholds for world and target-lineage outcomes;
- explicit separation of routed-output, retained-cost and total-expression evidence;
- non-dominant replication guard across at least two seeds and lineage identities;
- automatic 300-tick confirmation plans that select modules but preserve every preselected pair;
- short/long paired-horizon persistence assessment;
- protocol audit v11.

## Supplied result decision

Modules 2 and 3 pass the 120-tick continuation screen, but neither has a positive ecological routed-output result. Module 2 has a repeated negative knowledge-transfer-root effect. Module 3 has a repeated target-lineage survival/energy trade-off. The source lineage guard remains failed, so copy-number experiments remain blocked.

## Packaging policy

The complete project package contains only the current `docs/v0.43` version-specific directory. Older version-specific directories are omitted; durable history remains in `docs/CHANGELOG.md`.

## Final validation

- baseline v0.42: `199 passed, 1 skipped`;
- final suite: `204 passed, 1 skipped`;
- 75 configuration JSON files parsed; 129 Python files compiled;
- Conda-prefix editable validation: version `0.43.0`, 85 modules, 8 console entries, external 2-tick smoke passed;
- installed D2-E CLI synthetic execution: 3 pairs, v2 plan/result and v1 assessment schemas;
- supplied-result installed CLI assessment: modules 2 and 3, 48-pair 300-tick confirmation plan, no outcome-conditioned pair selection;
- v0.42 compatibility: 38 checkpoint arrays and 333 non-timing summary cells exactly equal after 20 ticks.
