# D1-Z Subject VM Stage 3C-34

Stage 3C-34 is a read-only event-level audit over the frozen Stage 3C-33 matched-horizon trajectories. It does not rerun selected seeds and does not change exposure, addressing, weights, runtime state, checkpoint schema, reward, or retention.

## Question

The Stage 3C-33 source-balanced exposure-only fact contrast was nonzero only in seeds 12305 and 12308. This study locates where the remaining sources stop in the causal chain:

```text
Subject-VM action-potential divergence
  → sampled-action crossing
  → Objective-Fact crossing
  → source-balanced aggregation
```

All eight arms per source must share the same 144 event identities over ticks 4–12. Event-level Objective-Fact contrasts must reproduce the frozen Stage 3C-33 source-balanced vectors exactly.

## Frozen result

All nine sources contain exposure-dependent, alignment-dependent Subject-VM action-potential divergence. Only seeds 12305, 12307 and 12308 cross an actual sampled-action boundary. Seed 12307 crosses in the same way in both alignment modes and is removed by the cross-mode contrast. Seeds 12305 and 12308 contain four alignment-specific action crossings in total; these are followed by twelve differential Objective-Fact events, eight of them delayed after the crossing event. Those two seeds exactly reproduce the two nonzero Stage 3C-33 source-level effects. No differential Objective-Fact crossing is later cancelled by source balancing.

The frozen trace does not persist the complete masked policy logits or categorical draw, so the exact numeric distance to the action boundary is not observable. No value, correct-credit, keep/revert, learning, or retention conclusion is authorized.
