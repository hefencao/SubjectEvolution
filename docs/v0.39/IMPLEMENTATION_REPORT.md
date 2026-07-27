# v0.39 implementation report

## Workflow corrections

- Added `se --seed`.
- Added exact comma-separated `--checkpoint-ticks` to `se` and `se-multi`.
- Exact future checkpoints are supported on restored runs.
- `se-multi` writes the same checkpoint union for every seed.
- Added persistent `make release-env`; disposable `release-check` now prints an
  explicit PATH warning.
- Distribution verification executes installed single- and multi-seed exact
  checkpoint smoke tests outside the source tree.
- Fixed persistent-venv source-leak detection: only `project/src` is rejected;
  the candidate must still resolve inside the target venv.
- Short `se-multi` smoke runs without an evolution-progress window now finish as
  `completed-no-progress` and publish an explicit analysis-unavailable record.
- Added `se-d1-factorial --plan` to reuse an existing plan.
- Corrected the phase-planner error from “ecological cycle” to observed
  trough→peak→trough population cycle.

## D2-A

- Added four fixed-layout expression-gated modules per entity.
- Appended module genes after D1 capacity genes without moving existing genome
  coordinates.
- Added inherited gate/input/bias/output mutation.
- Added contextual ten-input evaluation and fixed-budget four-port residual.
- Integrated the effective request preference into CPU and GPU harvest planners.
- Kept assimilation and policy gradient utility on static affinity.
- Added maintenance/development costs and `neutralize-functional-modules`.
- Added checkpoint, clone, manifest, metrics, progress, protocol and long-run
  analysis support.
- Long-run schema upgraded to v14; protocol audit upgraded to v7.

## Compatibility boundary

With functional modules disabled, v0.39 preserves v0.38 world semantics. New
request/checkpoint CLI options are opt-in. Checkpoint serialization includes the
new ablation flag, but the project does not promise cross-version pickle
compatibility as a scientific requirement.
