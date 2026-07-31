# SE v0.84

Reference implementation for nested-subject existence evolution simulation.

## Current direction

Portfolio/candidate audit expansion remains paused. The active mainline follows
`PROJECT_CHARTER`: build effective environmental diversity and costed inherited
carrier capabilities before returning to ecological or social claims.

D1-D established that inherited resource-sensing radius reaches the physical
observation boundary and can be neutralized while preserving genotype and all
registered costs. Its three-seed calibration is frozen under
[`studies/d1d_inherited_resource_sensing_v1/`](studies/d1d_inherited_resource_sensing_v1/README.md).
The archived source used a non-persistent v1 resource landscape, so the result
is treated as a substrate mismatch rather than a general fitness conclusion.

v0.84 adds D1-E persistent multiscale resources. Four existing resource channels
now retain distinct coarse-to-fine spatial modes through moving-target renewal,
creating a real scale tradeoff for inherited sensing radii without rewards, role
labels, or result-dependent world feedback. The active runbook is under
[`studies/d1e_persistent_multiscale_resources_v1/`](studies/d1e_persistent_multiscale_resources_v1/README.md).

## Workspace layout

- [`studies/`](studies/README.md): study design, protocols, ordered runbooks, and frozen evidence.
- [`runs/`](runs/README.md): source trajectories, intervention branches, and checkpoints.
- [`analyses/`](analyses/README.md): derived results and compact reports only.
- [`state/`](state/README.md): mutable local decision overlays.
- [`protocols/`](protocols/README.md): project-wide registries and immutable release decisions.
- [`configs/`](configs/README.md): reusable project-level configuration presets.

Each active study includes a numbered result-packaging script. Compact bundles
omit checkpoint bytes by default and can include them explicitly for exact replay.

## Validation workflow

Project validation targets remain defined in the [`Makefile`](Makefile). Target-
device GPU parity requires a usable CUDA/CuPy environment.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Recurring governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.84 ecosystem implementation](docs/v0.84/ECOSYSTEM_IMPLEMENTATION.md)
