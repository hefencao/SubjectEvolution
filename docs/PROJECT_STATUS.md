# SE project status

Version: **0.152.0**

## Current iteration identity

- Progress type: **`[MAIN-EXP]` read-only mainline experiment**
- Git title: **`[MAIN-EXP] D1-Z: decompose bootstrap geometry transport failure`**
- Git branch: **`main-exp/stage3c36-geometry-transport`**
- Workflow profile: **`SCIENTIFIC-FREEZE` + versioned `RELEASE-HANDOFF`**
- Runtime/config/checkpoint change: **none**
- Frozen scientific frontier: **Stage 3C-36**
- Next authorized mainline experiment: **Stage 3C-37 query-level exact-tie origin audit**

## Typed task progress tree

```text
SubjectEvolution
├── [MAIN-EXP] Mainline experiment
│   └── D1-Z unified Subject Graph VM
│       ├── [FROZEN] Stage 3C-33 matched-horizon exposure propagation
│       ├── [FROZEN] Stage 3C-34 action/objective-event crossing audit
│       ├── [FROZEN] Stage 3C-35 disjoint-source prerequisite failure
│       ├── [FROZEN] Stage 3C-36 bootstrap-geometry transport decomposition
│       ├── [NEXT]   Stage 3C-37 query-level exact-tie origin audit
│       └── [BLOCKED] crossing replication, retention, learned weights, topology evolution
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
│   ├── [DONE] `se-workspace` owns external result and patch directory configuration
│   ├── [PARKED] automatic inference of local-only versus artifact-handoff intent
│   └── [PARKED] optional full-policy-logit and categorical-draw trace export
│
└── [DOC-GOV] Documentation governance
    └── [DONE] active-document authority, typed task tree and Git handoff contract
```

## Current mainline decision

The candidate-support contract transports exactly: all 18 sources retain 128 requested,
112 assigned, 16 no-candidate, 16 forced and 96 multi-candidate queries with the same
candidate-count histogram. Median winner reuse is also unchanged at 0.4643.

The pooled age-one loss is instead localized to first-state recurrence composition.
Same-first-state queries decline from 344 to 320. Applying the original panel's
conditional selection rates to the new recurrence composition predicts 367.65 age-one
selections, within 1.35 of the observed 369. Holding the original composition while
using the new conditional rates predicts 387.38, essentially the original 387.

The large local-step separation transports (200.2× versus 191.2×). The formal Stage
3C-28 gate is nevertheless tripped because diagnostic ties rise from 1 to 6, lowering
strict age-one wins from 386/387 to 363/369. The aggregate frozen assessments cannot
resolve whether those five additional near-exact ties come from duplicated normalized
directions, float32 quantization or the 1e-8 diagnostic tolerance.

## Frozen evidence boundary

Stage 3C-36 does not authorize Stage 3C-28 or the crossing replication on the failed
panel. It narrows the unresolved transport problem to query-level tie origin; no source,
threshold, addressing, exposure or retention change is authorized.

## Documentation and evidence map

| Need | Authoritative location |
|---|---|
| Current system structure | `docs/ARCHITECTURE.md` |
| Current task and queue | `docs/PROJECT_STATUS.md` |
| Active scientific issues | `docs/SCIENTIFIC_ISSUES.md` |
| Frozen Stage 3C results | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| Current iteration record | `docs/迭代/v0.152_D1-Z_主体图Stage3C36_几何迁移根因分解.md` |
| Executable decision contract | `protocols/decisions/subject_graph_vm_stage3c36_geometry_transport_v1.json` |
| Repository execution rules | `AGENTS.md` |
