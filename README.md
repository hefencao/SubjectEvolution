# SubjectEvolution v0.132.0

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

The project is building a **partitioned unified subject graph** with one node/edge identity space, bounded continuous internal tokens, short-lived local eligibility, delayed association, explicitly guarded temporary parameter writes, exact rollback, and score-free paired evidence. The fixed bootstrap graph and selectors remain replaceable engineering shaping aids, not evolved topology or a universal attention claim.

Version 0.132.0 implements **Subject VM Stage 3C-18: bounded association candidate-allocation audit**. It holds the reachable Stage-3C-16 `edge_forward_gate` carrier-on panel and the Stage-3C-17 latest-on-tie rule fixed, then changes only the maximum selected historical candidates per current event from one to two. The two-candidate arm uses an equal-weight mean of the two objective-fact vectors, still emits at most one modulation proposal, and retains the same event delta budget.

Across nine independent sources, top-2 adds 864 secondary references and 28 modulation proposals, but it does not increase unique historical-event coverage or guarded-live commits. Both arms remain 0/21 stable objective coordinates. This establishes that bounded candidate cardinality is a material fixed-bootstrap allocation factor; it does not validate equal weights, causal credit, learning, value, retention, or a general attention mechanism.

## Workspace layout

- [`studies/`](studies/README.md): study design, protocols, workflows and frozen evidence.
- [`runs/`](runs/README.md): runtime trajectories and explicit replay checkpoints.
- [`analyses/`](analyses/README.md): derived reports.
- [`state/`](state/README.md): ignored generated configs and local overlays.
- [`protocols/`](protocols/README.md): project-wide registries and release decisions.
- [`configs/`](configs/README.md): reusable presets.

## Configure external result storage

```text
mkdir -p ../SubjectEvolution-results
se-study config --set-result-dir ../SubjectEvolution-results
se-study config
```

The pointer lives in ignored `.se-workspace.toml` and does not affect protocol identity or release artifacts.

## Stage 3C-18 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c18_bounded_candidate_allocation_v1/workflow.toml`](studies/d1z_subject_vm_stage3c18_bounded_candidate_allocation_v1/workflow.toml). The workflow runs top-1 and top-2 arms from the same nine-source carrier-on edge-forward baseline, verifies source identity and read-only control behavior, and packages only declared Stage 3C-7/8/10/18 evidence without checkpoints.

Both arms retain the same normalized-dot score, latest tie-break, candidate validity, delay bounds, target family, carrier, delta, exposure and rollback. Top-2 combines at most two candidates by equal-weight objective-fact mean but still produces one proposal under the original per-event budget. No scalar objective, automatic keep/revert, permanent retention, topology evolution, learned attention weight, universal-attention claim or Epoch 1 entry is authorized.

## Validation and packaging

After package metadata, entry-point, dependency or editable-checkout changes:

```text
make conda-sync
```

Normal validation:

```text
make test
make conda-check
make parity
make release-check
```

`make package` builds from a disposable archive copy and keeps only the current v0.132 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.132 D1-Z iteration](docs/迭代/v0.132_D1-Z_主体图Stage3C18有界候选分配审计.md)
