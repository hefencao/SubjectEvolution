# SubjectEvolution v0.131.0

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

The project is building a **partitioned unified subject graph** with one node/edge identity space, bounded continuous internal tokens, short-lived local eligibility, delayed association, explicitly guarded temporary parameter writes, exact rollback, and score-free paired evidence. The fixed bootstrap graph and selectors remain replaceable engineering shaping aids, not evolved topology or a universal attention claim.

Version 0.131.0 implements **Subject VM Stage 3C-17: equal-similarity temporal tie-break audit**. It holds the reachable Stage-3C-16 `edge_forward_gate` carrier-on panel fixed and changes only whether exact normalized-dot similarity ties select the latest or oldest eligible historical token.

The latest arm maps all 1008 assigned candidates to delay 1. The oldest arm spreads delays across 1–6 but repeatedly reuses only 32 historical events per source instead of 112. It produces fewer proposals and completed windows, while both arms remain 0/21 stable objective coordinates. This establishes that the tie-break is a material fixed-bootstrap addressing bias; it does not rank recency, validate causal credit, authorize retention, or establish learning or subjecthood.

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

## Stage 3C-17 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c17_temporal_tie_break_v1/workflow.toml`](studies/d1z_subject_vm_stage3c17_temporal_tie_break_v1/workflow.toml). The workflow runs latest-on-tie and oldest-on-tie arms from the same nine-source carrier-on edge-forward baseline, verifies source identity and read-only control behavior, and packages only declared Stage 3C-7/8/10/17 evidence without checkpoints.

Both arms retain the same candidate set, normalized-dot score, thresholds, delay bounds, target family, carrier, delta, exposure and rollback. No scalar objective, automatic keep/revert, permanent retention, topology evolution, universal-attention claim or Epoch 1 entry is authorized.

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

`make package` builds from a disposable archive copy and keeps only the current v0.131 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.131 D1-Z iteration](docs/迭代/v0.131_D1-Z_主体图Stage3C17时间并列寻址审计.md)
