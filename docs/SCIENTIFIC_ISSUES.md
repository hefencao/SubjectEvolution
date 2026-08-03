# Scientific issues

## 1. Purpose

This file contains only active unresolved scientific questions. Frozen evidence is
summarized in `docs/results/`; engineering and release defects do not belong here.

Status values are `OPEN`, `BLOCKED`, and `PARKED`.

## 2. Active issue registry

| ID | Type | Status | Question | Current evidence boundary |
|---|---|---|---|---|
| SG-02 | Bootstrap transport | OPEN | Why does the Stage 3C-27 fixed-bootstrap geometry qualification fail on the first disjoint source panel? | Stage 3C-35 stops before Stage 3C-28; the crossing classifier remains untested out of sample. |
| SG-03 | Evidence semantics | OPEN | Can component-wise objective facts support any retention decision without importing a fixed value function? | No retention study is authorized until a non-scalar decision contract exists. |
| SG-04 | Bootstrap generality | PARKED | Which results depend on normalized-dot/latest/top-1 bootstrap addressing? | Compare only after the current crossing result is independently replicated. |
| SG-05 | Persistence | BLOCKED | Can a temporary graph-parameter effect persist under an independently justified decision rule? | Requires replicated downstream evidence and a separate keep/revert contract. |
| SG-06 | Topology evolution | BLOCKED | Can topology, readout, and addressing evolve without collapsing into undiagnosable search? | Requires costs, mutation/development timing, inheritance, neutralization, and healthy source qualification. |
| SG-07 | Decision-boundary observability | BLOCKED | What is the exact numeric distance from a continuous internal divergence to the categorical sampled-action boundary? | Requires a separately typed export-only instrumentation change that records full masked policy logits and the counter-based categorical draw without changing sampling semantics. |
| ENV-01 | Environment | PARKED | Does the environment sustain persistent orthogonal opportunity for differentiated capabilities? | Resume only as `[EVOLVE-ENV]` with conservation and source-health gates. |
| ENV-02 | Demography | OPEN | Are source checkpoints healthy enough for evolutionary interpretation rather than short-run mechanism diagnosis? | Require population, descendant, generation-depth, founder-replacement, and checkpoint-stability gates. |
| SOC-01 | Identity | BLOCKED | How should delayed partner evidence survive entity death without attaching to recycled rows? | Requires historical subject identity with retention, inheritance, eviction, and regional-branch semantics. |

## 3. SG-02 — bootstrap-geometry transport failure

Stage 3C-35 used disjoint source seeds 12401–12409. The original panel has 386/387
strict-geometry age-one selections; the replication panel has 363/369. Exact
latest-tie use rises from 1/864 to 6/864. The frozen Stage 3C-28 prerequisite therefore
fails, and only sources 12402 and 12408 satisfy all three per-source diagnostics.

The active question is which already-recorded factor explains the transport loss:
candidate opportunity composition, first-state recurrence, local second-coordinate
step geometry, or their interaction. The next audit must be read-only over the two
frozen panels. It may not replace seeds, relax the gate, change addressing, or run the
Stage 3C-33 intervention.

## 4. SG-03 — objective facts are not value

Objective post-commit measurements have no built-in positive or negative meaning.
No analysis may sum coordinates with undeclared weights, select favorable-looking
coordinates, infer reward from resource abundance, or authorize keep/revert from mixed
component directions.

## 5. SG-07 — exact action-margin observability

The frozen trace exports the Subject-VM residual action-potential vector and the
probability of the selected action. It does not export the complete masked policy
logit vector or the exact counter-based categorical draw. Therefore Stage 3C-34 can
identify observed crossings but cannot calculate a numeric distance to the sampled
action boundary for non-crossing events.

Adding those fields is an `[ENGINEERING]` export-instrumentation task, not a scientific
result. It must prove semantic neutrality, fixed random-stream identity, bounded trace
cost, checkpoint compatibility, and unchanged sampled actions before any margin audit.

## 6. Parked environment and topology questions

Environment changes must be typed `[EVOLVE-ENV]`; topology, genetics, developmental
expression, and inherited graph capability changes must be typed `[EVOLVE-SUBJECT]`.
Neither may be inserted into the current fixed-bootstrap mainline as an unlabelled
experiment.

## 7. What does not belong here

GPU availability, test discovery, source fingerprints, console-entry metadata,
packaging, patch replay, archive pruning, file permissions, and Git command formatting
are engineering or delivery matters, not scientific issues.

## 8. Update rule

Provisional observations remain in analysis artifacts or the current iteration note.
A validated result enters `docs/results/` once. This registry changes only when an
unresolved question is created, materially narrowed, blocked, or parked.
