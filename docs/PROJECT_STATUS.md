# SE project status

Version: **0.149.0**

## Current iteration identity

- Progress type: **`[MAIN-EXP]` mainline experiment**
- Git title: **`[MAIN-EXP] D1-Z: audit action and objective-event threshold crossings`**
- Git branch: **`main-exp/stage3c34-threshold-crossing`**
- Runtime/config/checkpoint change: **none**
- Frozen scientific frontier: **Stage 3C-34**
- Next authorized mainline experiment: **Stage 3C-35 disjoint-source crossing-taxonomy replication**

Stage 3C-34 is a read-only audit over the frozen Stage 3C-33 eight-arm trajectories.
It localizes the exposure-only alignment contrast at continuous Subject-VM action
potentials, sampled actions, Objective-Fact events, and source-balanced aggregation.

## Typed task progress tree

```text
SubjectEvolution
├── [MAIN-EXP] Mainline experiment
│   └── D1-Z unified Subject Graph VM
│       ├── [FROZEN] Stage 3C-33 matched-horizon exposure propagation
│       ├── [FROZEN] Stage 3C-34 action/objective-event crossing audit
│       ├── [NEXT]   Stage 3C-35 disjoint-source crossing-taxonomy replication
│       └── [BLOCKED] retention, learned weights, topology evolution
│
├── [BRANCH-EXP] Branch experiment
│   └── none active
│
├── [PARAM-EXP] Code-parameter exploration
│   └── none active
│
├── [EVOLVE-ENV] Evolution code — environment/substrate
│   └── [PARKED] persistent multi-pressure environment and source-health work
│
├── [EVOLVE-SUBJECT] Evolution code — subject capability
│   └── [BLOCKED] topology/readout/addressing evolution lacks an authorized
│       mutation, cost, development, inheritance, and neutralization contract
│
├── [ENGINEERING] Runtime, tooling, tests, packaging
│   └── [PARKED] optional full-policy-logit and categorical-draw trace export
│       for exact numeric action-margin measurement
│
└── [DOC-GOV] Documentation governance
    ├── [DONE] active-document authority boundaries
    ├── [DONE] typed Git title and branch prefixes
    └── [DONE] concrete Git command handoff required for every delivery
```

## Current mainline decision

Stage 3C-34 resolves the current nine-source crossing location:

- all nine sources contain exposure-dependent, alignment-dependent Subject-VM
  action-potential divergence;
- six sources do not cross the realized sampled-action boundary;
- seed 12307 crosses the sampled-action boundary in both alignment modes in the same
  way, so the alignment difference-in-differences removes it;
- seeds 12305 and 12308 contain alignment-specific action crossings and are exactly
  the two sources with nonzero Stage 3C-33 source-balanced Objective-Fact effects;
- no source contains a differential Objective-Fact crossing that is later cancelled
  only by source balancing.

The next authorized mainline step is an out-of-sample replication using a disjoint
source checkpoint panel and the unchanged Stage 3C-33/34 protocol. It must preregister
the prediction that alignment-differential sampled-action crossings identify every
nonzero exposure-only fact source. It may not select seeds, alter exposure, add a
value function, or authorize retention.

## Frozen evidence boundary

Stage 3C-34 establishes a narrow causal localization for this panel:

```text
continuous Subject-VM decision divergence in 9/9 sources
  → any sampled-action crossing in 3/9 sources
  → alignment-specific sampled-action crossing in 2/9 sources
  → differential Objective-Fact crossing in the same 2/9 sources
  → surviving source-balanced effect in the same 2/9 sources
```

Four alignment-specific sampled-action crossing events lead to twelve differential
Objective-Fact events, including eight delayed events after the original crossing.
This does not establish value, correct causal credit, learning, keep/revert, or
permanent retention.

The exact numeric distance to the categorical action boundary remains unobservable
because the frozen trace contains Subject-VM residual potentials and selected-action
probability, but not the complete masked policy logits or categorical draw.

## Not implemented or authorized

- scalar reward or fixed value weights;
- automatic keep/revert or permanent graph-parameter retention;
- learned association weights or a general attention allocator;
- Subject VM topology mutation or developmental expression;
- selected-seed reruns or adaptive exposure extension;
- Epoch 1 subjecthood score or claim.

## Documentation and evidence map

| Need | Authoritative location |
|---|---|
| Current system structure | `docs/ARCHITECTURE.md` |
| Current task and queue | `docs/PROJECT_STATUS.md` |
| Active unresolved scientific questions | `docs/SCIENTIFIC_ISSUES.md` |
| Frozen Stage 3C results | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| Current iteration record | `docs/迭代/v0.149_D1-Z_主体图Stage3C34_动作与客观事件跨界审计.md` |
| Executable decision contract | `protocols/decisions/subject_graph_vm_stage3c34_threshold_crossing_v1.json` |
| Repository execution rules | `AGENTS.md` |
