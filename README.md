# SubjectEvolution v0.130.0

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

The project is building a **partitioned unified subject graph** with one node/edge identity space, bounded continuous internal tokens, short-lived local eligibility, delayed association, explicitly guarded temporary parameter writes, exact rollback, and score-free paired evidence. The current fixed bootstrap graph and nearest-token/single-winner selectors are engineering shaping aids, not evolved topology or a universal attention claim.

Version 0.130.0 implements **Subject VM Stage 3C-16: fixed-bootstrap edge eligibility-carrier reachability audit**. It keeps the v0.129 nine-source, 32-entity, sixteen-bootstrap-subject, eight-tick, exposure-three CPU panel fixed. Both arms route the same one-hot proposal coordinate to `edge_forward_gate`; the only bootstrap difference is whether edge 0 owns the existing bounded local-eligibility flag and gate.

The carrier-off arm preserves token generation, delayed association and modulation proposals but cannot bind an exact edge target, so it produces no transaction, commit or evaluation window. The carrier-on arm reaches the existing guarded temporary-write chain and produces 129 completed paired windows with full pairing coverage, exact rollback and 0/21 stable objective coordinates. This establishes eligibility-carrier necessity and engineering reachability only; it does not validate causal credit, assign value, authorize retention, or establish learning or subjecthood.

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

## Stage 3C-16 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c16_edge_carrier_reachability_v1/workflow.toml`](studies/d1z_subject_vm_stage3c16_edge_carrier_reachability_v1/workflow.toml). The workflow runs carrier-off and carrier-on `edge_forward_gate` arms from the frozen nine-source panel, verifies source/control identity, and packages only declared Stage 3C-7/8/10 and Stage 3C-16 evidence without checkpoints.

The carrier-off arm is an intentionally unreachable funnel baseline and is not treated as a Stage 3C-8 replicate. The carrier-on arm must pass the existing paired-evidence contracts before component-wise objective coordinates are summarized under `window -> stable subject -> independent source`. No scalar objective, automatic keep/revert, permanent retention, topology evolution, universal-attention claim or Epoch 1 entry is authorized.

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

`make package` builds from a disposable archive copy and keeps only the current v0.130 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.130 D1-Z iteration](docs/迭代/v0.130_D1-Z_主体图Stage3C16边资格载体可达性审计.md)
