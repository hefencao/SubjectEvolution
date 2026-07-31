# SE project status

Version: **0.93.0**

## Current development direction

Audit expansion and new-gene work remain paused. D1-M showed that the fixed
conservative reproduction substrate is promising but not formally qualified:
two seeds passed tick 360, while one source was prematurely stopped at tick 240
by an execution-contract defect. v0.93 advances D1-N, which separates advisory
trajectory diagnostics, catastrophic runtime floors, and required final source
qualification.

## D1-M frozen result

Seeds 92102 and 92103 completed tick 360 and passed every v1 health condition.
Seed 92101 was stopped when its tick-120 to tick-240 population decline was
30.43%, narrowly above a 30% desired trajectory bound. At the stop it still had
128 living entities from 128 founders, 98 cumulative births, 56 living
descendants, and mean generation 0.4375. D1-M is therefore neither promoted nor
classified as a failed substrate. The original result and decision are frozen.

## Source-health contract v2

`source-health-contract-v2` separates three meanings that v1 conflated:

1. advisory checkpoints record whether maturation is on schedule;
2. broad catastrophic floors alone may terminate a run early;
3. required final checkpoints alone authorize the next stage.

A marginal advisory miss remains visible but does not destroy a recoverable
source. A catastrophic floor still stops the run and may stop the remaining
panel. Final qualification thresholds are fixed before formal seeds execute.

## D1-N stable-turnover substrate

D1-N adds no inherited trait, reward, role, or population protection. It retains
the fixed conservative reproduction settlement and applies one uniform physical
substrate calibration to every entity:

- maintenance cost: 0.010 energy/tick;
- four-channel harvest multiplier: 1.30;
- four-channel abiotic regeneration: 0.027;
- 128 founders, fixed 0.9 offspring transfer, 0.1 event overhead, 0.8 parent reserve.

The formal panel uses disjoint seeds 93101--93103 and a required tick-480
checkpoint. Internal calibration seeds proved only that the default is not known
to be invalid; they are not project evidence.

## Development-order rule

1. Run the complete D1-N formal panel.
2. Require all three seeds to pass the required tick-480 qualification.
3. Derive a per-capita energy and reserve budget from those formal trajectories.
4. Declare structural, use, development, and combination-maturation costs before
   attaching another inherited capability.
5. Re-run source health after capability attachment.
6. Only then authorize paired or evolutionary measurement.

## Current task

Run only the D1-N formal qualification workflow and package all staged warnings,
hard-stop evidence, final health results, source config, and manifest. Do not add
a new gene or paired branch unless all three formal seeds pass.

## Still incomplete

- formal D1-N qualification on seeds 93101--93103;
- a capability-affordability budget derived from qualified formal throughput;
- a combination-maturation protocol;
- independent evolutionary evidence for any D1 inherited allocation;
- coexistence, reversal, and removal tests required for a niche claim.
