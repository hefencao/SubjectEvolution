# SubjectEvolution v0.128.0

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

The project is building a **partitioned unified subject graph** with one node/edge identity space, bounded continuous internal tokens, short-lived local eligibility, delayed association, explicitly guarded temporary parameter writes, exact rollback, and score-free paired evidence. The current fixed bootstrap graph and nearest-token/single-winner selectors are engineering shaping aids, not evolved topology or a universal attention claim.

Version 0.128.0 implements **Subject VM Stage 3C-14: fixed-bootstrap parameter-family reachability audit**. It keeps the v0.127 nine-source, 32-entity, sixteen-bootstrap-subject, eight-tick, exposure-three CPU panel fixed and changes only the fixed bootstrap target-family token route from `node_bias` to `node_output_gate`.

Both arms start from identical pre-bootstrap source state/config hashes and stable-subject selections. The target control ports are excluded from association similarity, and read-only control behavior is identical apart from relocating the same one-hot target coordinate from token port 23 to port 25. Both families receive 722 proposals and 144 temporary commits. `node_output_gate` produces fewer continuous live/control differences than `node_bias`, while both remain sparse at the sampled-action layer and retain 0/21 stable objective coordinates. This is a parameter-role visibility result, not a family-value ranking, learning claim, causal-credit result or retention authorization.

A preliminary `node_input_gate` arm was rejected before formal comparison because the targeted bootstrap node reads a constant-one input; in that fixed graph, an input-gate delta and bias delta are algebraically equivalent.

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

## Stage 3C-14 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c14_family_reachability_v1/workflow.toml`](studies/d1z_subject_vm_stage3c14_family_reachability_v1/workflow.toml). The workflow runs both score-free evidence arms, verifies the isolation contract and packages reports without checkpoints.

The comparison requires identical pre-bootstrap source state/config hashes, identical subject selection, an authorized one-hot token relocation only, complete bounded-trace coverage and identical read-only action/objective behavior. Windows remain nested observations under `window -> stable subject -> independent source`. No scalar objective, automatic keep/revert, permanent retention, topology evolution or Epoch 1 entry is authorized.

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

`make package` builds from a disposable archive copy and keeps only the current v0.128 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.128 D1-Z iteration](docs/迭代/v0.128_D1-Z_主体图Stage3C14参数族可达性审计.md)
