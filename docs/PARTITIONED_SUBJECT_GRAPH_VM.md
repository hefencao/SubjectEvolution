# Partitioned Subject Graph VM

Status: **current mechanism contract**
Contract generation: **v1**
Repository review: **v0.154**

This document defines the active Subject Graph VM architecture and safety boundaries. It is not
a version diary or experiment-results ledger. Historical Stage 3C conclusions are summarized in
`docs/results/SUBJECT_VM_STAGE3C_RESULTS.md`; executable details live in
`protocols/decisions/`.

## 1. Architectural decision

SubjectEvolution uses one partitioned, evolvable subject graph rather than one
programmer-defined ledger or network for each named benefit, memory, trust, knowledge, or
policy function.

The VM provides:

- one node and edge identity system;
- initially biased computational regions;
- one shared routing substrate;
- distinct activation and delayed-update phases;
- bounded provenance, token, eligibility, and transaction state;
- no built-in reward, trust, hostility, knowledge value, social role, or group preference.

The project may prescribe a general cognitive architecture to make long-horizon organization
computationally reachable. It must not prescribe the concrete cognition that occupies that
architecture.

## 2. Scope and non-goals

The VM is a substrate for studying whether persistent internal organization can arise and exert
causal influence. It does not:

- define universal utility or reward;
- assign subjective valence to objective facts;
- define friends, enemies, roles, loyalty, or group membership;
- require actor-critic or another named cognitive decomposition;
- make attribution, memory, interest, and decision permanently separate services;
- replace observer-side continuation and counterfactual analysis;
- authorize learning, retention, or subjecthood from score geometry alone.

D1-X/Y semantic ledgers remain fixed-cognition comparison baselines and compatibility fixtures,
not the primary scientific model.

## 3. One graph with biased regions

Regions are developmental and scheduling priors. They share graph identity and may later overlap,
change capacity, or exchange function.

### 3.1 Fast sensorimotor region

- updates at policy cadence;
- reads immediate observation and body state;
- supports the minimal role-neutral action path;
- has low persistence and bounded cost;
- may contribute action potentials.

### 3.2 Persistent-state region

- retains bounded internal state across ticks;
- supports configured decay and overwrite;
- pays capacity and duration cost;
- can be read and written through the shared router.

### 3.3 Delayed-association region

- observes objective events only after world settlement;
- can compare later facts with bounded earlier graph-produced tokens;
- may propose modulation of still-live local eligibility;
- cannot alter the action whose consequence has not yet occurred.

### 3.4 Integrative-drive region

- combines immediate, retained, and delayed state;
- may influence action-channel potentials;
- permits recurrence and overlapping interest-like and decision-like organization;
- receives no privileged reward input.

Region names are engineering labels, not evidence of cognitive function.

## 4. Unified node, edge, and storage contracts

### 4.1 Node contract

An expressed node has bounded, versioned fields for:

- stable node identity within subject-lineage state;
- region and update schedule;
- role-neutral operator;
- expression and activation gates;
- internal state and retention;
- optional trace readout port and gate;
- plasticity participation;
- structural, execution, and retention costs.

### 4.2 Edge contract

An expressed edge has bounded fields for:

- source node or approved external port;
- target node or approved output port;
- weight or gate;
- delay, bandwidth, and persistence;
- activation and delayed-phase permissions;
- eligibility/plasticity participation;
- structural and use cost.

Memory, knowledge, action, and latent computation cannot each invent incompatible edge identity.

### 4.3 Storage and lifecycle

The VM uses fixed-capacity storage with explicit occupancy and stable subject binding. Lifecycle
operations must handle:

- initialization and disabled null state;
- entity birth, death, compaction, and slot reuse;
- structural inheritance with dynamic-state reset where declared;
- checkpoint save/restore and clone;
- regional branch construction;
- deterministic clearing of retired rows.

World history, graph token history, local eligibility, subject-owned memory, and analysis output
are separate capacities.

## 5. Ownership and dependency direction

The existing action strategy remains the minimal inherited sensorimotor baseline. Feasibility
masks, categorical sampling, intents, and world settlement remain the physical action authority.

When enabled, Subject VM is the sole optional primary-path action-potential residual owner.
Legacy knowledge residual, latent router, quantized working-memory, and sparse-selection routes
may remain for historical checkpoints and baselines but cannot coexecute as competing residual
owners.

Knowledge provenance remains an objective external store. Functional modules remain embodied
mechanisms. Candidate-subject and group graphs remain observations. None is copied wholesale into
Subject VM identity or state.

No automatic migration converts old semantic genes, memory coordinates, or benefit ledgers into
Subject VM nodes and edges.

## 6. Causal execution phases

### 6.1 Activation

```text
objective input ports and retained graph state
→ scheduled graph activation
→ bounded node and edge transmission
→ action-potential output ports
→ existing policy masks and sampling
→ world execution and settlement
```

Zero-delay routing is limited to permitted earlier activation phases. Other recurrence reads
previous retained state or explicit delayed edges.

### 6.2 Objective trace

After settlement, the runtime may append a bounded event record containing:

- event and tick identity;
- stable participating subject identity;
- executed action and physical target;
- objective pre/post facts;
- actual content or signal provenance;
- bounded graph-produced continuous token;
- physically defined parent/source event references.

The trace does not persist a whole executed graph path.

### 6.3 Local eligibility

Graph-owned node and edge eligibility marks arise only from actual bounded activation or
transmission. They decay, expire, checkpoint, clone, and clear under explicit lifecycle rules.
They are not copied into long-lived event history and carry no fixed value.

### 6.4 Delayed association

A later event may request one bounded historical candidate from the same stable subject history.
Candidate admission is controlled by declared delay, nonzero-token, threshold, and control-port
rules. Assignment may remain empty.

An association stores identity, tick, delay, and similarity. It does not assert causality,
correctness, value, or semantic equivalence.

### 6.5 Modulation proposal

A bounded delayed association may propose a target family, carrier, and signed delta only when
an eligible local carrier remains live. Proposal generation is separate from parameter update.
Objective facts are retained component-wise and are not converted into reward.

### 6.6 Shadow transaction and guarded live write

Shadow transactions validate target resolution, compare-and-swap preconditions, delta bounds,
branch identity, and rollback without changing authoritative parameters.

Guarded live writes additionally require explicit opt-in, matching read-only control reservation,
later-tick visibility, a bounded exposure horizon, rollback, and export-boundary finalization.
Pending or overdue transactions make the evidence incomplete.

Permanent retention is not implemented.

### 6.7 Objective evaluation

Evaluation records objective post-commit facts without assigning scores. Live and control
branches preserve component-wise evidence, branch identity, source lineage, evaluation cost, and
support. No automatic keep/revert decision is made.

## 7. Bootstrap readout and addressing

The current experiment-only bootstrap may expose a small number of role-neutral graph readout
coordinates and use normalized-dot candidate addressing with a declared threshold, delay window,
latest-on-runtime-tie policy, and top-1 selection.

These are fixed engineering shaping aids, not a universal attention architecture. Their
coordinates, score, rank, margin, winner age, reuse, or basin occupancy have no fixed subjective
meaning.

The runtime score comparator is authoritative for selection semantics. Analysis-only tolerances
or bins must be labelled as diagnostics and cannot be substituted for runtime tie semantics.
Qualification overlays may reinterpret a diagnostic classification when checksum-bound evidence
shows a mismatch, but may not rewrite historical artifacts.

## 8. Experiment-only interventions

The runtime may expose explicit experiment-only policies when a frozen protocol requires a
causal manipulation. Current examples include subject-time coordinate identity and cyclic donor
alignment modes.

An experiment-only intervention must:

- be disabled by default;
- enter normalized configuration and branch identity;
- preserve declared candidate opportunity and compute/storage budgets;
- share one implementation path across treatment and control where possible;
- prove the manipulation occurred;
- avoid adding semantic value or a production policy.

Such policies are scientific instruments, not automatically evolvable mechanisms.

## 9. Safety invariants

The VM mechanically enforces or requires tests for:

1. no same-action feedback from an unrealized consequence;
2. no diagnostic label feeding back into runtime cognition;
3. no whole-network execution history in long-lived event storage;
4. bounded token, event, eligibility, and transaction capacity;
5. later-tick-only visibility of delayed updates;
6. immutable world provenance;
7. exact source, configuration, branch, and checkpoint lineage;
8. rollback or explicit finalization before evidence export;
9. no hidden scalar reward or coordinate valence;
10. no competing ownership of the action-residual path.

## 10. Development, evolution, and cost boundary

Random founders must not pay mature-graph costs. The cost model separates:

- unexpressed structure;
- expressed structural maintenance;
- node activation;
- edge use and bandwidth;
- retained state by capacity and duration;
- cross-region transport where configured;
- delayed updates;
- development, duplication, deletion, and repair.

Topology, region capacity, migration, duplication, deletion, inherited readout, and addressing
evolution remain blocked until a separately typed `[EVOLVE-SUBJECT]` contract defines mutation,
development, inheritance, cost, neutralization, and source-health requirements.

## 11. Evidence and qualification

Formal evidence follows:

```text
qualified independent source checkpoint
→ declared paired or multi-arm branch plan
→ guarded-live and matching read-only control
→ verified export and finalization
→ integrity assessment
→ source-balanced component assessment
→ frozen result ledger
```

The independent source checkpoint is the ordinary replicate. Entities, windows, events,
coordinates, and ticks inside one source are dependent observations.

Assessments distinguish:

- prerequisite/support failure;
- manipulation or dose failure;
- identity, lineage, or export failure;
- observation-coverage failure;
- path-dependent or source-sparse effect;
- source-replicated effect.

Mixed component directions cannot be collapsed into a hidden utility score.

## 12. Implementation boundaries

The canonical implementation lives under `src/se/subject_vm/`:

- configuration and port contracts;
- storage and lifecycle;
- activation and runtime orchestration;
- trace and delayed association;
- eligibility and modulation;
- transactions, guarded live write, and update safety;
- evaluation and export;
- ownership and binding.

Integration points remain thin:

- global configuration owns versioned schema only;
- runtime orchestration calls phase boundaries;
- action policy consumes bounded potentials but does not own graph internals;
- checkpointing delegates graph snapshot and restore;
- evolution delegates lifecycle and, when authorized, mutation;
- reporting is read-only.

Do not relocate Subject VM internals into social, knowledge, or monolithic simulation modules
merely because related data already exists there.

## 13. Current capability boundary

Implemented substrate capabilities include:

- inert graph schema and lifecycle;
- bounded activation routing and action-potential output;
- continuous token and objective-event trace;
- local eligibility carriers;
- delayed candidate association;
- bounded modulation proposal;
- shadow transactions;
- guarded temporary live writes and rollback;
- score-free objective evaluation;
- paired/multi-arm export, integrity, and reproducibility assessment;
- experiment-only alignment interventions;
- external read-only diagnostic studies.

Not authorized or not implemented as a general capability:

- automatic value assignment;
- automatic keep/revert;
- permanent retention;
- learned attention or addressing weights;
- online topology evolution;
- semantic partner, trust, or role networks;
- Epoch 1 qualification or subjecthood claims.

Current scientific frontier and next work are intentionally omitted here; see
`docs/PROJECT_STATUS.md` and `docs/SCIENTIFIC_ISSUES.md`.

## 14. Authoritative references

| Need | Authority |
|---|---|
| Project-level permission and interpretation | `PROJECT_CHARTER.md` |
| Cross-version inference rules | `PROJECT_GOVERNANCE.md` |
| Current system dependency structure | `ARCHITECTURE.md` |
| Machine-readable VM decisions | `protocols/decisions/subject_graph_vm_*.json` |
| Frozen Stage 3C results | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| Current task frontier | `PROJECT_STATUS.md` |
| Active open questions | `SCIENTIFIC_ISSUES.md` |

If prose and an executable decision protocol disagree for a specific study, the frozen protocol
controls execution. Neither can exceed the interpretation limits in the charter.
