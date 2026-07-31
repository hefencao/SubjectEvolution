# SE v0.96

Reference implementation for nested-subject existence and ecological evolution
simulation.

## Current direction

The current source is already a plural subject-environment system, not a
single-gene prototype. It contains 704 inherited coordinates spanning morphology,
action policy, knowledge routing, memory, sparse selection, capacities,
functional modules and physiology. Its environment contains four asynchronous
resource fields with distinct body effects, plus oxygen, terrain, wear and
mortality-trace structure.

D1-P ran this complete system to tick 1200 on three seeds. All samples turned over
successfully, but population was still expanding and founder-lineage breadth was
uneven. A relative audit now identifies 520 retained, 112 concentrated, 66
moderate-thinning and 6 strong-thinning coordinates, but those flags do not yet
authorize gene-specific adjustment.

D1-Q changes only the four-channel external regeneration vector, uniformly from
0.027 to 0.00675. A frozen independent pilot passes source health and a
cycle-aware bounded-regime gate over 450 ticks, longer than the maximum 431-tick
environmental forcing period. This authorizes the three-seed integrated panel,
not a return to one-gene/one-environment iteration.

## Workspace layout

- [`studies/`](studies/README.md): study design, protocols, workflows and frozen evidence.
- [`runs/`](runs/README.md): runtime trajectories and explicit replay checkpoints.
- [`analyses/`](analyses/README.md): derived reports, including integrated retention scans.
- [`state/`](state/README.md): ignored generated configs and local overlays.
- [`protocols/`](protocols/README.md): project-wide registries and release decisions.
- [`configs/`](configs/README.md): reusable presets.

## Configure external result storage

```text
mkdir -p ../SubjectEvolution-results
se-study config --set-result-dir ../SubjectEvolution-results
se-study config
```

The pointer lives in ignored `.se-workspace.toml` and does not affect protocol
identity or release artifacts.

## D1-Q workflow

```text
se-study show studies/d1q_integrated_equilibrium_retention_v1
se-study run studies/d1q_integrated_equilibrium_retention_v1 evidence-audit --dry-run
se-study run studies/d1q_integrated_equilibrium_retention_v1 prepare-config --dry-run
se-study run studies/d1q_integrated_equilibrium_retention_v1 integrated-panel --dry-run
```

The frozen pilot lock authorizes only `integrated-panel`. No paired or per-gene
effect command is declared.

## Validation and packaging

Run `make conda-sync` only after changing package metadata, entry points,
dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current v0.96
iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.96 D1-Q iteration](docs/迭代/v0.96_D1-Q_周期感知稳态与整合遗传收缩审计.md)
