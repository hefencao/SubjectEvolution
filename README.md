# SE v0.85

Reference implementation for nested-subject existence and ecological evolution
simulation.

## Current direction

Audit expansion remains paused. The active mainline follows
[`PROJECT_CHARTER`](docs/PROJECT_CHARTER.md): establish effective environmental
diversity and costed inherited carrier capabilities before ecological or social
claims.

The supplied D1-E panel is frozen under
[`studies/d1e_persistent_multiscale_resources_v1/`](studies/d1e_persistent_multiscale_resources_v1/README.md).
Its persistent resource fields remain non-degenerate, but one common sensing
radius across all resource channels has a consistently negative acute paired
outcome.

v0.85 adds D1-F affinity-routed resource sensing. One inherited reach capacity
is routed to the strongest inherited resource-affinity channel while the other
three channels retain local radius-one gradients. Costs and the shared
checkpoint neutralization remain unchanged.

## Workspace layout

- [`studies/`](studies/README.md): study design, protocols, declarative workflows, and frozen evidence.
- [`runs/`](runs/README.md): source trajectories, intervention branches, and checkpoints.
- [`analyses/`](analyses/README.md): derived results and compact reports.
- [`state/`](state/README.md): mutable local decision overlays.
- [`protocols/`](protocols/README.md): project-wide registries and immutable release decisions.
- [`configs/`](configs/README.md): reusable project-level configuration presets.

## Study commands

Study operations are declared in `workflow.toml`, not executable shell files.
After editable installation:

```text
se-study show studies/d1f_channel_selective_resource_sensing_v1
se-study run studies/d1f_channel_selective_resource_sensing_v1 source-pilot --dry-run
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
current version note in the complete project archive.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.85 D1-F iteration](docs/迭代/v0.85_D1-F_按资源通道分配的可遗传感知尺度.md)
