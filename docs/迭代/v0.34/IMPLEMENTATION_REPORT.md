# v0.34 implementation report

## Scope

v0.34 removes forwarding modules introduced by the first package decomposition. It changes import paths and package ownership only; no scientific schema, default configuration, random stream, commit order or world equation is changed.

## Result

- Top-level Python files: 16 (`__init__.py, __main__.py, backend.py, checkpointing.py, config.py, device_state.py, event_cohort.py, execution.py, gpu_runtime.py, information.py, intents.py, metrics.py, policy.py, random_api.py, reductions.py, simulation.py`).
- Generic facade helper: removed.
- Old GUI alias package: removed.
- Canonical modules imported in audit: 81, failures: 0.
- Retained compatibility bridge: `subject_evolution.simulation` only, for trusted checkpoint pickle module identities.
- Runtime/domain dependency on analysis or GUI: none.
- Shipped configs validated: 69/69; unchanged byte-for-byte: 69.
- Shell scripts migrated: 5/5; removed paths remaining: 0.

## Structural corrections

1. `analysis.environment_diversity` moved to `domains.environment.diversity`, because orthogonal field generation and diversity primitives are used by the authoritative environment domain.
2. Knowledge `policy`, `latent`, `working_memory`, `routing_cost`, `system`, `logging` and `diagnostics` import owning sibling modules directly.
3. Commands, experiments, analysis and GUI import `runtime.simulation` directly rather than the checkpoint bridge.
4. Tests patch the concrete owner of a symbol rather than relying on facade assignment propagation.

## Compatibility evidence

- Metrics cells compared: 2219; differences: 0.
- Authoritative final checkpoint differences: 0.
- v0.33 tick-30 checkpoint loaded by v0.34: True.
- Resume versus continuous final-state differences: 0.
- Core output files are byte-identical: True.

## Compatibility policy

A future facade requires a serialized artifact, stable plugin ABI or independently versioned downstream API that cannot be migrated atomically. Import convenience and old test patch paths are not sufficient reasons.
