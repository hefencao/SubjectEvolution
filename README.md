# SE v0.83

Reference implementation for nested-subject existence evolution simulation.

## Current direction

D3-T remains frozen as terminal `confirmed-acute`; no long-horizon selection or
stable-niche claim follows from it. New candidate-audit work is paused. The
active mainline follows `PROJECT_CHARTER`: expand costed inherited carrier
capabilities that enter real world interaction before returning to ecological
claims or social control.

v0.83 adds D1-D inherited resource-sensing scale. Morphology coordinate 7
selects a resource-gradient radius of 1, 2, 4, or 8 and pays separate
maintenance, use, and development costs. A shared-checkpoint radius-one
neutralization preserves genotype and costs. The active calibration design and
numbered commands are under
[`studies/d1d_inherited_resource_sensing_v1/`](studies/d1d_inherited_resource_sensing_v1/README.md).

## Workspace layout

- [`studies/`](studies/README.md): study design, candidate/config protocols, ordered runbooks, and frozen evidence chains.
- [`runs/`](runs/README.md): source trajectories, intervention branches, and checkpoints.
- [`analyses/`](analyses/README.md): derived assessments, audits, and compact reports only.
- [`state/`](state/README.md): mutable local decision overlays.
- [`protocols/`](protocols/README.md): project-wide registries and immutable release decisions.
- [`configs/`](configs/README.md): reusable project-level configuration presets; study-specific configs live with their study.

## D3-T result chain

The canonical design and complete frozen screen-to-confirmation chain are under
[`studies/d3t_spatial_processing_conversion_v1/`](studies/d3t_spatial_processing_conversion_v1/README.md).

Executable commands remain isolated in numbered files under
[`studies/d3t_spatial_processing_conversion_v1/commands/`](studies/d3t_spatial_processing_conversion_v1/commands/).
The compact result import/export commands make cross-version transfer explicit;
README files do not duplicate executable command blocks.

## Compact result capability

A canonical exported result bundle contains the study definition, protocols,
frozen evidence, chain summary, and a file manifest. It is sufficient for
scientific decision import. Large checkpoints remain external and are required
only for exact replay or analyses not already frozen.

## Validation workflow

Project validation targets remain defined in the [`Makefile`](Makefile). Target-
device GPU parity remains a release gate and requires a usable CUDA/CuPy
environment.

## Current documents

- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Recurring governance check](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [v0.83 capability implementation](docs/v0.83/CAPABILITY_IMPLEMENTATION.md)
- [v0.82 frozen D3-T result integration](docs/v0.82/RESULT_INTEGRATION.md)
