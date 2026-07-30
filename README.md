# SE v0.81

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

D3-T has now passed both its preregistered screen and disjoint-seed replication. In the supplied replication, 8/8 manipulation contracts pass, 8/8 effects retain the screen direction, and neutralizing spatial-processing support increases cumulative realized resource conversion by an equal-seed median of about **2.546%**, above the unchanged 2% practical threshold.

This remains an acute fixed-checkpoint mechanism result. It does not establish long-horizon selection, adaptive benefit, stable niches, or a population source rule. The observed direction remains suppressive on this estimand: active support reduces realized conversion relative to neutral support on both independent panels.

The next authorized stage is exact-protocol confirmation on a third disjoint seed set.

## Workspace layout

- [`studies/`](studies/README.md): study design, candidate/config protocols, ordered runbooks, and frozen evidence chains.
- [`runs/`](runs/README.md): source trajectories, intervention branches, and checkpoints.
- [`analyses/`](analyses/README.md): derived assessments, audits, and compact reports only.
- [`state/`](state/README.md): mutable local decision overlays.
- [`protocols/`](protocols/README.md): project-wide registries and immutable release decisions.
- [`configs/`](configs/README.md): reusable project-level configuration presets; study-specific configs live with their study.

## D3-T runbook

The canonical design and complete frozen screen-to-replication chain are under [`studies/d3t_spatial_processing_conversion_v1/`](studies/d3t_spatial_processing_conversion_v1/README.md).

Executable commands are intentionally isolated in the numbered files under [`studies/d3t_spatial_processing_conversion_v1/commands/`](studies/d3t_spatial_processing_conversion_v1/commands/). Run only the command file for the intended step; README files do not duplicate executable command blocks.

## Validation workflow

Project validation targets remain defined in the [`Makefile`](Makefile). Target-device GPU parity remains a release gate and requires a usable CUDA/CuPy environment.

## Current documents

- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Recurring governance check](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [v0.81 implementation report](docs/v0.81/IMPLEMENTATION_REPORT.md)
- [v0.81 governance check](docs/v0.81/GOVERNANCE_CHECK.md)
