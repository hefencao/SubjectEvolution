# SE project status

Version: **0.117.0**

## Current scientific task

Version 0.117 implements **Subject VM Stage 3C-3: atomic shadow compare-and-swap and rollback validation without permanent parameter writes**.

Stage 3A remains the authoritative long-term history boundary: the unified graph emits a fixed-width continuous token, and a bounded event ring stores that token with objective post-commit facts. Historical node IDs, edge IDs, activation masks and complete execution paths are not persisted.

Stage 3B-1 remains the only micro-level bridge. Executed node output and actual bandwidth-bounded edge transmission may leave short-lived, local, decaying eligibility values selected by graph flags and gates. Their signs remain local computational directions, not event value.

Stage 3B-2 and Stage 3C-1 continue as explicit bootstrap biases: normalized continuous token similarity chooses at most one historical event candidate, and the largest still-valid pre-activation local eligibility carrier chooses at most one target per parameter family. These mechanisms are retained to shorten early graph shaping and debugging; they are not universal attention claims.

Stage 3B-3 forms a graph-controlled six-dimensional proposal over node bias, node input/output/trace gates, edge forward gate and edge bandwidth. Stage 3C-1 binds nonzero family components to exact stable node or edge targets without writing them.

Stage 3C-2 now revalidates each bound target against current stable ID, slot, expression state, parameter family and required port. It combines the family proposal, historical local eligibility and a configured role-neutral step scale into a candidate delta. The candidate is constrained by per-family absolute clips, a per-subject event L1 envelope and configured parameter bounds. The current parameter value is persisted as a future compare-and-swap and rollback guard. No parameter, eligibility, retained state or topology write is authorized.

Stage 3C-3 consumes those safe candidates as one event transaction. It performs exact float32 compare-and-swap checks against the live graph, rejects the entire event if any target is stale or changed, applies projected values only to a private six-family shadow vector, and verifies exact rollback to the captured pre-state. Shadow validation produces count-only cost units; it does not debit energy, consume randomness or authorize graph writes.

Audit-only proposals do not consume a long-window applied-update budget. Such accounting would fabricate plasticity that did not occur. A future write stage must add an actual accepted/applied ledger, atomic compare-and-swap revalidation and independent physical cost accounting.

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
- Stage-3C-1 compact pre-activation target candidates and exact audit-only binding metadata;
- Stage-3C-2 stable-target revalidation and bounded compare-and-swap candidate-delta metadata;
- proportional per-event L1 scaling without parameter-family order priority;
- configured lower/upper parameter projection, including nonnegative edge bandwidth;
- current parameter snapshots as future rollback guards;
- count-only proposal accounting with zero parameter writes;
- deterministic bootstrap single-winner selection by absolute local eligibility with stable-ID tie break;
- explicit classification of fixed normalized-dot association, single-winner binding and three-factor candidate-delta formation as replaceable bootstrap engineering biases;
- birth/death/compaction/clone/checkpoint handling through the existing stable-owner lifecycle;
- explicit v0.115 checkpoint upgrade to empty Stage-3C-2 metadata;
- exact disabled/default normalization preserving frozen legacy configuration identities;
- no engine-defined event value, similarity-as-strength, delay-as-strength, action feedback or random-number consumption.

D1-X/Y and the latent/working-memory policy family remain:

```text
rejected-as-primary-subject-model
retained-as-fixed-cognition-baseline
```

They retain engineering and comparison value but own neither Subject VM state nor the primary optional action route.

## Epoch milestones

- `epoch-0-ecological-carriers`: current era. Stage 3C-3 is engineering infrastructure only.
- `epoch-1-entity-subject-prototype`: not started. It still requires actual delayed parameter use, intervention, baseline exceedance, cost compensation and independent replication.
- `epoch-2-group-subject-prototype`: not started. Candidate/group graphs remain observational and own no rules or Subject VM state.

No supplied checkpoint qualifies either later epoch.

## Not implemented or authorized

- interpreting delayed token similarity as causal credit;
- using objective event coordinates as fixed positive or negative value;
- permanent node bias, gate, bandwidth, retained-state or topology writes;
- permanent compare-and-swap commit, live rollback execution or partial-write recovery;
- an accepted/applied long-window plasticity ledger;
- physical plasticity cost debit or health-compensated cost experiments;
- content-provenance references actually consumed by the graph;
- automatic conversion of legacy router genes/state into Subject VM nodes or edges;
- topology mutation, developmental expression, token/proposal-readout mutation, node migration or region-capacity evolution;
- a complete general attention allocator, candidate budget competition or lazy payload execution;
- fixed reward, trust, knowledge value, interest formula or group bonus;
- relation/group replacement;
- GPU packed Stage-2/3 execution;
- Epoch 1 panel, paired selection, gene persistence, candidate ledger or subjecthood score.

The next authorized boundary is a separately frozen **Stage 3C-4 guarded live-write experiment contract**. It must keep permanent writes disabled by default, define explicit opt-in, applied-update ledgers, bounded rollback windows, count-only cost accounting and trajectory-neutral controls before any scientific use.
