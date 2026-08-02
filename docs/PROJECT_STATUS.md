# SE project status

Version: **0.120.0**

## Current scientific task

Version 0.120 implements **Subject VM Stage 3C-6: shared-checkpoint paired-evaluation planning, branch identity and score-free export**.

Stage 3A remains the authoritative long-term internal-history boundary: the unified graph emits a fixed-width continuous token and a bounded event ring stores that token with objective post-commit facts. Historical node IDs, edge IDs, activation masks and complete execution paths are not persisted.

Stage 3B-1 remains the micro-level bridge. Executed node output and actual bandwidth-bounded edge transmission may leave short-lived local eligibility values selected by graph flags and gates. Their signs remain local computational directions, not event value.

Stage 3B-2 and Stage 3C-1 remain explicit bootstrap biases: normalized continuous-token similarity chooses at most one historical event candidate, and the largest still-valid pre-activation local eligibility carrier chooses at most one target per parameter family. These mechanisms shorten early graph shaping; they are not universal attention claims.

Stage 3B-3 forms a graph-controlled six-dimensional parameter-family proposal. Stage 3C-1 binds nonzero components to exact stable node or edge targets. Stage 3C-2 revalidates those targets and forms bounded candidate deltas. Stage 3C-3 verifies exact float32 compare-and-swap, event-level all-or-none semantics and rollback in a private shadow vector. Stage 3C-4 allows an explicitly opted-in live write only inside a fixed short rollback window and records it in a bounded applied ledger. Stage 3C-5 records the same 21-dimensional score-free evidence contract for guarded-live and read-only control windows.

Stage 3C-6 remains outside the runtime learning path. A plan binds one trusted quiescent checkpoint, its file/state/config hashes, exact source tick, common final tick and two explicit branch identities. The only authorized branch configuration difference is `subject_vm.live_write.enabled`. The branch runner preserves shared checkpoint state and stable-ID keyed randomness, persists branch identity in checkpoint lineage, and writes separate final checkpoints.

The exporter accepts only the planned guarded-live and read-only-control checkpoints, verifies their branch identities and final configuration hashes, extracts completed rollback-verified windows, and pairs them by stable subject, source event, window and exact target/update contract. It emits component-wise objective differences and preserves all unpaired windows. It does not produce a scalar score, fixed value weights, automatic keep/revert decision, permanent write authorization or automatic causal conclusion.

The v0.110 single-owner rule remains unchanged. Subject VM is the sole optional action-potential residual owner when enabled; legacy knowledge/latent/working-memory routes remain fixed-cognition comparison baselines and cannot coexecute on the primary path.

## Engineering status

Implemented and tested:

- Stage-1 fixed-capacity unified graph storage and lifecycle/checkpoint ownership;
- Stage-2 deterministic bounded CPU-reference activation and action-potential integration;
- v0.110 routing-ownership registry and policy/configuration conflict guards;
- Stage-3A continuous graph-produced token and bounded objective-event ring;
- Stage-3B-1 local node/edge eligibility with deterministic decay and expiry;
- Stage-3B-2 bounded delayed association candidates with explicit unassigned outcomes;
- Stage-3B-3 graph-requested parameter-family proposals without fixed event value;
- Stage-3C-1 pre-activation exact target binding under a replaceable bootstrap selector;
- Stage-3C-2 bounded candidate deltas with target revalidation, clips, L1 budget and parameter projection;
- Stage-3C-3 exact all-or-none shadow CAS, apply and rollback evidence;
- Stage-3C-4 explicit opt-in guarded live commits, bounded applied ledger and deterministic pre-activation rollback;
- Stage-3C-5 guarded-live/read-only objective evaluation windows with identical evidence shape;
- Stage-3C-6 source-checkpoint quiescence checks and deterministic plan identity;
- explicit guarded-live/read-only branch identities bound to source state, branch config and final tick;
- branch identity persistence in final checkpoint lineage;
- completed-window extraction and component-wise paired export without scalarization;
- explicit preservation of unpaired windows and failed pairing visibility;
- fixed 21-dimensional fact sums, absolute sums, maximum absolute values and event counts without a scalar score;
- birth/death/compaction/clone/checkpoint handling through the existing stable-owner lifecycle;
- exact disabled/default normalization preserving frozen legacy configuration identities;
- no engine-defined event value, automatic keep/revert choice, permanent retention or additional runtime random-number consumption.

D1-X/Y and the latent/working-memory policy family remain:

```text
rejected-as-primary-subject-model
retained-as-fixed-cognition-baseline
```

They retain engineering and comparison value but own neither Subject VM state nor the primary optional action route.

## Epoch milestones

- `epoch-0-ecological-carriers`: current era. Stage 3C-6 is an engineering branch/export contract only.
- `epoch-1-entity-subject-prototype`: not started. It still requires delayed parameter use, controlled intervention, baseline exceedance, cost compensation and independent replication.
- `epoch-2-group-subject-prototype`: not started. Candidate/group graphs remain observational and own no rules or Subject VM state.

No supplied checkpoint qualifies either later epoch.

## Not implemented or authorized

- interpreting delayed token similarity as causal credit;
- using objective event coordinates as fixed positive or negative value;
- scalarizing Stage 3C-5/3C-6 fact vectors;
- automatic causal attribution from a paired export;
- automatic keep/revert or permanent parameter retention;
- semantic acceptance of a committed update as beneficial or causally correct;
- recovery from rollback CAS failure beyond locking the subject write path;
- an unbounded or cross-generation applied-update/evaluation ledger;
- physical plasticity cost debit or health-compensated cost experiments;
- content-provenance references actually consumed by the graph;
- automatic conversion of legacy router genes/state into Subject VM nodes or edges;
- topology mutation, developmental expression, token/proposal-readout mutation, node migration or region-capacity evolution;
- a complete general attention allocator, candidate budget competition or lazy payload execution;
- fixed reward, trust, knowledge value, interest formula or group bonus;
- relation/group replacement;
- GPU packed Stage-2/3 execution;
- Epoch 1 panel, paired selection, gene persistence, candidate ledger or subjecthood score.

The next authorized boundary is a **bounded Stage 3C-7 paired-evidence adequacy and integrity assessment contract**. It may report coverage, pairing loss, rollback failures, clipping, branch divergence and cost matching across independently repeated shared-checkpoint pairs, but must not convert objective coordinates into a universal scalar value or automatically retain updates.
