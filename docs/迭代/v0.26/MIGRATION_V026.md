# Migration to v0.26

## World and checkpoint compatibility

The default world path is unchanged. v0.25 full checkpoints can be resumed by
v0.26. Restored checkpoints that predate the common-boundary fields initialize
that diagnostic as disabled.

## Natural-event execution plans

- v0.25 `natural-event-execution-plan-v1` files remain readable.
- Newly generated plans use `natural-event-execution-plan-v2` and bind the
  common-boundary diagnostic mode into the plan hash.
- Existing v0.25 trajectory markers are not silently reused as v0.26
  common-boundary trajectories. Use a new output directory for the rerun.
- `--execution-plan` executes an already signed plan exactly. Path-prefix,
  anchor, event, intervention and common-boundary modifiers are rejected in
  this mode. Rebuild from the manifest to change any of them.

## Result interpretation

v0.25 result-schema v2 remains auditable. Its `freeze-group-refresh` cohesion
uses branch-current labels and is therefore measurement-entangled. Execute the
v0.26 common-boundary follow-up plan before interpreting the effect on social
flow under a shared partition.
