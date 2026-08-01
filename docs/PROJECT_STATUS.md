# SE project status

Version: **0.114.0**

## Current scientific task

Version 0.114 implements **Subject VM Stage 3B-3: bounded modulation proposals**.

Stage 3A remains the authoritative long-term history boundary: the unified graph emits a fixed-width continuous token, and a bounded event ring stores that token with objective post-commit facts. Historical node IDs, edge IDs, activation masks and complete execution paths are not persisted.

Stage 3B-1 remains the only micro-level bridge. Executed node output and actual bandwidth-bounded edge transmission may leave short-lived, local, decaying eligibility values selected by graph flags and gates. Their signs remain local computational directions, not event value.

Stage 3B-2 remains a role-neutral content-address boundary. A graph-requested current token may select one strictly older token in the same bounded ring by normalized continuous similarity. Similarity is only an address criterion and never a credit or modulation magnitude.

Stage 3B-3 adds a second, independent graph request over an already assigned association. Reserved token coordinates provide twenty-one fact-projection weights and six generic parameter-family weights. The runtime forms the normalized current-minus-historical objective-fact contrast, projects it with graph-produced weights, and stores a bounded six-dimensional proposal over:

- node bias;
- node input gate;
- node output gate;
- node trace gate;
- edge forward gate;
- edge bandwidth.

All association, fact-projection, target-projection and request coordinates are excluded from association similarity. Every event may remain without a proposal. The proposal record contains no concrete node/edge target and performs no eligibility or parameter write.

The v0.110 single-owner rule remains unchanged. Subject VM is the sole optional action-potential residual owner when enabled; legacy knowledge/latent/working-memory routes remain fixed-cognition comparison baselines and cannot coexecute on the primary path.

## Engineering status

Implemented and tested:

- Stage-1 fixed-capacity unified graph storage and lifecycle/checkpoint ownership;
- Stage-2 deterministic bounded CPU-reference activation and action-potential integration;
- v0.110 routing-ownership registry and policy/configuration conflict guards;
- Stage-3A continuous graph-produced token and bounded objective-event ring;
- Stage-3B-1 per-node and per-edge local eligibility gates, values, ages, decay and expiry;
- Stage-3B-2 bounded delayed association candidates with explicit unassigned outcomes;
- Stage-3B-3 graph-requested, bounded, rejectable parameter-family proposal vectors;
- exclusion of all proposal-control token coordinates from association similarity;
- proposal strength independent of association similarity and delay;
- explicit rejection for no request, no association, missing history, zero fact weights, zero fact contrast, zero target weights or zero signal;
- proposal metadata stored only in Stage-3B-3 event rings and independent of graph node/edge capacity;
- no concrete target IDs, local eligibility snapshots or micro execution paths in proposal records;
- birth/death/compaction/clone/checkpoint handling through the existing stable-owner lifecycle;
- explicit v0.113 checkpoint upgrade to empty modulation-proposal metadata;
- exact disabled/default normalization preserving frozen legacy configuration identities;
- no event-value conversion, eligibility modulation, parameter binding, parameter update, random-number consumption or action feedback.

D1-X/Y and the latent/working-memory policy family remain:

```text
rejected-as-primary-subject-model
retained-as-fixed-cognition-baseline
```

They retain engineering and comparison value but own neither Subject VM state nor the primary optional action route.

## Epoch milestones

- `epoch-0-ecological-carriers`: current era. Stage 3B-3 is engineering infrastructure only.
- `epoch-1-entity-subject-prototype`: not started. It still requires actual delayed parameter use, intervention, baseline exceedance, cost compensation and independent replication.
- `epoch-2-group-subject-prototype`: not started. Candidate/group graphs remain observational and own no rules or Subject VM state.

No supplied checkpoint qualifies either later epoch.

## Not implemented or authorized

- interpreting delayed token similarity as causal credit;
- using objective event coordinates as fixed positive or negative value;
- binding proposal components to exact nodes, edges or retained-state slots;
- event-to-eligibility modulation or any three-factor parameter update;
- node bias, input/output/trace gate, edge gate/bandwidth, retained-state or topology plasticity;
- same-tick-safe eligibility target separation and update scheduling;
- plasticity stability limits, rollback and physical cost debit;
- content-provenance references actually consumed by the graph;
- automatic conversion of legacy router genes/state into Subject VM nodes or edges;
- topology mutation, developmental expression, token/proposal-readout mutation, node migration or region-capacity evolution;
- fixed reward, trust, knowledge value, interest formula or group bonus;
- relation/group replacement;
- GPU packed Stage-2/3 execution;
- Epoch 1 panel, paired selection, gene persistence, candidate ledger or subjecthood score.

The next authorized boundary is a separately frozen **Stage 3C-1 exact-target binding and update-safety contract**. It must solve same-tick eligibility contamination, bind proposals only to still-valid historical local carriers, preserve a reject/rollback path, define per-parameter and cumulative bounds, and still keep physical plasticity cost and actual writes independently auditable. Parameter writes remain unauthorized until that contract is frozen and tested.
