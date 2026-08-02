# SubjectEvolution v0.127.0

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

The project is building a **partitioned unified subject graph** with one node/edge identity space, bounded continuous internal tokens, short-lived local eligibility, delayed association, explicitly guarded temporary parameter writes, exact rollback, and score-free paired evidence. The current fixed bootstrap graph and nearest-token/single-winner selectors are engineering shaping aids, not evolved topology or a universal attention claim.

Version 0.127.0 implements **Subject VM Stage 3C-13: temporary parameter exposure adequacy audit**. It keeps the v0.126 nine-source, 32-entity, sixteen-bootstrap-subject, eight-tick CPU panel fixed and changes only `rollback_after_ticks` from 2 to 3. The paired read-only control horizon is synchronized because the existing Stage-3C-5 contract requires equality; it is not a second experimental factor.

The source checkpoint is generated from the same config in both arms. Branch-only exposure overrides are checksum-bound in the paired plan, and all nine source state/config hashes, bootstrap lineages and read-only control behavior traces match. Longer exposure raises mean effective semantic ticks per commit from 1.000 to 1.993 and increases continuous action-potential/probability differences, but discrete-action differences change from 3 to 2, source incidence from 2/9 to 1/9, and Stage 3C-8 remains 0/21 stable objective coordinates. This is an engineering visibility result, not a utility, learning, causal-credit or retention conclusion.

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

## Stage 3C-13 study

```text
se-study show studies/d1z_subject_vm_stage3c13_exposure_adequacy_v1/workflow.toml
se-study run studies/d1z_subject_vm_stage3c13_exposure_adequacy_v1/workflow.toml run-baseline-exposure-two
se-study run studies/d1z_subject_vm_stage3c13_exposure_adequacy_v1/workflow.toml run-extended-exposure-three
se-study run studies/d1z_subject_vm_stage3c13_exposure_adequacy_v1/workflow.toml assess-exposure-adequacy
se-study run studies/d1z_subject_vm_stage3c13_exposure_adequacy_v1/workflow.toml pack-results
```

The comparison requires identical source state/config hashes, identical bootstrap lineage, complete bounded-trace coverage and identical read-only control behavior. Windows remain nested observations under `window -> stable subject -> independent source`. No scalar objective, automatic keep/revert, permanent retention, topology evolution or Epoch 1 entry is authorized.

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

`make package` builds from a disposable archive copy and keeps only the current v0.127 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.127 D1-Z iteration](docs/迭代/v0.127_D1-Z_主体图Stage3C13临时参数暴露充分性审计.md)
