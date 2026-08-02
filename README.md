# SubjectEvolution v0.125.0

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

The project is building a **partitioned unified subject graph** with one node/edge identity space, bounded continuous internal tokens, short-lived local eligibility, delayed association, explicitly guarded temporary parameter writes, exact rollback, and score-free paired evidence. The current fixed bootstrap graph and nearest-token/single-winner selectors are engineering shaping aids, not evolved topology or a universal attention claim.

Version 0.125.0 implements **Subject VM Stage 3C-11: independent-source sample-adequacy audit**. It keeps the v0.124 runtime and five-tick branch contract unchanged and expands only the predeclared independent source panel from three to nine CPU seeds. Entities, subjects and paired windows remain nested observations; the independent source checkpoint is the highest replicate unit.

The nine-source panel produces 111 fully paired windows, but only two sources show trace-level discrete-action/objective-event divergence and only one source has a nonzero completed-window objective vector. No objective coordinate passes the descriptive Stage 3C-8 stability screen. This validates a small engineering data pipeline, not stable learning, causal credit, permanent retention or scientific sample sufficiency.

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

## Stage 3C-11 study

```text
se-study show studies/d1z_subject_vm_stage3c11_source_adequacy_v1/workflow.toml
se-study run studies/d1z_subject_vm_stage3c11_source_adequacy_v1/workflow.toml run-expanded-source-study
se-study run studies/d1z_subject_vm_stage3c11_source_adequacy_v1/workflow.toml assess-sample-adequacy
se-study run studies/d1z_subject_vm_stage3c11_source_adequacy_v1/workflow.toml pack-results
```

The workflow preserves the hierarchy `window -> stable subject -> independent source`, retains zero and nonzero outcomes, and emits Stage 3C-7 integrity, Stage 3C-8 component reproducibility, Stage 3C-10 diagnostics and Stage 3C-11 sample-adequacy evidence. It does not authorize permanent parameter retention, scalar reward, automatic keep/revert, topology evolution or Epoch 1.

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

`make package` builds from a disposable archive copy and keeps only the current v0.125 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.125 D1-Z iteration](docs/迭代/v0.125_D1-Z_主体图Stage3C11独立Source样本充分性审计.md)
