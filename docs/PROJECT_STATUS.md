# SE project status

Version: **0.71.0**

## Current sample diagnosis

The D3-M scale-4 runs have adequate within-run observational support:

- final alive: 23,533–28,523;
- descendant alive fraction: 1.0;
- effective successful parents in the final window: about 2,278–2,480;
- largest parent contribution remains very small;
- current strategy effective dimensions remain about 13–27.

The remaining sample limitations are cross-run and source-regime limitations:

- only three independent seeds;
- founder-lineage inverse-Simpson counts about 14–35;
- no common future source rule;
- population remains slightly increasing at the final observation windows.

Thus the completed large runs are useful demographic and operational anchors, but not confirmation-level selection evidence.

## Current exploration policy

```text
mechanism smoke
→ 8-seed small screen
→ 8 new-seed medium replication
→ explicit large long confirmation only for promoted candidates
```

`se-exploration-plan` pre-registers the stage and `se-multi` verifies the exact config hash, seeds, output, backend and horizon before execution.

## Current gates

1. Do not count entities, windows, births or moves as independent replicates.
2. Do not repeat large long runs for ordinary exploratory iteration.
3. Require at least eight seeds for screen and replication.
4. Require disjoint seeds across all stages.
5. Require explicit authorization before large long confirmation.
6. Preserve every failed or insufficient run.
7. Keep migration, specialization, coexistence and ecotype gates closed.

## Still incomplete

- a stable common post-bottleneck source rule;
- confirmation-level independent replication;
- causal decomposition of founder-lineage contraction;
- replicated positive processing-response evidence;
- device-resident action settlement, lifecycle and graph updates.
