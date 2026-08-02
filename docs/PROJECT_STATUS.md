# SE project status

Version: **0.118.0**

## Current scientific task

Version 0.118 implements **Subject VM Stage 3C-4: explicitly opted-in guarded live writes with a fixed-capacity applied ledger and deterministic short-window rollback**.

Stage 3A remains the authoritative long-term history boundary: the unified graph emits a fixed-width continuous token and a bounded event ring stores that token with objective post-commit facts. Historical node IDs, edge IDs, activation masks and complete execution paths are not persisted.

Stage 3B-1 remains the only micro-level bridge. Executed node output and actual bandwidth-bounded edge transmission may leave short-lived local eligibility values selected by graph flags and gates. Their signs remain local computational directions, not event value.

Stage 3B-2 and Stage 3C-1 continue as explicit bootstrap biases: normalized continuous-token similarity chooses at most one historical event candidate, and the largest still-valid pre-activation local eligibility carrier chooses at most one target per parameter family. These mechanisms shorten early graph shaping; they are not universal attention claims.

Stage 3B-3 forms a graph-controlled six-dimensional parameter-family proposal. Stage 3C-1 binds nonzero components to exact stable node or edge targets. Stage 3C-2 revalidates those targets and forms bounded candidate deltas under per-family clips, per-event L1 limits and parameter ranges. Stage 3C-3 verifies exact float32 compare-and-swap, event-level all-or-none semantics and rollback in a private shadow vector.

Stage 3C-4 adds the first live parameter mutation path, but only behind an explicit `live_write.enabled` opt-in. A commit is accepted only when the Stage 3C-3 shadow transaction was prepared and rollback-verified, a second exact float32 CAS still matches the live graph, the subject is not locked, no pending transaction overlaps the same stable target, and fixed pending/window budgets remain available.

Accepted writes enter a fixed-capacity per-subject applied ledger containing event identity, stable targets, pre/post float32 values, apply tick and rollback deadline. The live values are visible only during the configured short window. At or after the deadline the runtime attempts an exact post-value-guarded, all-or-none rollback before activation. Any rollback mismatch locks further writes for that subject rather than silently accepting an unrecoverable state.

The same Stage 3C-4 contract supports a trajectory-neutral control with `live_write.enabled=false`. Commit and rollback costs remain count-only instrumentation; they do not debit entity energy. The bootstrap association, binding and update formulas remain replaceable engineering biases and are not treated as causal truth.

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
- Stage-3C-3 exact shadow CAS, all-or-none validation and rollback evidence;
- Stage-3C-4 explicit opt-in guarded live commits with a second exact CAS;
- fixed-capacity per-subject applied ledger, pending-transaction cap and target/delta window budgets;
- overlapping pending-target rejection and deterministic pre-activation rollback;
- subject write lock after rollback failure;
- a Stage-3C-4 `enabled=false` trajectory-neutral control;
- count-only commit/rollback accounting with no entity-energy debit;
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

- `epoch-0-ecological-carriers`: current era. Stage 3C-4 is a guarded engineering experiment only.
- `epoch-1-entity-subject-prototype`: not started. It still requires actual delayed parameter use, intervention, baseline exceedance, cost compensation and independent replication.
- `epoch-2-group-subject-prototype`: not started. Candidate/group graphs remain observational and own no rules or Subject VM state.

No supplied checkpoint qualifies either later epoch.

## Not implemented or authorized

- interpreting delayed token similarity as causal credit;
- using objective event coordinates as fixed positive or negative value;
- permanent node bias, gate, bandwidth, retained-state or topology changes beyond the rollback window;
- semantic acceptance of a committed update as beneficial or causally correct;
- recovery from rollback CAS failure beyond locking the subject write path;
- an unbounded or cross-generation applied-update ledger;
- physical plasticity cost debit or health-compensated cost experiments;
- content-provenance references actually consumed by the graph;
- automatic conversion of legacy router genes/state into Subject VM nodes or edges;
- topology mutation, developmental expression, token/proposal-readout mutation, node migration or region-capacity evolution;
- a complete general attention allocator, candidate budget competition or lazy payload execution;
- fixed reward, trust, knowledge value, interest formula or group bonus;
- relation/group replacement;
- GPU packed Stage-2/3 execution;
- Epoch 1 panel, paired selection, gene persistence, candidate ledger or subjecthood score.

The next authorized boundary is **Stage 3C-5 guarded commit evaluation and explicit keep-or-revert policy**. It must not infer benefit from objective deltas, must retain a forced-rollback control, and must separate mechanical write safety from any later scientific claim that an update improved behavior.
