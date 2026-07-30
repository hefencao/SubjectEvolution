# v0.80 implementation report

## Scientific input

The supplied D3-T screen contains eight eligible seeds and six successful manipulation checks per seed. Neutralizing spatial processing support increases cumulative realized conversion in all eight seeds. The equal-seed median relative effect is about +3.026%, above the unchanged 2% practical threshold, so the screen decision is promotion to disjoint replication.

This result is bounded to the acute tick-480 panel. It does not establish adaptive benefit, ecological specialization, long-horizon selection or a stable source population.

## Implementation

- Records the D3-T screen in the immutable repository and package decision baselines.
- Upgrades source exploration plans to `tiered-exploration-plan-v2`.
- Adds a canonical replication-protocol fingerprint over the full configuration with only `run.seed` normalized.
- Requires replication source plans to match the prior screen fingerprint and to use disjoint seeds.
- Requires paired replication inputs to come from a source plan explicitly locked to the prior screen.
- Changes `mvp_d3n_exploration_replication.json` to the screen protocol with seeds 71201–71208 as the intended independent set.
- Preserves the former larger configuration as `mvp_d3n_exploration_scale_robustness.json`, without authorizing its execution.
- Adds source-plan provenance to new paired assessments and candidate-ledger entries.
- Upgrades the protocol audit to v48 and project version to 0.80.0.

## Scientific boundary

No reward, action, sensor, survival protection, threshold, response window, checkpoint tick, conversion cost or simulation mechanism is changed. The only execution-design change is stricter separation of independent-seed replication from scale robustness.
