# v0.66 implementation report

## Scope

v0.66 applies the user-supplied staged files over the v0.65 baseline and fixes
the scale-4 final-report consistency failure. It changes reporting and
provenance only; no simulated world mechanism is added or retuned.

## Supplied staged files

The overlay retains:

- 100-tick full checkpoints in scale-4 and scale-8 presets;
- disabled dense per-entity knowledge CSV streams for large runs while aggregate
  mechanisms and costs remain enabled;
- batched deterministic latent-root hash components on the selected device;
- `gpu_device_latent_root_rows` and associated transfer telemetry;
- corresponding configuration validation and tests.

## Mixed-age summary diagnosis

`Simulation.run()` previously assembled a metrics row before the checkpoint at
the same tick. In deferred-sync hybrid runs, entity arrays and counters were
current on the host, while `Environment.resource_residue` and its float32
settlement counters remained at the last full checkpoint materialization. The
supplied runs therefore both reported tick 3000/alive 7506, but the old
1,000-tick cadence exposed the tick-2000 residue mirror and the new 100-tick
cadence exposed the tick-2900 mirror.

## Fix

Every metrics/final-report boundary now calls `materialize_reporting_state()`
before `metric_row()`. The resulting row includes:

- `reporting_snapshot_schema = authoritative-reporting-snapshot-v1`;
- `reporting_state_tick`;
- `reporting_state_source`.

The state tick must equal the row tick. Checkpoint cadence is no longer used as
an implicit report synchronization mechanism.

## Run plan

Every `Simulation.run()` writes `run_plan.json` before the first step using
`simulation-run-plan-v1`. It records the fixed start/target ticks, requested and
resolved backend, config SHA-256, metrics cadence, periodic and exact checkpoint
schedule, checkpoint type and planned outputs. The plan declares that schedules
are not outcome-conditioned.

## Scientific boundary

Device-to-host materialization is observational. It does not modify random
streams, actions, costs, reproduction, inheritance, resource dynamics or any
selection pressure. The staged logging switches affect publication only.

## Validation

- 95/95 JSON configurations loaded.
- 192 Python source/script/test files compiled.
- Full deterministic test suite: 321 passed, 2 real-CUDA tests skipped on the delivery host.
- Ordinary parity suite: 20 passed, 2 real-CUDA tests skipped.
- Editable install: 117 modules and 32 console entries; external empty-`PYTHONPATH` smoke passed.
- Explicit CLI reporting smoke wrote `run_plan.json` before stepping and produced a final summary with `tick == reporting_state_tick == 2`.
- Isolated wheel/sdist release audit passed.
- `make conda-sync` and `make conda-check` were executed but stopped at the real `CONDA_PREFIX` guard; the latter completed its full test phase first.
- `make parity-gpu` was executed and intentionally failed its required-device contract because this delivery host has no usable CUDA/CuPy device.
