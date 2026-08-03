# SubjectEvolution architecture

## 1. Purpose and authority

This document describes the **current structural boundaries** of the project. It is
not a version diary, experiment report, task list, or scientific-issue backlog.

Architecture statements belong here only when they remain true after the iteration
that introduced them. Frozen experimental findings belong in
`docs/results/`; unresolved scientific questions belong in
`docs/SCIENTIFIC_ISSUES.md`; current work belongs in `docs/PROJECT_STATUS.md`;
and release history belongs in `docs/CHANGELOG.md`.

The primary design objective is to support simulation and evolution of subject-like
internal organization without preassigning reward, human social roles, or fixed
semantic value to objective world coordinates.

## 2. System map

```text
configuration and identity contracts
                ↓
environment / physiology / evolution / differentiation / knowledge / subjects
                ↓
runtime orchestration and checkpoint ownership
                ↓
command-line interfaces and observation-only GUI bridge

analysis / experiments → runtime and domain read interfaces
runtime and domains ✕→ analysis, experiments, or GUI policy
```

Primary Python package layout:

```text
src/se/
├── analysis/          external, read-only or post-run assessments
├── cmd/               console entry points
├── differentiation/   inherited differentiation mechanisms
├── env/               world fields and settlement
├── evolution/         mutation, reproduction, selection infrastructure
├── experiments/       declared branch and study runners
├── gui/               Python observation/control bridge
├── knowledge/         transferred-copy and verification mechanisms
├── runtime/           authoritative simulation orchestration
├── subject_vm/        unified subject graph runtime and trace state
├── subjects/          subject ownership and lifecycle
└── cfg.py             normalized configuration contracts
```

The independent native workspace `src/gui/` is built by its own toolchain. It is
outside the Python release-freshness fingerprint used by `make test`.
`src/se/gui/` remains ordinary Python product code and stays inside test and release
freshness boundaries.

## 3. Runtime ownership

### 3.1 Authoritative world state

The runtime owns tick order, entity lifecycle, random-stream progression,
checkpoint boundaries, branch identity, and final reporting materialization.
Domain systems may propose intents or local updates but cannot independently
commit world state outside the runtime settlement order.

A request and its realization are distinct:

```text
policy / graph output
    → requested action or requested resource vector
    → feasibility, competition, and world settlement
    → realized action, transfer, resource, and objective event
```

Requested values are causal intents. Realized values are constrained outcomes and
must not be substituted for requests in analysis or credit attribution.

### 3.2 Backend contract

- `auto` is the high-level default and records the resolved backend.
- `cpu` is the authoritative semantic reference.
- accelerated backends must preserve checkpoint-authoritative state and reporting
  boundaries.
- parity is a validation boundary, not a scientific intervention.
- allocator caches, compilation artifacts, and device availability are engineering
  concerns and cannot be interpreted as biological or cognitive effects.

### 3.3 Reporting and checkpoint materialization

Reporting and checkpoint export must observe one authoritative materialized state
per tick. Device mirrors may be deferred internally, but final summaries,
checkpoints, branch exports, and reproducibility assessments must identify the
materialization tick and source.

## 4. Configuration, checkpoint, and branch identity

Configuration normalization is part of experiment identity. A study must bind:

- normalized configuration hash;
- source checkpoint file and authoritative state hash;
- source tick and final tick;
- explicit branch role and intervention identity;
- random-stream ownership;
- allowed configuration differences;
- export and assessment checksums.

A branch runner may change only the factors declared by its protocol. Unrelated
configuration changes, source replacement, post-hoc horizon extension, or missing
lineage fields invalidate paired interpretation.

Checkpoint compatibility may rebuild absent legacy fields only through explicit
versioned defaults. A restored checkpoint must not silently activate a newer
mechanism or inherit state from a recycled entity row.

## 5. Environment and embodied substrate

The world provides spatially persistent resource, terrain, signal, and material
constraints. Subject mechanisms act through existing action and settlement
interfaces rather than receiving direct role bonuses.

Current stable boundaries include:

- multiple resource channels with distinct request, availability, storage,
  conversion, and conservation paths;
- inherited capacities and affinities that pay explicit structural or use costs;
- spatial resource geography, terrain resistance, signal openness, and local
  competition;
- delayed raw-resource metabolism and residual-material settlement;
- bounded physiology, repair, fatigue, and messenger state;
- source-health gates that prevent ordinary mechanism interpretation after
  catastrophic demographic collapse.

Environmental diversity and subject capability are evolution-code work, not mere
experiment parameters. Changes to them must be typed separately in the task tree
and Git title.

## 6. Legacy social and knowledge baselines

Material-interest and transferred-knowledge mechanisms remain fixed-cognition
comparison baselines. They may produce delayed, auditable evidence but do not own
the primary Subject VM action-residual path.

Stable boundaries:

- material giving/receiving and knowledge verification settle in separate channels;
- transferred-copy attribution uses stable source identity;
- evidence cannot be attached to a recycled entity row;
- missing historical identity remains orphaned rather than reassigned;
- group detection is observational unless a separately authorized epoch contract
  grants control authority.

These baselines must not be expanded into a second competing subject network.

## 7. Unified Subject Graph VM

### 7.1 Ownership and topology

The Subject VM is one partitioned node/edge graph owned by a stable subject. Regions
may provide initial shaping bias, but they are not separate semantic networks and
do not constitute evidence of cognition, role, interest, or value.

The graph currently supports fixed topology and bounded state. Topology mutation,
region-capacity evolution, developmental expression, migration, and permanent
retention remain unauthorized.

### 7.2 Activation boundary

The activation adapter reads the approved objective input ports, executes generic
node and edge operators in a deterministic phase order, and publishes bounded
residuals to existing action interfaces. The action system remains the only owner
of feasibility masks, categorical sampling, intents, and world settlement.

Same-phase array order cannot create hidden zero-delay dependencies. Delayed edges
read explicitly retained prior state.

### 7.3 Long-term event trace

The long-term trace stores a fixed-width continuous token and bounded objective
post-commit facts. It does not persist complete execution paths, activation masks,
full node/edge identity histories, or human semantic labels.

Objective facts are measurements, not rewards. Their coordinates remain separate;
no scalar value is formed by default.

### 7.4 Local eligibility and delayed association

Short-lived local eligibility values may be written only from actual bounded node
output or actual bounded edge transmission selected by graph flags and gates.
Their signs are computational directions, not event valence.

Delayed association is a bounded bootstrap addressing mechanism:

- candidates are older same-subject events inside explicit delay bounds;
- normalized visible-token similarity controls admission and ranking;
- the current fixed bootstrap uses at most two visible coordinates and a bounded
  candidate count;
- deterministic latest/top-1 ordering remains an engineering baseline;
- association records addressing diagnostics, not causal truth or value.

The fixed bootstrap exists to make early graph shaping diagnosable. It is not a
claim of universal attention or a final general allocator.

### 7.5 Parameter proposals and temporary transactions

Graph-controlled readouts form bounded parameter-family proposals. A valid proposal
must bind to an exact stable node or edge target, pass safety revalidation, and enter
an atomic shadow transaction before any live write.

Guarded live writes are explicitly opt-in, temporary, and rollback-bound. The live
ledger records transaction identity, target, family, bounded delta, pre/post value,
commit tick, rollback due tick, and finalization status. Read-only control reserves
matching budgets without changing parameters.

Permanent keep/revert, learned weighting, scalar reward, and retention are not part
of the current runtime.

### 7.6 Experiment-only alignment policy

The trace runtime supports explicit experiment-only association-coordinate policies
for subject-time alignment studies. Identity and cyclic-donor modes share one stable
sort/copy implementation and preserve the exact per-tick float32 coordinate
multiset. Policy, port, and origin tick are bound into branch identity.

These policies exist only to test causal routing. They do not define a production
attention mechanism.

## 8. Evidence pipeline

The evidence stack is intentionally outside the runtime learning path:

```text
shared source checkpoint
    → declared paired or multi-arm branch plan
    → guarded-live / read-only-control execution
    → export with branch and lineage verification
    → integrity assessment
    → source-balanced component reproducibility assessment
    → frozen result ledger
```

The highest ordinary replicate unit is the independent source checkpoint, not the
number of entities, windows, events, or coordinates inside that source.

Assessments must preserve:

- paired and unpaired support;
- rollback and pending-write status;
- fact clipping and evaluation-cost checks;
- component-wise facts without hidden scalarization;
- source-balanced aggregation;
- exact distinction between manipulation failure, support failure, identity error,
  and a genuinely small or path-dependent effect.

A longer intervention must separately prove realized dose, fixed common evaluation
support, and sufficient observation coverage.

## 9. Study and release tooling

Studies are declared in `workflow.toml`. Every parameter has a type, default, and
description. `se-study show` renders exact argv and `se-study run` invokes without a
shell. Result packaging is an explicit workflow step.

Project-external operator paths are owned by `se-workspace`, which reads and writes the
ignored `.se-workspace.toml`. `se-workspace config` sets result and patch directories;
`se-workspace path result|patch` prints one configured path for scripts and Git handoff.
The study runner consumes result-directory settings but does not own workspace
configuration.

Validation and artifact depth are selected through `docs/WORKFLOW_PROFILES.md`.
Small fixes do not automatically run a release workflow. Public CLI, package, or shared
runtime changes use the standard-code profile, scientific freezes use the scientific
profile, and patch/archive checks run only for a release handoff.

Release packaging, patch replay, archive governance, and isolated wheel/sdist checks
validate transferability; they do not change scientific conclusions.

## 10. Documentation boundaries

| Document | Contains | Must not contain |
|---|---|---|
| `ARCHITECTURE.md` | current structural contracts | per-version results, task queue, provisional claims |
| `PROJECT_STATUS.md` | current typed task tree and frozen headline state | stage-by-stage history, test reports |
| `SCIENTIFIC_ISSUES.md` | active unresolved scientific questions | release notes, resolved chronology, engineering defects |
| `docs/results/` | frozen, validated result ledgers | provisional interpretation |
| `docs/迭代/` | current iteration design, work log, and final frozen note | cross-version authority |
| `PROJECT_GOVERNANCE.md` | durable process and inference rules | raw experiment narrative |
| `CHANGELOG.md` | versioned delivered changes | scientific backlog |

Detailed Subject VM protocol and mechanism semantics remain in
`docs/PARTITIONED_SUBJECT_GRAPH_VM.md` and `protocols/decisions/`.
