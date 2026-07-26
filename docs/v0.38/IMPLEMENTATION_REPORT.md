# v0.38 implementation report

## Scope

v0.38 is D1-C: measurement and paired-intervention infrastructure required to
decide whether D1 has produced meaningful ecological differentiation. It does
not add D2 functional operators.

## Runtime changes

- preserve requested harvest arrays in CPU and GPU resolution plans;
- accumulate requested and realized channel totals separately;
- publish per-window requests, shares and extraction efficiency;
- include request counters in checkpoint, clone and metrics state;
- retain a restore fallback for pre-field progress tracker state.

## Analysis changes

- long-run schema upgraded to `multi-seed-long-run-analysis-v13`;
- raw volume separated from per-window composition;
- explicit, inferred-uniform and unavailable-selective provenance recorded;
- old selective realized output is never used to invent requested composition.

## Experiment changes

- new `d1-affinity-capacity-factorial-plan-v1`;
- four paired branches from a shared checkpoint;
- affinity, capacity and interaction contrasts;
- `se-d1-factorial` console script.

## Release changes

- new sdist→wheel disposable-venv verifier;
- optional previous-wheel replacement test;
- source-tree exclusion and installed-module origin check;
- import-all, `pip check`, four CLI checks and external-config smoke;
- `make release-check` combines source tests and distribution validation.

## Interpretation boundary

Request composition, utilization and factorial contrasts are necessary evidence,
not a subjecthood score or proof of universal adaptive value. D2 remains blocked
until the preregistered rerun and paired branches are available.
