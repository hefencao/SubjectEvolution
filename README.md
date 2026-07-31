# SE v0.89

Reference implementation for nested-subject existence and ecological evolution
simulation.

## Current direction

Audit expansion remains paused. The active mainline follows
[`PROJECT_CHARTER`](docs/PROJECT_CHARTER.md): establish effective environmental
diversity and costed inherited carrier capabilities before ecological or social
claims.

D1-I is frozen under
[`studies/d1i_fixed_budget_resource_conversion_v1/`](studies/d1i_fixed_budget_resource_conversion_v1/README.md).
Fixed-total conversion allocation produces repeatable energetic differences but
only weak allocation separation and no repeated demographic direction. v0.89
adds D1-J: the existing four storage genes allocate one fixed total internal
volume across channels, creating a conserved material-capacity opportunity cost
without changing rewards, actions, conversion effects, or environment amplitudes.

## Workspace layout

- [`studies/`](studies/README.md): study design, protocols, declarative workflows, and frozen evidence.
- [`runs/`](runs/README.md): source trajectories, intervention branches, and checkpoints.
- [`analyses/`](analyses/README.md): derived results and compact reports.
- [`state/`](state/README.md): mutable local decision overlays.
- [`protocols/`](protocols/README.md): project-wide registries and immutable release decisions.
- [`configs/`](configs/README.md): reusable project-level configuration presets.

## Configure external result storage

Compact result archives must not be written into the project tree. Configure one
project-local pointer to an external directory after editable installation:

```text
mkdir -p ../SubjectEvolution-results
se-study config --set-result-dir ../SubjectEvolution-results
se-study config
```

The setting is stored in ignored `.se-workspace.toml`; the result directory must
resolve outside the project. Relative `pack-results --output` values are placed
under that configured directory. An absolute external `--output` can still be
used for a one-off destination.

## Study commands

Study operations are declared in `workflow.toml`, not executable shell files.
After editable installation:

```text
se-study show studies/d1j_fixed_budget_resource_storage_v1
se-study run studies/d1j_fixed_budget_resource_storage_v1 source-pilot --dry-run
```

Every parameter is declared and can be overridden explicitly. The resolved argv
is printed before execution, and no shell is used.

## Validation and packaging

Validation targets remain in the [`Makefile`](Makefile). `make conda-sync`
checks only durable version sources, cleans bytecode, refreshes editable install,
and verifies the active Conda environment. It does not inspect or delete local
iteration history.

Local iteration notes live under `docs/迭代/`. `make package` builds a disposable
artifact copy, removes old iteration notes from that copy, and keeps only the
current version note in the complete project archive. Workspace settings and
runtime results are never included.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.89 D1-J iteration](docs/迭代/v0.89_D1-J_固定总量的可遗传四资源储存分配.md)
