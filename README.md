# SubjectEvolution v0.129.0

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

The project is building a **partitioned unified subject graph** with one node/edge identity space, bounded continuous internal tokens, short-lived local eligibility, delayed association, explicitly guarded temporary parameter writes, exact rollback, and score-free paired evidence. The current fixed bootstrap graph and nearest-token/single-winner selectors are engineering shaping aids, not evolved topology or a universal attention claim.

Version 0.129.0 implements **Subject VM Stage 3C-15: fixed-bootstrap local sensitivity and algebraic-degeneracy audit**. It keeps the v0.128 nine-source, 32-entity, sixteen-bootstrap-subject, eight-tick, exposure-three CPU panel unchanged and performs bounded external finite-difference probes over all six generic parameter families. Probe branches are transient, source checkpoints are never modified, and no live-write, eligibility, association, retention or topology contract is changed.

The audit separates local mechanical sensitivity from current eligibility reachability. `node_bias` and `node_input_gate` are numerically degenerate in the current constant-one bootstrap; `node_trace_gate` changes the internal token but not the one-step action channel; `edge_forward_gate` becomes action-sensitive only after the delayed edge has a warmed state; and `edge_bandwidth` remains locally zero because no inspected operating point reaches its clamp. `node_trace_gate` and `edge_forward_gate` are mechanically sensitive but unavailable to the current local eligibility selector. These are engineering identifiability facts, not value rankings, learning claims, causal-credit validation or authorization to expand eligibility.

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

## Stage 3C-15 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c15_local_sensitivity_v1/workflow.toml`](studies/d1z_subject_vm_stage3c15_local_sensitivity_v1/workflow.toml). The workflow regenerates the frozen score-free node-bias baseline, replays two bounded operating contexts from checksum-bound quiescent source checkpoints, and packages the Stage 3C-7/8/10 evidence plus Stage 3C-15 assessment without checkpoints.

The diagnostic requires the same nine independent sources and distinguishes first-post-bootstrap behavior from a one-tick warmed delayed-edge context. It reports action-channel sensitivity, token-channel sensitivity, clamp activity and existing eligibility reachability separately. Windows remain nested observations under `window -> stable subject -> independent source`. No scalar objective, automatic keep/revert, eligibility expansion, permanent retention, topology evolution or Epoch 1 entry is authorized.

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

`make package` builds from a disposable archive copy and keeps only the current v0.129 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.129 D1-Z iteration](docs/迭代/v0.129_D1-Z_主体图Stage3C15局部灵敏度与退化诊断.md)
