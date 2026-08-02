# SE project status

Version: **0.124.0**

## Current scientific task

Version 0.124 implements **Subject VM Stage 3C-10: short paired funnel, update-visibility and branch-divergence diagnostics**.

Stage 3A remains the authoritative long-term internal-history boundary: the unified graph emits a fixed-width continuous token and a bounded event ring stores that token with objective post-commit facts. Historical node IDs, edge IDs, activation masks and complete execution paths are not persisted.

Stage 3B-1 remains the micro-level bridge. Executed node output and actual bandwidth-bounded edge transmission may leave short-lived local eligibility values selected by graph flags and gates. Their signs remain local computational directions, not event value.

Stage 3B-2 and Stage 3C-1 remain explicit bootstrap biases: normalized continuous-token similarity chooses at most one historical event candidate, and the largest still-valid pre-activation local eligibility carrier chooses at most one target per parameter family. These mechanisms shorten early graph shaping; they are not universal attention claims.

Stage 3B-3 forms a graph-controlled six-dimensional parameter-family proposal. Stage 3C-1 binds nonzero components to exact stable node or edge targets. Stage 3C-2 revalidates those targets and forms bounded candidate deltas. Stage 3C-3 verifies exact float32 compare-and-swap, event-level all-or-none semantics and rollback in a private shadow vector. Stage 3C-4 allows an explicitly opted-in live write only inside a fixed short rollback window and records it in a bounded applied ledger. Stage 3C-5 records the same 21-dimensional score-free evidence contract for guarded-live and read-only control windows.

Stage 3C-6 remains outside the runtime learning path. A plan binds one trusted quiescent checkpoint, its file/state/config hashes, exact source tick, common final tick and two explicit branch identities. The only authorized branch configuration difference is `subject_vm.live_write.enabled`. The branch runner preserves shared checkpoint state and stable-ID keyed randomness, persists branch identity in checkpoint lineage, and writes separate final checkpoints.

The exporter accepts only the planned guarded-live and read-only-control checkpoints, verifies their branch identities and final configuration hashes, extracts completed rollback-verified windows, and pairs them by stable subject, source event, window and exact target/update contract. It emits component-wise objective differences and preserves all unpaired windows. It does not produce a scalar score, fixed value weights, automatic keep/revert decision, permanent write authorization or automatic causal conclusion.

Stage 3C-7 remains outside the runtime and consumes one or more Stage-3C-6 exports plus their referenced final checkpoints. It verifies export/checkpoint hashes, reports independent source-state count, paired-window coverage and structured unpaired reasons, inspects rollback failures, pending writes, locked rows, fact clipping and count-only evaluation-cost matching, and records component-wise entity/environment branch divergence. Its default thresholds are explicit engineering screening parameters, not universal scientific sufficiency or subjective value.

Stage 3C-8 remains outside the runtime and consumes checksum-valid Stage-3C-7 assessments that passed their engineering screen. It resolves the referenced Stage-3C-6 exports, treats independent source checkpoints as the highest replicate unit, averages windows within stable subjects, then balances subjects within each source before cross-source comparison. It reports per-coordinate sign, dispersion and central-interval stability for objective facts, absolute activity and count differences. Duplicate source states do not become additional replicates, and conflicting duplicate data are rejected.

Stage 3C-9 adds a reproducible short-study runner and a frozen fixed bootstrap graph so the existing Stage-3C chain can produce infrastructure data without waiting for topology evolution. The bootstrap is explicitly recorded as fixed cognition and not as an evolved result. Read-only control now reserves the same pending target, ledger and window budgets as guarded-live while remaining parameter-read-only and cost-free at the live-write layer. At the export boundary, remaining temporary writes are restored and control reservations released without executing new semantic ticks; incomplete windows are excluded from paired evidence.

The default three-seed pilot produced 38 completed paired windows with full pairing coverage, zero rollback failures, zero fact clipping and matched evaluation costs. The Stage 3C-8 report found no coordinate passing its descriptive sign-and-interval stability screen: most branch differences were exactly or nearly zero, while the few nonzero differences appeared in only one of three sources. This is an engineering pipeline result only; it does not establish beneficial updates, causal credit, attention optimality, learning or subjecthood.

Stage 3C-10 keeps the v0.123 study factors unchanged and adds external diagnostics plus two bounded trace facts. Across the same three sources, all fixed-bootstrap subjects emit tokens and enter the association/update chain. The dominant bottleneck is later: assigned candidates collapse to delay `1` and similarity `1.0`, all safe proposals and all 45 temporary commits target only `node_bias`, and each commit affects one subsequent semantic activation tick. Live parameters change action potentials and sampled probabilities in all three sources, but only two subject-events in one source cross the sampled discrete-action boundary. Exact parameter restoration, control reservation symmetry, counted evaluation cost matching and export-boundary clearing hold in all sources. One source retains non-parameter path dependence after rollback because the changed action already altered objective state.

These diagnostics support an observability conclusion, not a learning conclusion: the data chain is active, the paired contract is intact, and the short fixed bootstrap produces parameter-level effects that are usually too narrow or too brief to become objective-event differences across independent sources. No mechanism parameter was changed in v0.124.

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
- Stage-3C-7 repeated paired-export checksum verification, coverage/unpaired diagnostics and integrity assessment;
- Stage-3C-8 hierarchical source/subject/window aggregation and coordinate-wise sign, dispersion and interval assessment;
- Stage-3C-9 fixed-bootstrap short paired runner, symmetric control admission and export-boundary transient finalization;
- Stage-3C-10 source/subject funnel, update magnitude and exposure, association/eligibility quality, branch divergence and aggregation-sensitivity diagnostics;
- v0.123 trace/checkpoint compatibility for the new bounded diagnostic fields;
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

- `epoch-0-ecological-carriers`: current era. Stage 3C-10 diagnoses the short fixed-bootstrap engineering study without authorizing retention or Epoch 1.
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

The next authorized boundary is a separately versioned, single-variable short-study comparison chosen from the Stage 3C-10 evidence. The current data most directly motivates testing temporary-effect reach or fixed-bootstrap family reachability, but v0.124 changes neither. Permanent retention, scalar value construction, a complete general-attention replacement and Epoch 1 qualification remain unauthorized.
