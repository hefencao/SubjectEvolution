# SE project status

Version: **0.112.0**

## Current scientific task

Version 0.112 implements **Subject VM Stage 3B-1: short-lived local eligibility carriers**.

Stage 3A remains the authoritative long-term history boundary: the graph emits a fixed-width continuous token, and the bounded event ring stores that token with objective post-commit facts. It still does not store historical node IDs, edge IDs, activation masks or whole-network execution paths.

Stage 3B-1 adds only a local, decaying bridge inside the same unified graph. A graph element participates only when its generic eligibility flag and gate are expressed. Executed node output and actual bounded edge transmission may leave signed local traces. The sign is a computational direction, not positive or negative event value. Traces decay by elapsed ticks, expire at a fixed horizon and are checkpointed only for exact replay.

Objective events do not write eligibility in this version. No token/event matcher, credit router, subjective value, weight update or topology change exists. An objective event may remain entirely unassigned.

The v0.110 single-owner rule remains unchanged. Subject VM is the sole optional action-potential residual owner when enabled; legacy knowledge/latent/working-memory routes remain fixed-cognition comparison baselines and cannot coexecute on the primary path.

## Engineering status

Implemented and tested:

- Stage-1 fixed-capacity unified graph storage and lifecycle/checkpoint ownership;
- Stage-2 deterministic bounded CPU-reference activation and action-potential integration;
- v0.110 routing-ownership registry and policy/configuration conflict guards;
- Stage-3A continuous graph-produced token and bounded objective-event ring;
- Stage-3B-1 per-node and per-edge local eligibility gates, participation flags, values and ages;
- deterministic elapsed-tick decay, clipping and fixed-horizon expiry;
- node marks from actual executed node output and edge marks from actual bandwidth-bounded transmission;
- no copy of local eligibility into the long-term token/event ring;
- structural inheritance with dynamic eligibility reset on birth;
- clone/checkpoint preservation, compaction movement and death cleanup;
- explicit v0.111 Stage-3A checkpoint upgrade to empty local eligibility;
- eligibility use/decay/expiry accounting as counts only;
- no event-driven eligibility write, no random-number consumption and no same-tick action feedback;
- exact disabled/default normalization preserving frozen legacy config identities.

D1-X/Y and the latent/working-memory policy family remain:

```text
rejected-as-primary-subject-model
retained-as-fixed-cognition-baseline
```

They retain engineering and comparison value but own neither Subject VM state nor the primary optional action route.

## Epoch milestones

- `epoch-0-ecological-carriers`: current era. Stage 3B-1 is engineering infrastructure only.
- `epoch-1-entity-subject-prototype`: not started. It still requires delayed history use, intervention, baseline exceedance, cost compensation and independent replication.
- `epoch-2-group-subject-prototype`: not started. Candidate/group graphs remain observational and own no rules or Subject VM state.

No supplied checkpoint qualifies either later epoch.

## Not implemented or authorized

- matching historical tokens to later objective events;
- event-to-eligibility modulation or credit assignment;
- subjective value, valence, polarity or fixed event meaning;
- delayed weight, gate, retained-state or topology plasticity;
- content-provenance references actually consumed by the graph;
- automatic conversion of legacy router genes/state into Subject VM nodes or edges;
- topology mutation, developmental expression, token-readout mutation, node migration or region-capacity evolution;
- physical structural, execution, token-memory, bandwidth, eligibility or plasticity cost debit;
- fixed reward, trust, knowledge value, interest formula or group bonus;
- relation/group replacement;
- GPU packed Stage-2/3 execution;
- Epoch 1 panel, paired selection, gene persistence, candidate ledger or subjecthood score.

The next authorized boundary is a separately frozen **delayed association/modulation contract**. It must combine bounded historical continuous tokens, unsigned objective facts and still-live local eligibility without requiring any event to receive credit, without persistent full-network history and without assigning designer-defined positive or negative meaning to any event coordinate.
