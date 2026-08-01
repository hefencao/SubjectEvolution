# SE project status

Version: **0.113.0**

## Current scientific task

Version 0.113 implements **Subject VM Stage 3B-2: bounded delayed association candidates**.

Stage 3A remains the authoritative long-term history boundary: the unified graph emits a fixed-width continuous token, and a bounded event ring stores that token with objective post-commit facts. Historical node IDs, edge IDs, activation masks and complete execution paths are still not persisted.

Stage 3B-1 remains the only micro-level bridge. Executed node output and actual bandwidth-bounded edge transmission may leave short-lived, local, decaying eligibility values selected by graph flags and gates. Their signs remain local computational directions, not event value.

Stage 3B-2 adds a role-neutral content-address candidate mechanism. One configured token coordinate acts as a graph-produced association-request gate and is excluded from similarity. When the request reaches threshold, the current token may select one strictly older token in the same bounded ring by normalized continuous similarity, subject to minimum/maximum delay and deterministic tie-breaking. Every current event may remain unassigned.

The association record contains only a stable historical event ID, historical tick, delay and similarity. It does not interpret the current objective event, modulate eligibility, assign credit, change graph parameters, alter action or consume random numbers. Token similarity is a candidate-addressing result, not proof of causality, correctness, value or memory understanding.

The v0.110 single-owner rule remains unchanged. Subject VM is the sole optional action-potential residual owner when enabled; legacy knowledge/latent/working-memory routes remain fixed-cognition comparison baselines and cannot coexecute on the primary path.

## Engineering status

Implemented and tested:

- Stage-1 fixed-capacity unified graph storage and lifecycle/checkpoint ownership;
- Stage-2 deterministic bounded CPU-reference activation and action-potential integration;
- v0.110 routing-ownership registry and policy/configuration conflict guards;
- Stage-3A continuous graph-produced token and bounded objective-event ring;
- Stage-3B-1 per-node and per-edge local eligibility gates, values, ages, decay and expiry;
- Stage-3B-2 graph-requested delayed token matching with a reserved request coordinate excluded from similarity;
- strictly positive minimum delay and bounded maximum delay constrained by both trace retention and local eligibility lifetime;
- deterministic candidate tie-breaking by similarity, eligible event recency and stable event ID;
- explicit unassigned outcomes for no request, zero query, no candidate or insufficient similarity;
- association metadata stored only in Stage-3B-2 event rings, independent of node/edge capacity;
- no copy of local eligibility or micro execution paths into delayed association records;
- birth/death/compaction/clone/checkpoint handling through the existing stable-owner lifecycle;
- explicit v0.112 Stage-3B-1 checkpoint upgrade to empty association metadata;
- exact disabled/default normalization preserving frozen legacy configuration identities;
- no event-value conversion, eligibility modulation, parameter update, random-number consumption or action feedback.

D1-X/Y and the latent/working-memory policy family remain:

```text
rejected-as-primary-subject-model
retained-as-fixed-cognition-baseline
```

They retain engineering and comparison value but own neither Subject VM state nor the primary optional action route.

## Epoch milestones

- `epoch-0-ecological-carriers`: current era. Stage 3B-2 is engineering infrastructure only.
- `epoch-1-entity-subject-prototype`: not started. It still requires delayed history use, intervention, baseline exceedance, cost compensation and independent replication.
- `epoch-2-group-subject-prototype`: not started. Candidate/group graphs remain observational and own no rules or Subject VM state.

No supplied checkpoint qualifies either later epoch.

## Not implemented or authorized

- interpreting delayed token similarity as causal credit;
- using objective event coordinates as fixed positive or negative value;
- event-to-eligibility modulation or any three-factor update;
- node bias, input/output/trace gate, edge weight, retained-state or topology plasticity;
- graph-produced modulation amplitude or parameter-target selection;
- plasticity stability limits and physical cost debit;
- content-provenance references actually consumed by the graph;
- automatic conversion of legacy router genes/state into Subject VM nodes or edges;
- topology mutation, developmental expression, token-readout mutation, node migration or region-capacity evolution;
- fixed reward, trust, knowledge value, interest formula or group bonus;
- relation/group replacement;
- GPU packed Stage-2/3 execution;
- Epoch 1 panel, paired selection, gene persistence, candidate ledger or subjecthood score.

The next authorized boundary is a separately frozen **Stage 3B-3 modulation-proposal contract**. It must use only already committed delayed association candidates and still-live local eligibility, must preserve an explicit no-update outcome, and must define graph-controlled modulation and generic parameter targets without interpreting any objective event coordinate as designer-defined value. Actual parameter writes remain unauthorized until update bounds, stability and physical plasticity costs are separately fixed.
