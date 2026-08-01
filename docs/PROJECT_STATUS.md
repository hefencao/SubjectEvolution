# SE project status

Version: **0.111.0**

## Current scientific task

Version 0.111 implements **Subject VM Stage 3A: graph-produced continuous token and objective-event trace**.

The implementation was deliberately corrected before release. A provisional design that would have persisted the exact node and edge path for every event was discarded. Long-term attribution history now stores only a fixed-width continuous token emitted by the graph itself, together with objective post-commit event facts. The token is not a cryptographic hash: nearby internal states remain nearby in token space, so a later mechanism may generalize without relying on exact path identity or hash equality.

The runtime does not decide which internal state is a “thought”. Generic per-node token readout ports allow the graph structure to choose which current node values contribute to each token coordinate. A token may therefore be absent even when the graph acts; in that case no long-term Subject VM event record is created.

Stage 3A preserves the v0.110 single-owner rule. Subject VM remains the sole optional action-potential residual owner when enabled, while legacy knowledge/latent/working-memory routes remain fixed-cognition comparison baselines and cannot coexecute on the primary path.

## Engineering status

Implemented and tested:

- Stage-1 fixed-capacity unified graph storage and complete lifecycle/checkpoint ownership;
- Stage-2 deterministic bounded CPU-reference activation and existing-policy action-potential integration;
- v0.110 routing-ownership registry and policy/configuration conflict guards;
- Stage-3A continuous fixed-width token readout using generic graph-selected ports and gates;
- bounded per-living-subject token/event ring with tick expiry, overwrite accounting and exact checkpoint round trip;
- objective carrier/target identity, action resolution, sampled probability, body/position/information/raw-store deltas and resolution resource/cost facts;
- no persistent executed-node IDs, transmitted-edge IDs, activation masks or whole-network snapshots;
- trace memory scaling with entity capacity, event capacity and token width, independent of graph node/edge capacity;
- token history reset on birth and death, preservation through compaction and clone, and explicit empty-ring upgrade from a Stage-2 runtime payload;
- zero eligibility, zero credit, zero plasticity, zero random-number consumption and no same-tick feedback;
- exact disabled-default normalization preserving frozen legacy config identities.

D1-X/Y and the latent/working-memory policy family remain:

```text
rejected-as-primary-subject-model
retained-as-fixed-cognition-baseline
```

They retain engineering and comparison value but own neither Stage-3 token state nor the primary optional action route.

## Epoch milestones

- `epoch-0-ecological-carriers`: current era. Stage-3A is engineering infrastructure only.
- `epoch-1-entity-subject-prototype`: not started. It still requires delayed history use, intervention, baseline exceedance, cost compensation and independent replication.
- `epoch-2-group-subject-prototype`: not started. Candidate/group graphs remain observational and own no rules or Subject VM state.

No supplied checkpoint qualifies either later epoch.

## Not implemented or authorized

- short-lived local node/edge eligibility dynamics;
- later-tick association between tokens and objective events;
- credit assignment, subjective value, valence or polarity;
- delayed weight, state or topology plasticity;
- content-provenance references actually consumed by the graph;
- automatic conversion of legacy router genes/state into Subject VM nodes or edges;
- topology mutation, developmental expression, token-readout mutation, node migration or region-capacity evolution;
- physical structural, execution, token-memory, bandwidth or plasticity cost debit;
- fixed reward, trust, knowledge value, interest formula or group bonus;
- relation/group replacement;
- GPU packed Stage-2/3 execution;
- Epoch 1 panel, paired selection, gene persistence, candidate ledger or subjecthood score.

The next authorized boundary is not a persistent full-network usage log. It is a separately frozen **short-lived local eligibility contract** or an equally local alternative that can bridge a graph-produced token to future graph change without storing historical node/edge paths. It must permit objective events to remain unassigned and must not assign a fixed positive or negative meaning to any event field.
