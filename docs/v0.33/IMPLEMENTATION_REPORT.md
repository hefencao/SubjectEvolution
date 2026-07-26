# v0.33 implementation report

## Delivered changes

- Moved concrete single-run and multi-seed commands into `subject_evolution.commands`.
- Reduced historical command files to compatibility facades.
- Replaced 35 repeated facade implementations with `_compat.install_facade()`.
- Preserved old module execution and monkey-patch behavior.
- Integrated the supplied GUI bridge under `subject_evolution.interfaces.gui`.
- Added compatibility package `subject_evolution.gui_interface`.
- Added protocol sidecar manifest, stable reference reader, attachment lifecycle,
  duplicate attachment rejection, config/checkpoint GUI runner, and three console scripts.

## No scientific changes

This release does not change environment, policy, knowledge, social, lifecycle,
subject, random-key, commit-order, checkpoint-state, or scientific log semantics.

## Results

- Full suite: 161 passed, 1 skipped.
- v0.32/v0.33 authoritative state: zero differences.
- v0.32 checkpoint continuation: zero differences.
- GUI attached/disabled authoritative state: zero differences.
