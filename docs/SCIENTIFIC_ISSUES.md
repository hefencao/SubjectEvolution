# Scientific issues

## 1. Purpose

This file is the registry of **active unresolved scientific questions**. It is not a
chronological notebook. A question stays here only while additional evidence could
materially change the project decision.

Status values:

- `OPEN`: authorized next evidence boundary exists;
- `BLOCKED`: prerequisite mechanism, source quality, or evidence contract is missing;
- `PARKED`: scientifically relevant but outside the current mainline;
- `FROZEN`: no longer active; summarized in a result ledger and removed at the next
  documentation cleanup.

Frozen Stage 3C evidence is summarized in
`docs/results/SUBJECT_VM_STAGE3C_RESULTS.md`.

## 2. Active issue registry

| ID | Type | Status | Question | Current evidence boundary |
|---|---|---|---|---|
| SG-01 | Subject VM | OPEN | Do temporary alignment-dependent parameter routes cross discrete action or objective-event boundaries? | Read-only Stage 3C-34 threshold/crossing audit over the frozen Stage 3C-33 trajectories. |
| SG-02 | Replication | OPEN | Why do exposure-dependent trajectory effects appear in only a minority of source checkpoints? | Separate no-divergence, subthreshold-divergence, crossing, and later-cancellation cases without selecting seeds post hoc. |
| SG-03 | Evidence semantics | OPEN | Can component-wise objective facts ever support a retention decision without importing a fixed value function? | No retention study is authorized until a non-scalar, preregistered decision contract exists. |
| SG-04 | Bootstrap generality | PARKED | Which findings depend on the current fixed normalized-dot/latest/top-1 bootstrap rather than the unified graph substrate? | Compare only after the current causal chain is diagnosed; do not replace the allocator during Stage 3C-34. |
| SG-05 | Persistence | BLOCKED | Can a temporary graph-parameter effect persist beneficially across independent sources? | Requires stable downstream evidence and a separate keep/revert protocol; current evidence is insufficient. |
| SG-06 | Topology evolution | BLOCKED | Can topology, readout, and addressing structure evolve without collapsing into undiagnosable search? | Requires explicit costs, mutation/development contracts, neutralization, and a healthy source substrate. |
| ENV-01 | Environment | PARKED | Does the environment provide enough persistent, orthogonal opportunity to sustain differentiated capabilities? | Resume only as `[EVOLVE-ENV]`, with source-health and conservation gates. |
| ENV-02 | Demography | OPEN | Are source checkpoints healthy enough for evolutionary interpretation rather than short-run mechanism diagnostics? | Require population, births, descendants, generation depth, founder replacement, and checkpoint stability gates. |
| SOC-01 | Identity | BLOCKED | How should delayed partner evidence survive entity death without attaching to recycled rows? | Historical stable-subject memory needs explicit retention, inheritance, eviction, and regional-branch semantics. |

## 3. Current mainline issues

### SG-01 — discrete threshold and crossing boundary

Stage 3C-32 established that subject-time alignment changes runtime selector identity
and temporary update routing in every independent source. Stage 3C-33 established
that doubling realized target-tick exposure changes fixed-support downstream event
trajectories in two of nine sources, with no stable Objective-Fact coordinate.

The unresolved question is where the causal chain stops:

```text
alignment
  → historical event identity
  → temporary target/family/delta route
  → continuous internal trajectory
  → discrete action sample
  → objective-event change
```

Stage 3C-34 may read only already frozen trajectories and random/action diagnostics.
It must classify each source and event as:

1. no continuous divergence;
2. continuous divergence but below action threshold;
3. action-threshold crossing without objective-event crossing;
4. objective-event crossing;
5. later cancellation or aggregation masking.

It may not add exposure, change weights, introduce reward, rerun selected seeds, or
choose a threshold after seeing outcomes.

### SG-02 — source dependence and replicate meaning

The independent source checkpoint is the primary replicate. Subjects, windows,
events, and fact coordinates improve within-source measurement but do not increase
the cross-source sample size.

Sparse effects must not be described as stable merely because many within-source
rows are nonzero. Conversely, a zero aggregate may hide offsetting crossings. The
next audit must preserve source identity and event-level support before aggregation.

### SG-03 — objective facts are not value

The current evidence vector contains objective post-commit measurements. Positive
or negative coordinate movement is not inherently beneficial, harmful, desired, or
subjectively valued.

No analysis may:

- sum coordinates with undeclared weights;
- select coordinates because they look favorable;
- infer reward from physical survival or resource abundance alone;
- convert proximity to a historical fact into correct causal credit;
- authorize keep/revert from mixed component directions.

A future retention contract must state how decisions are made without hiding a
fixed human value function inside aggregation.

## 4. Parked architecture-level questions

### SG-04 — fixed bootstrap versus general allocator

The current bootstrap is useful because it makes candidate admission, ranking,
target selection, transaction safety, and rollback diagnosable. Its biases are
explicit: bounded history, normalized-dot similarity, latest/top-1 ordering, fixed
visible readouts, and bounded local-eligibility target selection.

Evidence obtained under this bootstrap applies to that operating point. It does not
prove a universal attention mechanism. Replacing it before the current causal chain
is understood would combine allocator design and downstream-effect diagnosis in one
unidentifiable change.

### SG-06 — topology and developmental evolution

Topology mutation is not merely another parameter sweep. It changes the hypothesis
class and may require an additional Git branch. Before authorization it needs:

- finite structural and execution costs;
- mutation and developmental timing;
- inheritance and reset semantics;
- neutralization and shared-checkpoint controls;
- source-health qualification;
- bounded graph size and deterministic checkpoint identity.

## 5. Environment and demographic questions

### ENV-01 — persistent differentiated opportunity

Previous environment work established resource, geography, conversion, storage,
turnover, terrain, and signal boundaries. The unresolved scientific question is not
whether more fields can be added, but whether independent persistent pressures are
strong enough to maintain differentiated capabilities across generations without
hard-coded ecological roles.

Any resumed work is evolution code and must be typed `[EVOLVE-ENV]`, not hidden in a
mainline Subject VM experiment.

### ENV-02 — source health

Mechanism evidence from a rapidly collapsing population is not ordinary
representative evidence. A source may still be useful for semantics debugging, but
it must be labelled accordingly. Recovery, qualification failure, and catastrophic
termination are distinct outcomes.

## 6. What does not belong here

The following are engineering or release issues, not scientific issues:

- unavailable GPU/CUDA runtime;
- allocator cache behavior;
- test discovery and source-fingerprint exclusions;
- console-entry metadata;
- packaging, patch replay, archive pruning, or file permissions;
- stale version assertions;
- documentation formatting defects.

They belong in issue tracking, iteration notes, validation reports, or the
engineering branch of `PROJECT_STATUS.md`.

## 7. Update rule

A provisional observation stays in the current iteration note or analysis artifact.
It enters this file only after validation and only when it creates or materially
changes an unresolved question. Once a question is resolved, superseded, or parked
without an authorized next boundary, its detailed history moves to a frozen result
ledger or changelog rather than remaining as another version-labelled section.
