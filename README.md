# SubjectEvolution v0.126.0

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

The project is building a **partitioned unified subject graph** with one node/edge identity space, bounded continuous internal tokens, short-lived local eligibility, delayed association, explicitly guarded temporary parameter writes, exact rollback, and score-free paired evidence. The current fixed bootstrap graph and nearest-token/single-winner selectors are engineering shaping aids, not evolved topology or a universal attention claim.

Version 0.126.0 implements **Subject VM Stage 3C-12: trace-safe branch-horizon adequacy audit**. It keeps the v0.125 nine-source panel, 32 entities, 16 bootstrap subjects, source tick 2, CPU backend and all update/rollback contracts fixed, and compares branch horizons 5 and 8 only.

The eight-tick arm raises completed paired windows from 111 to 143 but does not add any discrete-action boundary crossing: both arms contain three such events in the same two sources, and Stage 3C-8 remains 0/21 stable objective coordinates. The added tail records delayed continuation of one already-diverged objective path, not a new update-induced action divergence. This narrows the short-horizon explanation without claiming universal horizon sufficiency, learning, causal credit or permanent retention.

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

## Stage 3C-12 study

```text
se-study show studies/d1z_subject_vm_stage3c12_horizon_adequacy_v1/workflow.toml
se-study run studies/d1z_subject_vm_stage3c12_horizon_adequacy_v1/workflow.toml run-baseline-five-tick
se-study run studies/d1z_subject_vm_stage3c12_horizon_adequacy_v1/workflow.toml run-extended-eight-tick
se-study run studies/d1z_subject_vm_stage3c12_horizon_adequacy_v1/workflow.toml assess-horizon-adequacy
se-study run studies/d1z_subject_vm_stage3c12_horizon_adequacy_v1/workflow.toml pack-results
```

The comparison requires identical source state hashes, identical bootstrap lineage, complete bounded-trace coverage and exact equality of every event-shaped trace array before the five-tick stop boundary. Windows remain nested observations under the hierarchy `window -> stable subject -> independent source`. No scalar objective, automatic keep/revert, permanent retention, topology evolution or Epoch 1 entry is authorized.

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

`make package` builds from a disposable archive copy and keeps only the current v0.126 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.126 D1-Z iteration](docs/迭代/v0.126_D1-Z_主体图Stage3C12分支Horizon充分性审计.md)
