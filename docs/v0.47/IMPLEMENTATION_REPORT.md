# v0.47 implementation report

## Scientific route

The supplied D2-H screen did not replicate module 3 routed output in the redesigned source population. v0.47 closes the copy-number route and implements the first D4 environment-matching intervention.

## Added

- persistent resource-only 180-degree reversal on CPU and device environments;
- checkpoint and clone persistence for the resource reversal state;
- D4-A 2×2 shared-checkpoint factorial planner and executor;
- lineage-resolved pre-intervention exposure diagnostics;
- practical, cross-seed and cross-lineage interaction assessment;
- response-blind 300-tick confirmation-plan generation;
- `se-d4-niche-reversal` and `se-d4-niche-assess`.

## Preserved

When no resource-reversal intervention is active, the authoritative simulation path is unchanged. D4-A is available only through explicit experiment entry points.

## Blocked

- module duplication and deletion;
- arbitrary routing and new output ports;
- stable ecological-niche claims;
- social-controller expansion.
